"""Execution simulator: limit-order fill and position management on M1 BID/ASK candles.

Each setup is simulated in isolation (same signals for every runner method). Conventions:
  * Buy limit fills when ASK low <= entry; sell limit when BID high >= entry. A gap through the
    limit fills at the (better) open price.
  * Buy exits are driven by BID, sell exits by ASK (SL of a sell is triggered by the ask).
  * Intrabar ambiguity is resolved PESSIMISTICALLY: inside one M1 candle the stop is assumed to be
    hit before any favourable trigger; in the fill candle only the stop is checked; triggers (BE,
    partial, trailing) take effect from the next candle; a local trigger (BE / partial) observed
    in a candle is executed at its level (partial: minus `partial_slippage`).
  * SL / market exits suffer `stop_slippage`; a gap beyond the SL exits at the open.
All prices are mapped to a "buy space" (sells are mirrored by negation) so one code path serves
both directions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field
from typing import Optional

import numpy as np

from .config import CostModel, StrategyConfig
from .data import MinuteData
from .setups import Setup
from .structure import BREAK_DOWN, BREAK_UP, SWING_HIGH, SWING_LOW

INF = 2**62


@dataclass
class TradeResult:
    setup_id: str
    direction: int
    variant: str
    outcome: str = ""            # NOT_PLACED / MISSED_AT_PLACEMENT / CANCELLED / NOT_FILLED_END / CLOSED / OPEN_AT_END
    cancel_reason: str = ""
    place_time: int = -1
    fill_time: int = -1
    entry_theoretical: float = math.nan
    fill_price: float = math.nan
    sl_initial: float = math.nan
    risk_dist: float = math.nan  # |fill - SL| in price units = 1R
    be_time: int = -1
    partial_time: int = -1
    partial_price: float = math.nan
    partial_fraction: float = 0.0
    exit_time: int = -1
    exit_price: float = math.nan
    exit_reason: str = ""
    tp_price: float = math.nan
    r_gross: float = 0.0
    r_commission: float = 0.0
    r_swap: float = 0.0
    r_net: float = 0.0
    mfe_r: float = 0.0
    mae_r: float = 0.0
    nights: float = 0.0
    spread_at_fill: float = math.nan
    r_partial_leg: float = math.nan
    r_runner_leg: float = math.nan

    def as_dict(self) -> dict:
        return asdict(self)


class _Space:
    """Direction-mirrored price arrays: entry side (fills) and exit side (stops / targets)."""

    def __init__(self, m1: MinuteData, direction: int, extra_spread: float):
        if direction > 0:
            self.ent_open = m1.ao + extra_spread
            self.ent_low = m1.al + extra_spread
            self.ex_open = m1.bo
            self.ex_low = m1.bl
            self.ex_high = m1.bh
        else:
            self.ent_open = -m1.bo
            self.ent_low = -m1.bh
            self.ex_open = -(m1.ao + extra_spread)
            self.ex_low = -(m1.ah + extra_spread)
            self.ex_high = -(m1.al + extra_spread)


def _first(mask: np.ndarray) -> int:
    """Index of the first True, or -1."""
    if mask.size == 0:
        return -1
    i = int(np.argmax(mask))
    return i if mask[i] else -1


class Simulator:
    def __init__(self, m1: MinuteData, cfg: StrategyConfig, costs: CostModel, tick: float,
                 entry_close_times: np.ndarray, entry_events: list, entry_atr: np.ndarray,
                 entry_tf: int):
        self.m1, self.cfg, self.costs, self.tick = m1, cfg, costs, tick
        self.space = {1: _Space(m1, 1, costs.extra_spread), -1: _Space(m1, -1, costs.extra_spread)}
        self.entry_close_times = entry_close_times
        self.entry_atr = entry_atr
        # structure events of the entry TF, as (time_known, price, bar)
        def ev(kind):
            rows = [(int(entry_close_times[e.bar]), e.price, e.bar) for e in entry_events if e.kind == kind]
            return np.array([r[0] for r in rows], dtype=np.int64), np.array([r[1] for r in rows]), \
                np.array([r[2] for r in rows], dtype=np.int64)
        self.breaks = {1: ev(BREAK_DOWN), -1: ev(BREAK_UP)}         # runner A exits
        self.swings = {1: ev(SWING_LOW), -1: ev(SWING_HIGH)}        # runner D trailing
        # rollover instants (server midnight) for swaps
        self.n = len(m1.time)

    # ------------------------------------------------------------------------------------------
    def run(self, s: Setup, variant: str = "", runner: Optional[str] = None,
            target_r: Optional[float] = None) -> TradeResult:
        cfg, m1 = self.cfg, self.m1
        runner = runner or cfg.runner_method
        target_r = target_r if target_r is not None else cfg.runner_target_r
        d = s.direction
        res = TradeResult(s.id, d, variant or runner, entry_theoretical=s.entry, sl_initial=s.sl)
        if s.status not in ("SETUP_VALID", "INVALIDATED") or s.place_time < 0:
            res.outcome = "NOT_PLACED"
            res.cancel_reason = s.reason or s.status
            return res
        cancel_t = s.end_time if s.end_time > 0 else INF

        # --- placement (spread gate retried at each entry-TF close while valid) -------------------
        t_place = s.place_time
        j0 = m1.index_at_or_after(t_place)
        if cfg.max_spread_price > 0:
            while j0 < self.n and (m1.ao[j0] - m1.bo[j0]) > cfg.max_spread_price:
                k = int(np.searchsorted(self.entry_close_times, t_place, side="right"))
                if k >= len(self.entry_close_times):
                    j0 = self.n
                    break
                t_place = int(self.entry_close_times[k])
                if t_place >= cancel_t:
                    res.outcome, res.cancel_reason = "CANCELLED", "SPREAD_NEVER_OK"
                    return res
                j0 = m1.index_at_or_after(t_place)
        if j0 >= self.n:
            res.outcome = "NOT_FILLED_END"
            return res
        res.place_time = int(m1.time[j0])
        sp = self.space[d]
        E = d * s.entry       # buy space
        SL = d * s.sl
        if sp.ent_open[j0] <= E:
            res.outcome, res.cancel_reason = "MISSED_AT_PLACEMENT", "PRICE_THROUGH_ENTRY"
            return res

        # --- pending ---------------------------------------------------------------------------
        j_end = int(np.searchsorted(m1.time, cancel_t, side="left")) if cancel_t < INF else self.n
        jf = _first(sp.ent_low[j0:j_end] <= E)
        if jf < 0:
            if cancel_t < INF:
                res.outcome, res.cancel_reason = "CANCELLED", s.end_reason
            else:
                res.outcome = "NOT_FILLED_END"
            return res
        jf += j0
        P = min(E, sp.ent_open[jf])
        R = P - SL
        res.fill_time = int(m1.time[jf])
        res.fill_price = d * P
        res.risk_dist = R
        res.spread_at_fill = float(m1.ao[jf] - m1.bo[jf])
        if R <= 0:
            # gap through entry AND stop: filled at the open, stopped immediately. R falls back to
            # the theoretical risk so the loss is expressed against the planned 1R.
            R = E - SL
            res.risk_dist = R
            res.exit_reason = "GAP_THROUGH_SL"
            return self._finish(res, [(jf, 1.0, sp.ex_open[jf] - self.costs.stop_slippage)], P, R, d, jf, jf)
        return self._manage(s, res, jf, P, R, SL, runner, target_r)

    # ------------------------------------------------------------------------------------------
    def _manage(self, s: Setup, res: TradeResult, jf: int, P: float, R: float, SL: float,
                runner: str, target_r: float) -> TradeResult:
        cfg, costs, m1 = self.cfg, self.costs, self.m1
        d = s.direction
        sp = self.space[d]
        n = self.n
        slip_stop, slip_part = costs.stop_slippage, costs.partial_slippage
        exits: list[tuple[int, float, float]] = []   # (bar, fraction, buy-space price)
        remaining = 1.0
        sl = SL
        # server TP (methods B and C) placed with the order
        tp = INF
        if runner == "FIXED_R":
            tp = P + target_r * R
        elif runner == "LIQUIDITY":
            tp = d * s.tp_liquidity
            if tp <= P + cfg.partial_trigger_r * R:      # target must lie beyond the partial level
                tp = P + cfg.liquidity_fallback_r * R
        res.tp_price = d * tp if tp < INF else math.nan
        be_level = P + cfg.be_trigger_r * R
        part_level = P + cfg.partial_trigger_r * R
        be_done = False
        part_done = False

        # fill candle: stop only (pessimistic)
        if sp.ex_low[jf] <= sl:
            exits.append((jf, 1.0, min(sl, sp.ex_open[jf]) - slip_stop))
            res.exit_reason = "SL"
            return self._finish(res, exits, P, R, d, jf, jf)

        j = jf + 1
        # pre-computed runner event streams (buy space)
        brk_t, _, _ = self.breaks[d]
        sw_t, sw_p, sw_bar = self.swings[d]
        while j < n:
            # ---- phase boundaries: next structural event time (runner A / D) -------------------
            next_evt_j = n
            evt = None
            if part_done and runner == "STRUCTURE":
                i = int(np.searchsorted(brk_t, res.partial_time, side="right"))
                if i < len(brk_t):
                    je = m1.index_at_or_after(int(brk_t[i]))
                    if je < next_evt_j:
                        next_evt_j, evt = max(je, j), ("A", i)
            if part_done and runner == "TRAILING":
                i = int(np.searchsorted(sw_t, max(res.partial_time, int(m1.time[j - 1])), side="right"))
                # skip swing events that would not tighten the stop
                while i < len(sw_t):
                    newsl = self._trail_level(d, sw_p[i], sw_bar[i], int(sw_t[i]))
                    if newsl > sl:
                        break
                    i += 1
                if i < len(sw_t):
                    je = m1.index_at_or_after(int(sw_t[i]))
                    if je < next_evt_j:
                        next_evt_j, evt = max(je, j), ("D", i)

            seg_end = next_evt_j
            if seg_end > j:
                lo = sp.ex_low[j:seg_end]
                hi = sp.ex_high[j:seg_end]
                trig = (lo <= sl)
                if not part_done:
                    trig = trig | (hi >= (be_level if not be_done else part_level))
                if tp < INF:
                    trig = trig | (hi >= tp)
                k = _first(trig)
                if k >= 0:
                    jj = j + k
                    self._mfe(res, sp, j, jj + 1, P, R)
                    if sp.ex_low[jj] <= sl:  # stop first (pessimistic)
                        exits.append((jj, remaining, min(sl, sp.ex_open[jj]) - slip_stop))
                        res.exit_reason = "SL" if not be_done else ("BE" if sl <= P + 1e-9 else "TRAIL_SL")
                        return self._finish(res, exits, P, R, d, jf, jj)
                    hi_j = sp.ex_high[jj]
                    if not be_done and hi_j >= be_level:
                        be_done = True
                        res.be_time = int(m1.time[jj])
                        sl = max(sl, P + cfg.be_offset_points * self.tick)
                    if not part_done and hi_j >= part_level:
                        part_done = True
                        res.partial_time = int(m1.time[jj])
                        frac = cfg.partial_fraction
                        exits.append((jj, frac, part_level - slip_part))
                        res.partial_price = d * (part_level - slip_part)
                        res.partial_fraction = frac
                        remaining -= frac
                        if remaining <= 1e-9:
                            res.exit_reason = "PARTIAL_ALL"
                            return self._finish(res, exits, P, R, d, jf, jj)
                    if tp < INF and hi_j >= tp:
                        exits.append((jj, remaining, tp))
                        res.exit_reason = "TP"
                        return self._finish(res, exits, P, R, d, jf, jj)
                    j = jj + 1
                    continue
                self._mfe(res, sp, j, seg_end, P, R)
                j = seg_end
            if j >= n or evt is None:
                break
            # ---- apply the structural event at bar j (its information is known at bar open) ------
            kind, i = evt
            if kind == "A":
                exits.append((j, remaining, sp.ex_open[j] - slip_stop))
                res.exit_reason = "STRUCTURE_BREAK"
                return self._finish(res, exits, P, R, d, jf, j)
            newsl = self._trail_level(d, sw_p[i], sw_bar[i], int(sw_t[i]))
            if newsl > sl:
                sl = newsl
                if sp.ex_open[j] <= sl:   # already through the new stop at the open
                    exits.append((j, remaining, sp.ex_open[j] - slip_stop))
                    res.exit_reason = "TRAIL_SL"
                    return self._finish(res, exits, P, R, d, jf, j)
        # data exhausted
        last = n - 1
        exits.append((last, remaining, sp.ex_open[last]))
        res.exit_reason = "END_OF_DATA"
        r = self._finish(res, exits, P, R, d, jf, last)
        r.outcome = "OPEN_AT_END"
        return r

    def _trail_level(self, d: int, swing_price: float, bar: int, t: int) -> float:
        a = self.entry_atr[bar]
        buf = 0.0 if np.isnan(a) else self.cfg.trailing_buffer_atr * a
        if d > 0:
            lvl = math.floor((swing_price - buf) / self.tick + 1e-9) * self.tick
            return lvl
        spread = self.m1.spread_at(t) if self.cfg.sl_add_spread_for_sells else 0.0
        lvl = math.ceil((swing_price + buf + spread) / self.tick - 1e-9) * self.tick
        return -lvl

    def _mfe(self, res: TradeResult, sp: _Space, a: int, b: int, P: float, R: float) -> None:
        if b <= a:
            return
        res.mfe_r = max(res.mfe_r, (sp.ex_high[a:b].max() - P) / R)
        res.mae_r = min(res.mae_r, (sp.ex_low[a:b].min() - P) / R)

    def _finish(self, res: TradeResult, exits, P: float, R: float, d: int, jf: int, jx: int) -> TradeResult:
        m1, costs = self.m1, self.costs
        res.outcome = "CLOSED"
        res.exit_time = int(m1.time[jx])
        res.exit_price = d * exits[-1][2]
        res.r_gross = float(sum(f * (px - P) for _, f, px in exits) / R)
        if res.partial_time >= 0 and len(exits) >= 2:
            # legs kept separately so the portfolio layer can apply PartialFallback when the
            # broker volume cannot be split (CLOSE_ALL: everything at the partial price;
            # KEEP_ALL: everything follows the runner).
            res.r_partial_leg = float((exits[0][2] - P) / R)
            res.r_runner_leg = float((exits[-1][2] - P) / R)
        # commission: one round turn on the full volume, expressed in R
        risk_money_per_lot = R * costs.contract_size
        res.r_commission = -costs.commission_per_lot_rt / risk_money_per_lot
        # swap per fraction held over server midnights
        nights = 0.0
        for jj, f, _ in exits:
            nights += f * self._nights(int(m1.time[jf]), int(m1.time[jj]))
        res.nights = nights
        swap = costs.swap_long_per_lot if d > 0 else costs.swap_short_per_lot
        res.r_swap = nights * swap / risk_money_per_lot
        res.r_net = res.r_gross + res.r_commission + res.r_swap
        return res

    def _nights(self, t0: int, t1: int) -> float:
        """Number of server midnights crossed (triple on `triple_swap_weekday`)."""
        if t1 <= t0:
            return 0.0
        off0 = int(self.m1.server_offset[min(self.m1.index_at_or_after(t0), self.n - 1)])
        s0, s1 = t0 + off0, t1 + off0
        day0, day1 = s0 // 86400, s1 // 86400
        total = 0.0
        for day in range(day0, day1):
            wd = (day + 3) % 7            # 1970-01-01 was a Thursday => Monday = 0
            if wd >= 5:
                continue                  # no rollover charged on Sat/Sun midnights
            total += 3.0 if wd == self.costs.triple_swap_weekday else 1.0
        return total
