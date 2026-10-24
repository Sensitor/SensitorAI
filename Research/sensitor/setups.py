"""Signal engine: turns closed bars (entry TF + H1/H4) into fully specified, frozen setups.

For every setup the engine determines, from market data only:
  - creation (confirmation) time and all frozen levels (impulse, OTE, OB, FVG, entry, SL, targets),
  - the time it becomes eligible for order placement (RSI gating),
  - the time and reason of its structural invalidation (if any).
Whether the limit order actually fills is decided by the execution simulator (simulator.py) or,
live, by the broker. Every rejected candidate is recorded with an explicit reason code.

Spec: Docs/SPECIFICATION.md §2-9. MQL5 port: MQL5/Include/SensitorAI/SignalEngine.mqh.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

import numpy as np

from .config import StrategyConfig
from .indicators import atr_sma, rsi_mt5, rsi_window_blocks
from .structure import (BEAR, BULL, BREAK_DOWN, BREAK_UP, NEUTRAL, SWEEP_HIGH, SWEEP_LOW,
                        SWING_HIGH, SWING_LOW, StructureTracker, combine_bias)
from . import zones as Z


@dataclass
class Bars:
    """OHLC bars of one timeframe. `time` = bar OPEN time in epoch seconds (UTC)."""
    tf: int                 # minutes
    time: np.ndarray        # int64
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray

    def __len__(self) -> int:
        return len(self.time)

    @property
    def close_time(self) -> np.ndarray:
        return self.time + self.tf * 60

    def last_closed_index(self, t: int) -> int:
        """Index of the last bar whose close time is <= t (-1 if none)."""
        return int(np.searchsorted(self.close_time, t, side="right")) - 1


@dataclass
class Setup:
    id: str
    direction: int
    break_bar: int
    break_time: int
    break_label: str
    broken_level: float
    broken_pivot: int
    origin_idx: int
    origin_price: float          # impulse origin (Lo for buy, Hi for sell)
    extreme_idx: int
    extreme_price: float         # impulse end (Hi for buy, Lo for sell)
    confirm_bar: int
    confirm_time: int
    bias_h4: int
    bias_h1: int
    atr: float
    spread: float
    ote_low: float = math.nan
    ote_high: float = math.nan
    fvg_low: float = math.nan
    fvg_high: float = math.nan
    fvg_mid_idx: int = -1
    ob_low: float = math.nan
    ob_high: float = math.nan
    ob_idx: int = -1
    zone_low: float = math.nan
    zone_high: float = math.nan
    entry_case: str = ""         # "A" (OB inside OTE) / "B" (partial overlap)
    entry: float = math.nan
    sl: float = math.nan
    risk_dist: float = math.nan
    tp_liquidity: float = math.nan
    tp_liquidity_is_fallback: bool = False
    rsi_extreme: float = math.nan
    sweeps_compatible: str = ""
    sweeps_caution: str = ""
    status: str = "SETUP_VALID"  # SETUP_VALID / REJECTED / INVALIDATED / MISSED
    reason: str = ""
    place_bar: int = -1
    place_time: int = -1
    end_bar: int = -1            # bar of invalidation (setup no longer valid after its close)
    end_time: int = -1
    end_reason: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    direction: int
    break_bar: int
    break_label: str
    broken_level: float
    broken_pivot: int
    origin_idx: int
    origin_price: float


@dataclass
class Decision:
    time: int
    bar: int
    direction: int
    code: str
    detail: str = ""


class SetupEngine:
    def __init__(self, cfg: StrategyConfig, entry: Bars, h1: Bars, h4: Bars,
                 spread_fn: Callable[[int], float], tick: float = 0.01,
                 rsi_bars: Optional[Bars] = None):
        cfg.validate()
        self.cfg = cfg
        self.tick = tick
        self.spread_fn = spread_fn
        self.e = entry
        self.h1, self.h4 = h1, h4
        self.atr_e = atr_sma(entry.h, entry.l, entry.c, 14)
        self.trk_e = StructureTracker(entry.o, entry.h, entry.l, entry.c, self.atr_e,
                                      cfg.swing_left_entry, cfg.swing_right_entry,
                                      cfg.bos_buffer_atr, cfg.bias_flip_mode, cfg.liquidity_max_levels)
        self.trk = {}
        self.htf_next = {}
        for name, b in (("H1", h1), ("H4", h4)):
            atr = atr_sma(b.h, b.l, b.c, 14)
            self.trk[name] = StructureTracker(b.o, b.h, b.l, b.c, atr, cfg.swing_left_htf,
                                              cfg.swing_right_htf, cfg.bos_buffer_atr,
                                              cfg.bias_flip_mode, cfg.liquidity_max_levels)
            self.htf_next[name] = 0
        # RSI
        if rsi_bars is None or cfg.rsi_timeframe == entry.tf:
            self.rsi_bars = entry
        else:
            self.rsi_bars = rsi_bars
        self.rsi = rsi_mt5(self.rsi_bars.c, cfg.rsi_period)
        self.setups: list[Setup] = []
        self.decisions: list[Decision] = []
        self.bias_series = np.zeros(len(entry), dtype=np.int8)
        self.h4_trend = np.zeros(len(entry), dtype=np.int8)
        self.h1_trend = np.zeros(len(entry), dtype=np.int8)

    # ------------------------------------------------------------------------------------------
    def _advance_htf(self, t: int) -> None:
        for name, b in (("H1", self.h1), ("H4", self.h4)):
            trk = self.trk[name]
            ct = b.close_time
            i = self.htf_next[name]
            while i < len(b) and ct[i] <= t:
                trk.update(i)
                i += 1
            self.htf_next[name] = i

    def _bias(self) -> tuple[int, int, int]:
        h4 = self.trk["H4"].trend
        h1 = self.trk["H1"].trend
        return combine_bias(h4, h1, self.cfg.bias_mode), h4, h1

    def _log(self, t: int, k: int, d: int, code: str, detail: str = "") -> None:
        self.decisions.append(Decision(t, k, d, code, detail))

    def _rsi_check(self, t: int, direction: int) -> tuple[bool, float]:
        if self.cfg.rsi_mode == "OFF":
            return False, math.nan
        k = self.rsi_bars.last_closed_index(t)
        return rsi_window_blocks(self.rsi, k, self.cfg.rsi_window, direction,
                                 self.cfg.rsi_overbought, self.cfg.rsi_oversold)

    # ------------------------------------------------------------------------------------------
    def run(self) -> list[Setup]:
        e = self.e
        ct = e.close_time
        cand: dict[int, Optional[Candidate]] = {BULL: None, BEAR: None}
        active: dict[int, Optional[Setup]] = {BULL: None, BEAR: None}
        for k in range(len(e)):
            t = int(ct[k])
            self._advance_htf(t)
            events = self.trk_e.update(k)
            bias, h4, h1 = self._bias()
            self.bias_series[k] = bias
            self.h4_trend[k] = h4
            self.h1_trend[k] = h1

            # 1) invalidation / gating of active setups
            for d in (BULL, BEAR):
                s = active[d]
                if s is None or k <= s.confirm_bar:
                    continue
                reason = self._invalidation(s, k, bias)
                if reason:
                    self._end(s, k, t, reason)
                    active[d] = None
                    continue
                if s.place_bar < 0:   # waiting for RSI gate
                    blocked, val = self._rsi_check(t, d)
                    if not blocked:
                        self._place(s, k, t)
                        if s.status != "SETUP_VALID":
                            active[d] = None

            # 2) pending candidates (SWING_CONFIRM anchor)
            for d in (BULL, BEAR):
                cd = cand[d]
                if cd is None or k <= cd.break_bar:
                    continue
                opp = BREAK_DOWN if d == BULL else BREAK_UP
                if any(ev.kind == opp for ev in events):
                    self._log(t, k, d, "CANDIDATE_DROPPED_OPPOSITE_BREAK")
                    cand[d] = None
                    continue
                if bias != d:
                    self._log(t, k, d, "CANDIDATE_DROPPED_BIAS", f"bias={bias}")
                    cand[d] = None
                    continue
                sw_kind = SWING_HIGH if d == BULL else SWING_LOW
                sw = [ev for ev in events if ev.kind == sw_kind and ev.pivot > cd.origin_idx]
                if sw:
                    cand[d] = None
                    s = self._build(cd, sw[0].pivot, k, t, bias, h4, h1)
                    if s is not None:
                        self._activate(s, active, k, t)

            # 3) new breaks => new candidates
            for ev in events:
                if ev.kind not in (BREAK_UP, BREAK_DOWN):
                    continue
                d = BULL if ev.kind == BREAK_UP else BEAR
                if bias != d:
                    self._log(t, k, d, "BREAK_IGNORED_BIAS", f"bias={bias} h4={h4} h1={h1}")
                    continue
                cd = self._candidate(d, ev, k)
                if self.cfg.impulse_anchor == "BOS_BAR":
                    s = self._build(cd, k, k, t, bias, h4, h1)
                    if s is not None:
                        self._activate(s, active, k, t)
                else:
                    if cand[d] is not None:
                        self._log(t, k, d, "CANDIDATE_REPLACED")
                    cand[d] = cd
                    self._log(t, k, d, "CANDIDATE_CREATED", f"level={ev.price} {ev.label}")
        return self.setups

    # ------------------------------------------------------------------------------------------
    def _candidate(self, d: int, ev, k: int) -> Candidate:
        e = self.e
        i0 = ev.pivot
        if d == BULL:
            seg = e.l[i0:k + 1]
            off = int(np.flatnonzero(seg == seg.min())[-1])
        else:
            seg = e.h[i0:k + 1]
            off = int(np.flatnonzero(seg == seg.max())[-1])
        o = i0 + off
        price = float(e.l[o] if d == BULL else e.h[o])
        return Candidate(d, k, ev.label, ev.price, ev.pivot, o, price)

    def _activate(self, s: Setup, active: dict, k: int, t: int) -> None:
        self.setups.append(s)
        if s.status != "SETUP_VALID":
            return  # a rejected or missed setup never supersedes a valid one
        old = active[s.direction]
        if old is not None:
            self._end(old, k, t, "INV_SUPERSEDED")
        active[s.direction] = s

    def _end(self, s: Setup, k: int, t: int, reason: str) -> None:
        s.end_bar, s.end_time, s.end_reason = k, t, reason
        if s.status == "SETUP_VALID":
            s.status = "INVALIDATED"
        self._log(t, k, s.direction, reason, s.id)

    def _invalidation(self, s: Setup, k: int, bias: int) -> str:
        e, cfg = self.e, self.cfg
        d = s.direction
        buf = 0.0
        if cfg.bos_buffer_atr > 0 and not np.isnan(self.atr_e[k]):
            buf = cfg.bos_buffer_atr * self.atr_e[k]
        if d == BULL:
            if cfg.continuation_invalidation == "WICK":
                if e.h[k] > s.extreme_price:
                    return "INV_CONTINUATION"
            elif e.c[k] > s.extreme_price + buf:
                return "INV_CONTINUATION"
            if e.c[k] < s.sl or e.c[k] < s.origin_price:
                return "INV_DEEP_FAILURE"
        else:
            if cfg.continuation_invalidation == "WICK":
                if e.l[k] < s.extreme_price:
                    return "INV_CONTINUATION"
            elif e.c[k] < s.extreme_price - buf:
                return "INV_CONTINUATION"
            if e.c[k] > s.sl or e.c[k] > s.origin_price:
                return "INV_DEEP_FAILURE"
        if cfg.cancel_on_bias_change and bias != d:
            return "INV_BIAS_CHANGED"
        if cfg.rsi_mode == "CONTINUOUS" and s.place_bar >= 0:
            blocked, _ = self._rsi_check(int(e.close_time[k]), d)
            if blocked:
                return "INV_RSI"
        return ""

    def _place(self, s: Setup, k: int, t: int) -> None:
        """Mark the setup eligible for order placement at close of bar k (time t)."""
        if self.cfg.reject_if_touched_before_placement:
            e = self.e
            a, b = s.extreme_idx + 1, k
            if b >= a:
                if s.direction == BULL and e.l[a:b + 1].min() <= s.entry:
                    s.status, s.reason = "MISSED", "MISSED_TOUCHED_BEFORE_PLACEMENT"
                    self._log(t, k, s.direction, s.reason, s.id)
                    return
                if s.direction == BEAR and e.h[a:b + 1].max() >= s.entry:
                    s.status, s.reason = "MISSED", "MISSED_TOUCHED_BEFORE_PLACEMENT"
                    self._log(t, k, s.direction, s.reason, s.id)
                    return
        s.place_bar, s.place_time = k, t
        self._log(t, k, s.direction, "READY_TO_PLACE", s.id)

    # ------------------------------------------------------------------------------------------
    def _build(self, cd: Candidate, end_idx: int, k: int, t: int, bias: int, h4: int,
               h1: int) -> Optional[Setup]:
        """Freeze all levels of a setup confirmed at close of bar k. Returns None if rejected
        before a Setup object is worth recording (impossible geometry); otherwise a Setup whose
        status may be REJECTED with a reason."""
        cfg, e, tick = self.cfg, self.e, self.tick
        d = cd.direction
        o_idx = cd.origin_idx
        if end_idx < o_idx:
            return None
        if d == BULL:
            seg = e.h[o_idx:end_idx + 1]
            ext_idx = o_idx + int(np.argmax(seg))
            lo, hi = cd.origin_price, float(e.h[ext_idx])
            ext_price = hi
        else:
            seg = e.l[o_idx:end_idx + 1]
            ext_idx = o_idx + int(np.argmin(seg))
            lo, hi = float(e.l[ext_idx]), cd.origin_price
            ext_price = lo
        atr = float(self.atr_e[k]) if not np.isnan(self.atr_e[k]) else math.nan
        spread = float(self.spread_fn(t))
        sid = f"{'B' if d == BULL else 'S'}{int(e.time[cd.break_bar])}"
        s = Setup(id=sid, direction=d, break_bar=cd.break_bar, break_time=int(e.close_time[cd.break_bar]),
                  break_label=cd.break_label, broken_level=cd.broken_level, broken_pivot=cd.broken_pivot,
                  origin_idx=o_idx, origin_price=cd.origin_price, extreme_idx=ext_idx,
                  extreme_price=ext_price, confirm_bar=k, confirm_time=t, bias_h4=h4, bias_h1=h1,
                  atr=atr, spread=spread)

        def reject(code: str, detail: str = "") -> Setup:
            s.status, s.reason = "REJECTED", code
            self._log(t, k, d, code, f"{sid} {detail}".strip())
            return s

        rng = hi - lo
        if rng <= 0 or math.isnan(atr):
            return reject("REJECT_DEGENERATE_IMPULSE")
        if cfg.min_impulse_atr > 0 and rng < cfg.min_impulse_atr * atr:
            return reject("REJECT_IMPULSE_TOO_SMALL", f"range={rng:.3f}")
        ote = Z.ote_zone(d, lo, hi, cfg.ote_min, cfg.ote_max)
        s.ote_low, s.ote_high = ote.low, ote.high

        # FVG / OB pairs, chronological, first fully valid pair wins
        fvgs = Z.find_fvgs(d, e.h, e.l, o_idx, ext_idx, cfg.fvg_min_atr * atr)
        if not fvgs:
            return reject("REJECT_NO_FVG")
        failure = "REJECT_NO_OB"
        chosen = None
        for fvg in fvgs:
            ob = Z.find_order_block(d, e.o, e.h, e.l, e.c, fvg.index, o_idx, cfg.ob_max_dist_bars,
                                    cfg.ob_pre_origin_bars, cfg.ob_zone_mode)
            if ob is None:
                continue
            zone = Z.intersect(ob, ote)
            if zone is None:
                failure = _worse(failure, "REJECT_NO_OB_OTE_OVERLAP")
                continue
            first = fvg.index + 2
            ob_state = Z.zone_state(d, ob, e.h, e.l, e.c, first, k)
            if ob_state in (Z.FULLY_MITIGATED, Z.INVALIDATED):
                failure = _worse(failure, "REJECT_OB_" + ob_state)
                continue
            fvg_state = Z.zone_state(d, fvg, e.h, e.l, e.c, first, k)
            # a FVG filled by the pullback towards the OB is expected; only a close beyond it rejects
            if fvg_state == Z.INVALIDATED:
                failure = _worse(failure, "REJECT_FVG_" + fvg_state)
                continue
            chosen = (fvg, ob, zone)
            break
        if chosen is None:
            return reject(failure)
        fvg, ob, zone = chosen
        s.fvg_low, s.fvg_high, s.fvg_mid_idx = fvg.low, fvg.high, fvg.index
        s.ob_low, s.ob_high, s.ob_idx = ob.low, ob.high, ob.index
        s.zone_low, s.zone_high = zone.low, zone.high
        s.entry_case = "A" if Z.is_inside(ob, ote) else "B"

        entry = Z.entry_price(d, zone, cfg.entry_depth, tick)
        if entry is None:
            return reject("REJECT_ZONE_TOO_NARROW")
        s.entry = entry
        buffer = max(cfg.sl_buffer_points * tick, cfg.sl_buffer_atr * atr)
        spread_add = spread if (d == BEAR and cfg.sl_add_spread_for_sells) else 0.0
        s.sl = Z.stop_loss_price(d, ob, lo, hi, cfg.sl_anchor, buffer, tick, spread_add)
        s.risk_dist = round(abs(s.entry - s.sl), 10)
        if s.risk_dist <= 0 or (d == BULL and s.sl >= s.entry) or (d == BEAR and s.sl <= s.entry):
            return reject("REJECT_SL_INVALID")
        if s.risk_dist < cfg.min_sl_spread_mult * spread:
            return reject("REJECT_SL_TOO_TIGHT", f"D={s.risk_dist:.3f} spread={spread:.3f}")
        if cfg.max_sl_atr > 0 and s.risk_dist > cfg.max_sl_atr * atr:
            return reject("REJECT_SL_TOO_WIDE", f"D={s.risk_dist:.3f}")

        # sweeps
        comp, caution = self._sweeps(d, cd.break_bar, t)
        s.sweeps_compatible = ";".join(comp)
        s.sweeps_caution = ";".join(caution)
        if caution and cfg.caution_sweep_action == "BLOCK":
            return reject("REJECT_CAUTION_SWEEP", s.sweeps_caution)
        if cfg.require_compatible_sweep and not comp:
            return reject("REJECT_NO_COMPATIBLE_SWEEP")

        # liquidity target for runner method B (frozen now)
        trg_level = s.entry + d * cfg.partial_trigger_r * s.risk_dist
        liq_trk = self.trk["H1"] if cfg.liquidity_tf == 60 else (
            self.trk["H4"] if cfg.liquidity_tf == 240 else self.trk_e)
        lv = (liq_trk.nearest_liquidity_above(trg_level) if d == BULL
              else liq_trk.nearest_liquidity_below(trg_level))
        if lv is not None:
            s.tp_liquidity = lv.price
        else:
            s.tp_liquidity = s.entry + d * cfg.liquidity_fallback_r * s.risk_dist
            s.tp_liquidity_is_fallback = True

        # RSI exclusion filter
        blocked, val = self._rsi_check(t, d)
        s.rsi_extreme = val
        if cfg.rsi_mode == "AT_SETUP" and blocked:
            return reject("REJECT_RSI", f"rsi={val:.2f}")
        self._log(t, k, d, "SETUP_CONFIRMED",
                  f"{sid} case={s.entry_case} E={s.entry} SL={s.sl} D={s.risk_dist:.3f}")
        if cfg.rsi_mode in ("GATE_PLACEMENT", "CONTINUOUS") and blocked:
            self._log(t, k, d, "WAIT_RSI_GATE", f"rsi={val:.2f}")
            return s
        self._place(s, k, t)
        return s

    def _sweeps(self, d: int, break_bar: int, t: int) -> tuple[list[str], list[str]]:
        cfg = self.cfg
        lb = cfg.sweep_lookback_bars
        comp, caution = [], []
        want_comp = SWEEP_LOW if d == BULL else SWEEP_HIGH
        want_caution = SWEEP_HIGH if d == BULL else SWEEP_LOW
        for ev in reversed(self.trk_e.events):
            if ev.bar < break_bar - lb:
                break
            if ev.kind == want_comp and ev.bar <= break_bar:
                comp.append(f"E:{ev.price}")
        for name in ("H1", "H4"):
            trk = self.trk[name]
            last = trk.last_k
            for ev in trk.events[::-1]:
                if ev.bar < last - lb + 1:
                    break
                if ev.kind == want_comp:
                    comp.append(f"{name}:{ev.price}")
                elif ev.kind == want_caution:
                    caution.append(f"{name}:{ev.price}")
        return comp, caution


_REJECT_ORDER = ["REJECT_NO_OB", "REJECT_NO_OB_OTE_OVERLAP", "REJECT_OB_INVALIDATED",
                 "REJECT_OB_FULLY_MITIGATED", "REJECT_FVG_INVALIDATED"]


def _worse(a: str, b: str) -> str:
    """Keep the most advanced failure reason (later in the pipeline)."""
    return a if _REJECT_ORDER.index(a) >= _REJECT_ORDER.index(b) else b
