"""Market-structure engine: swings, breaks (BOS / CHoCH), trend, liquidity levels and sweeps.

Pure analysis — never places orders. Processes CLOSED bars one at a time (incremental) so that
every output at bar k only depends on bars 0..k. See Docs/SPECIFICATION.md §1-3.

Ported 1:1 in MQL5/Include/SensitorAI/StructureEngine.mqh.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

BULL, BEAR, NEUTRAL = 1, -1, 0

# Event kinds
SWING_HIGH = "SWING_HIGH"
SWING_LOW = "SWING_LOW"
BREAK_UP = "BREAK_UP"
BREAK_DOWN = "BREAK_DOWN"
SWEEP_HIGH = "SWEEP_HIGH"
SWEEP_LOW = "SWEEP_LOW"


@dataclass
class Level:
    index: int          # pivot bar index
    price: float
    confirm_index: int  # bar at whose close the pivot became known


@dataclass
class Event:
    kind: str
    bar: int            # bar index at whose close the event is known
    price: float        # level involved (swing price / broken level / swept level)
    pivot: int          # pivot index of the level involved
    label: str = ""     # "BOS" / "CHOCH" for breaks


def is_swing_high(h: np.ndarray, i: int, left: int, right: int) -> bool:
    if i - left < 0 or i + right >= len(h):
        return False
    hi = h[i]
    for j in range(i - left, i):
        if not hi > h[j]:
            return False
    for j in range(i + 1, i + right + 1):
        if not hi >= h[j]:
            return False
    return True


def is_swing_low(l: np.ndarray, i: int, left: int, right: int) -> bool:
    if i - left < 0 or i + right >= len(l):
        return False
    lo = l[i]
    for j in range(i - left, i):
        if not lo < l[j]:
            return False
    for j in range(i + 1, i + right + 1):
        if not lo <= l[j]:
            return False
    return True


class StructureTracker:
    """Incremental structure state for one timeframe.

    Arrays are the full OHLC series of the timeframe; `update(k)` must be called for k = 0,1,2,...
    and only reads indices <= k.
    """

    def __init__(self, o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
                 atr: np.ndarray, left: int, right: int, bos_buffer_atr: float = 0.0,
                 flip_mode: str = "FLIP_ON_CHOCH", max_levels: int = 30):
        self.o, self.h, self.l, self.c, self.atr = o, h, l, c, atr
        self.left, self.right = left, right
        self.bos_buffer_atr = bos_buffer_atr
        self.flip_mode = flip_mode
        self.max_levels = max_levels
        self.ref_high: Optional[Level] = None
        self.ref_low: Optional[Level] = None
        self.last_swing_high: Optional[Level] = None
        self.last_swing_low: Optional[Level] = None
        self.trend = NEUTRAL
        self.liq_highs: list[Level] = []
        self.liq_lows: list[Level] = []
        self.events: list[Event] = []
        self.trend_at: list[int] = []   # trend after processing bar k
        self.last_k = -1

    # -- helpers -------------------------------------------------------------------------------
    def _buffer(self, k: int) -> float:
        if self.bos_buffer_atr <= 0:
            return 0.0
        a = self.atr[k]
        return 0.0 if np.isnan(a) else self.bos_buffer_atr * a

    def update(self, k: int) -> list[Event]:
        assert k == self.last_k + 1, "bars must be processed sequentially"
        self.last_k = k
        out: list[Event] = []
        c, h, l = self.c[k], self.h[k], self.l[k]
        buf = self._buffer(k)

        # 1. liquidity levels: broken (close beyond) or swept (wick beyond, close back inside)
        keep = []
        for lv in self.liq_highs:
            if c > lv.price + buf:
                continue  # broken, not a sweep
            if h > lv.price:
                out.append(Event(SWEEP_HIGH, k, lv.price, lv.index))
                continue
            keep.append(lv)
        self.liq_highs = keep
        keep = []
        for lv in self.liq_lows:
            if c < lv.price - buf:
                continue
            if l < lv.price:
                out.append(Event(SWEEP_LOW, k, lv.price, lv.index))
                continue
            keep.append(lv)
        self.liq_lows = keep

        # 2. breaks of the current references (close beyond; a wick is never a break)
        if self.ref_high is not None and c > self.ref_high.price + buf:
            label = "CHOCH" if self.trend == BEAR else "BOS"
            out.append(Event(BREAK_UP, k, self.ref_high.price, self.ref_high.index, label))
            self.ref_high = None
            self._apply_break(BULL, label)
        if self.ref_low is not None and c < self.ref_low.price - buf:
            label = "CHOCH" if self.trend == BULL else "BOS"
            out.append(Event(BREAK_DOWN, k, self.ref_low.price, self.ref_low.index, label))
            self.ref_low = None
            self._apply_break(BEAR, label)

        # 3. swings confirmed at this bar (pivot i = k - right)
        i = k - self.right
        if i >= 0:
            if is_swing_high(self.h, i, self.left, self.right):
                lv = Level(i, float(self.h[i]), k)
                self.ref_high = lv
                self.last_swing_high = lv
                self.liq_highs.append(lv)
                if len(self.liq_highs) > self.max_levels:
                    self.liq_highs.pop(0)
                out.append(Event(SWING_HIGH, k, lv.price, i))
            if is_swing_low(self.l, i, self.left, self.right):
                lv = Level(i, float(self.l[i]), k)
                self.ref_low = lv
                self.last_swing_low = lv
                self.liq_lows.append(lv)
                if len(self.liq_lows) > self.max_levels:
                    self.liq_lows.pop(0)
                out.append(Event(SWING_LOW, k, lv.price, i))

        self.trend_at.append(self.trend)
        self.events.extend(out)
        return out

    def _apply_break(self, direction: int, label: str) -> None:
        if self.flip_mode == "NEUTRAL_ON_CHOCH" and label == "CHOCH":
            self.trend = NEUTRAL
        else:
            self.trend = direction

    def nearest_liquidity_above(self, price: float) -> Optional[Level]:
        cands = [lv for lv in self.liq_highs if lv.price > price]
        return min(cands, key=lambda lv: lv.price) if cands else None

    def nearest_liquidity_below(self, price: float) -> Optional[Level]:
        cands = [lv for lv in self.liq_lows if lv.price < price]
        return max(cands, key=lambda lv: lv.price) if cands else None


def combine_bias(h4: int, h1: int, mode: str = "REQUIRE_BOTH") -> int:
    """Combined H4/H1 bias (Docs/SPECIFICATION.md §2.1). Any contradiction => NEUTRAL."""
    if mode == "REQUIRE_BOTH":
        return h4 if (h4 == h1 and h4 != NEUTRAL) else NEUTRAL
    if mode == "H4_LEADS":
        if h4 == NEUTRAL:
            return NEUTRAL
        if h1 == -h4:
            return NEUTRAL
        return h4
    raise ValueError(mode)
