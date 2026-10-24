"""Cycle 4: established strategy families on XAU/USD (Research/EXPERIMENT_PLAN.md).

Every family produces trade *specifications* from closed bars only (decision at bar close); a common
executor fills them on M1 BID/ASK candles with the same pessimistic conventions as simulator.py:
  * buys enter/stop on the ASK side, are exited on the BID side (sells mirrored);
  * market and stop entries suffer `stop_slippage`; stop entries gapped through fill at the open;
  * in the fill candle only the stop is checked; inside a candle the stop wins over the target;
  * commission and swaps expressed in R. One position at a time per variant.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .config import CostModel
from .data import MinuteData
from .indicators import atr_sma, rsi_mt5
from .setups import Bars


@dataclass
class Spec:
    direction: int
    t_entry: int                  # earliest entry time (epoch s)
    kind: str = "market"          # "market" | "stop"
    level: float = np.nan         # stop level (price) for kind="stop"
    t_entry_until: int = 0        # stop orders expire at this time
    sl_abs: float = np.nan        # absolute stop price, or
    sl_dist: float = np.nan       # stop distance from the fill price
    tp_r: float = np.nan          # target in R (nan = none)
    t_exit: int = 2**62           # planned exit time (signal / session end / max hold)
    oco: Optional["Spec"] = None  # other leg of an OCO pair


class Executor:
    def __init__(self, m1: MinuteData, costs: CostModel):
        self.m1, self.c = m1, costs
        self.n = len(m1.time)
        e = costs.extra_spread
        self.sp = {
            1: dict(eo=m1.ao + e, eh=m1.ah + e, xo=m1.bo, xl=m1.bl, xh=m1.bh),
            -1: dict(eo=-m1.bo, eh=-m1.bl, xo=-(m1.ao + e), xl=-(m1.ah + e), xh=-(m1.al + e)),
        }

    def idx(self, t: int) -> int:
        return int(np.searchsorted(self.m1.time, t, side="left"))

    def _fill(self, s: Spec) -> Optional[tuple[int, float]]:
        sp = self.sp[s.direction]
        j0 = self.idx(s.t_entry)
        if j0 >= self.n:
            return None
        if s.kind == "market":
            return j0, sp["eo"][j0] + self.c.stop_slippage
        lvl = s.direction * s.level
        j1 = min(self.idx(s.t_entry_until), self.n)
        if j1 <= j0:
            return None
        hit = np.flatnonzero(sp["eh"][j0:j1] >= lvl)
        if not len(hit):
            return None
        j = j0 + int(hit[0])
        return j, max(lvl, sp["eo"][j]) + self.c.stop_slippage

    def run(self, s: Spec) -> Optional[dict]:
        f = self._fill(s)
        if s.oco is not None:
            g = self._fill(s.oco)
            if g is not None and (f is None or g[0] < f[0]):
                s, f = s.oco, g
        if f is None:
            return None
        jf, P = f
        d = s.direction
        sp = self.sp[d]
        SL = P - s.sl_dist if np.isfinite(s.sl_dist) else d * s.sl_abs
        R = P - SL
        if not np.isfinite(R) or R <= 0:
            return None
        TP = P + s.tp_r * R if np.isfinite(s.tp_r) else np.inf
        jx = min(self.idx(s.t_exit), self.n)          # == n when no planned exit inside the data
        slip = self.c.stop_slippage
        if sp["xl"][jf] <= SL:
            jj, px, why = jf, min(SL, sp["xo"][jf]) - slip, "SL"
        else:
            a, b = jf + 1, max(jx, jf + 1)
            lo, hi = sp["xl"][a:b], sp["xh"][a:b]
            hit = np.flatnonzero((lo <= SL) | (hi >= TP))
            if len(hit):
                jj = a + int(hit[0])
                if sp["xl"][jj] <= SL:
                    px, why = min(SL, sp["xo"][jj]) - slip, "SL"
                else:
                    px, why = max(TP, sp["xo"][jj]), "TP"      # a gap beyond the target fills at the open
            elif b < self.n:
                jj, why = b, "TIME"
                px = sp["xo"][jj] - slip
            else:
                jj, why = self.n - 1, "END_OF_DATA"
                px = sp["xo"][jj] - slip
        r_gross = (px - P) / R
        r_comm = -self.c.commission_per_lot_rt / (R * self.c.contract_size)
        nights = self._nights(int(self.m1.time[jf]), int(self.m1.time[jj]))
        swap = self.c.swap_long_per_lot if d > 0 else self.c.swap_short_per_lot
        r_swap = nights * swap / (R * self.c.contract_size)
        return dict(direction=d, fill_time=int(self.m1.time[jf]), exit_time=int(self.m1.time[jj]),
                    risk=R, exit=why, r_gross=r_gross, r_net=r_gross + r_comm + r_swap)

    def _nights(self, t0: int, t1: int) -> float:
        off = int(self.m1.server_offset[min(self.idx(t0), self.n - 1)])
        tot = 0.0
        for day in range((t0 + off) // 86400, (t1 + off) // 86400):
            wd = (day + 3) % 7
            if wd < 5:
                tot += 3.0 if wd == self.c.triple_swap_weekday else 1.0
        return tot

    def run_all(self, specs: list[Spec]) -> pd.DataFrame:
        """Sequential: a new trade only after the previous one is closed."""
        out, busy_until = [], -1
        for s in sorted(specs, key=lambda x: x.t_entry):
            if s.t_entry < busy_until:
                continue
            r = self.run(s)
            if r is None:
                continue
            out.append(r)
            busy_until = r["exit_time"]
        return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------
def _roll(x: np.ndarray, n: int, fn) -> np.ndarray:
    """fn over the n PREVIOUS bars (excluding the current one)."""
    s = pd.Series(x)
    return (s.rolling(n).max() if fn == "max" else s.rolling(n).min()).shift(1).to_numpy()


def _ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def _first_after(cond: np.ndarray, k: int, limit: Optional[int] = None) -> int:
    idx = np.flatnonzero(cond[k + 1:]) if limit is None else np.flatnonzero(cond[k + 1:limit + 1])
    return k + 1 + int(idx[0]) if len(idx) else -1


def donchian(b: Bars, N: int, katr: float) -> list[Spec]:
    hh, ll = _roll(b.h, N, "max"), _roll(b.l, N, "min")
    M = max(N // 2, 2)
    xh, xl = _roll(b.h, M, "max"), _roll(b.l, M, "min")
    atr = atr_sma(b.h, b.l, b.c, 20)
    ct = b.close_time
    exit_long, exit_short = b.c < xl, b.c > xh
    specs = []
    for k in range(N + 1, len(b)):
        if np.isnan(atr[k]):
            continue
        for d, cond, ex in ((1, b.c[k] > hh[k], exit_long), (-1, b.c[k] < ll[k], exit_short)):
            if cond:
                k2 = _first_after(ex, k)
                specs.append(Spec(d, int(ct[k]), sl_dist=katr * atr[k], t_exit=int(ct[k2]) if k2 > 0 else 2**62))
    return specs


def _local_to_utc(day: dt.date, hh: int, mm: int, tz: str) -> int:
    return int(dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=ZoneInfo(tz)).timestamp())


def orb(m1: MinuteData, session: str, minutes: int, tp_r: float) -> list[Spec]:
    if session == "LONDON":
        tz, (oh, om), (eh, em) = "Europe/London", (8, 0), (12, 0)
    else:
        tz, (oh, om), (eh, em) = "America/New_York", (8, 20), (16, 0)
    days = pd.to_datetime(m1.time, unit="s", utc=True).tz_convert(tz).normalize().unique()
    specs = []
    for dday in days:
        day = dday.date()
        if day.weekday() >= 5:
            continue
        t0 = _local_to_utc(day, oh, om, tz)
        t1, tend = t0 + minutes * 60, _local_to_utc(day, eh, em, tz)
        a, b_ = np.searchsorted(m1.time, [t0, t1])
        if b_ - a < minutes // 2:
            continue
        hi, lo = m1.bh[a:b_].max(), m1.bl[a:b_].min()
        if hi - lo <= 0:
            continue
        long = Spec(1, t1, "stop", hi, tend, sl_abs=lo, tp_r=tp_r, t_exit=tend)
        short = Spec(-1, t1, "stop", lo, tend, sl_abs=hi, tp_r=tp_r, t_exit=tend)
        long.oco = short
        specs.append(long)
    return specs


def rsi2(b: Bars, s: float, trend_filter: bool, both_sides: bool) -> list[Spec]:
    r = rsi_mt5(b.c, 2)
    sma = pd.Series(b.c).rolling(200).mean().to_numpy()
    atr = atr_sma(b.h, b.l, b.c, 14)
    ct = b.close_time
    specs = []
    ex_long, ex_short = r > 70, r < 30
    for k in range(200, len(b)):
        if np.isnan(atr[k]) or np.isnan(r[k]):
            continue
        if r[k] < s and (not trend_filter or b.c[k] > sma[k]):
            k2 = _first_after(ex_long, k, min(k + 10, len(b) - 1))
            k2 = k2 if k2 > 0 else min(k + 10, len(b) - 1)
            specs.append(Spec(1, int(ct[k]), sl_dist=2 * atr[k], t_exit=int(ct[k2])))
        elif both_sides and r[k] > 100 - s and (not trend_filter or b.c[k] < sma[k]):
            k2 = _first_after(ex_short, k, min(k + 10, len(b) - 1))
            k2 = k2 if k2 > 0 else min(k + 10, len(b) - 1)
            specs.append(Spec(-1, int(ct[k]), sl_dist=2 * atr[k], t_exit=int(ct[k2])))
    return specs


def pullback(h1: Bars, h4: Bars, tp_r: float, both_sides: bool) -> list[Spec]:
    e50, e200 = _ema(h4.c, 50), _ema(h4.c, 200)
    trend4 = np.where(e50 > e200, 1, -1)
    trend4[:200] = 0
    idx4 = np.searchsorted(h4.close_time, h1.close_time, side="right") - 1
    trend = np.where(idx4 >= 0, trend4[np.clip(idx4, 0, None)], 0)
    e20 = _ema(h1.c, 20)
    atr = atr_sma(h1.h, h1.l, h1.c, 14)
    ct = h1.close_time
    specs = []
    for k in range(25, len(h1)):
        if np.isnan(atr[k]):
            continue
        if trend[k] == 1 and h1.c[k - 1] < e20[k - 1] and h1.c[k] > e20[k]:
            sl = h1.l[k - 4:k + 1].min() - 0.1 * atr[k]
            specs.append(Spec(1, int(ct[k]), sl_abs=sl, tp_r=tp_r, t_exit=int(ct[k]) + 5 * 86400))
        elif both_sides and trend[k] == -1 and h1.c[k - 1] > e20[k - 1] and h1.c[k] < e20[k]:
            sl = h1.h[k - 4:k + 1].max() + 0.1 * atr[k]
            specs.append(Spec(-1, int(ct[k]), sl_abs=sl, tp_r=tp_r, t_exit=int(ct[k]) + 5 * 86400))
    return specs


def compression(d1: Bars, kind: str, tp_r: float) -> list[Spec]:
    rng = d1.h - d1.l
    specs = []
    for k in range(7, len(d1) - 1):
        if kind == "NR7":
            ok = rng[k] <= rng[k - 6:k + 1].min()
        else:
            ok = d1.h[k] < d1.h[k - 1] and d1.l[k] > d1.l[k - 1]
        if not ok or rng[k] <= 0:
            continue
        t0, t1 = int(d1.close_time[k]), int(d1.close_time[k + 1])
        long = Spec(1, t0, "stop", d1.h[k], t1, sl_abs=d1.l[k], tp_r=tp_r, t_exit=t1)
        long.oco = Spec(-1, t0, "stop", d1.l[k], t1, sl_abs=d1.h[k], tp_r=tp_r, t_exit=t1)
        specs.append(long)
    return specs
