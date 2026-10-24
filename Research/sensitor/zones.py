"""Pure zone computations: OTE, FVG, Order Block, OB∩OTE intersection, entry and SL prices.

All functions are deterministic and side-effect free (unit-tested in Tests/python).
Direction convention: +1 = buy, -1 = sell. Zones are (low, high) tuples with low <= high.
Ported 1:1 in MQL5/Include/SensitorAI/Zones.mqh.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

EPS = 1e-9

# zone states (Docs/SPECIFICATION.md §6.3)
NEW = "NEW"
VALID = "VALID"
PARTIALLY_MITIGATED = "PARTIALLY_MITIGATED"
FULLY_MITIGATED = "FULLY_MITIGATED"
INVALIDATED = "INVALIDATED"


@dataclass(frozen=True)
class Zone:
    low: float
    high: float
    index: int = -1      # defining bar (OB candle, or middle candle of the FVG)

    @property
    def width(self) -> float:
        return self.high - self.low


# --------------------------------------------------------------------------------------------
# OTE
# --------------------------------------------------------------------------------------------
def retracement_level(direction: int, lo: float, hi: float, r: float) -> float:
    """Price at retracement r (0 = impulse extreme reached, 1 = impulse origin).

    Buy (impulse up lo -> hi): hi - r*(hi-lo). Sell (impulse down hi -> lo): lo + r*(hi-lo).
    """
    rng = hi - lo
    return hi - r * rng if direction > 0 else lo + r * rng


def ote_zone(direction: int, lo: float, hi: float, rmin: float = 0.62, rmax: float = 0.79) -> Zone:
    a = retracement_level(direction, lo, hi, rmin)
    b = retracement_level(direction, lo, hi, rmax)
    return Zone(min(a, b), max(a, b))


# --------------------------------------------------------------------------------------------
# FVG / OB detection inside an impulse
# --------------------------------------------------------------------------------------------
def find_fvgs(direction: int, h: np.ndarray, l: np.ndarray, start: int, end: int,
              min_size: float = 0.0) -> list[Zone]:
    """FVGs whose 3 candles (m-1, m, m+1) lie inside [start, end], in chronological order.

    Bullish: L[m+1] > H[m-1] -> zone [H[m-1], L[m+1]]. Bearish: H[m+1] < L[m-1] -> [H[m+1], L[m-1]].
    """
    out = []
    for m in range(start + 1, end):
        if direction > 0:
            a, b = h[m - 1], l[m + 1]
        else:
            a, b = h[m + 1], l[m - 1]
        if b > a and (b - a) >= min_size and (b - a) > EPS:
            out.append(Zone(float(a), float(b), m))
    return out


def find_order_block(direction: int, o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
                     fvg_mid: int, origin: int, max_dist: int, pre_origin: int,
                     zone_mode: str = "WICK") -> Optional[Zone]:
    """Last opposite-colour candle before the FVG displacement (searching back from m-1)."""
    lo_bound = max(origin - pre_origin, fvg_mid - 1 - max_dist, 0)
    for j in range(fvg_mid - 1, lo_bound - 1, -1):
        opposite = c[j] < o[j] if direction > 0 else c[j] > o[j]
        if opposite:
            if zone_mode == "BODY":
                return Zone(float(min(o[j], c[j])), float(max(o[j], c[j])), j)
            return Zone(float(l[j]), float(h[j]), j)
    return None


def intersect(a: Zone, b: Zone) -> Optional[Zone]:
    lo, hi = max(a.low, b.low), min(a.high, b.high)
    if lo > hi + EPS:
        return None
    return Zone(lo, max(lo, hi), a.index)


def is_inside(inner: Zone, outer: Zone) -> bool:
    return inner.low >= outer.low - EPS and inner.high <= outer.high + EPS


# --------------------------------------------------------------------------------------------
# Zone state tracking
# --------------------------------------------------------------------------------------------
def zone_state(direction: int, zone: Zone, h: np.ndarray, l: np.ndarray, c: np.ndarray,
               first: int, last: int) -> str:
    """State of a demand (buy) / supply (sell) zone given bars first..last (inclusive)."""
    if last < first:
        return NEW
    if direction > 0:
        if (c[first:last + 1] < zone.low - EPS).any():
            return INVALIDATED
        m = l[first:last + 1].min()
        if m <= zone.low + EPS:
            return FULLY_MITIGATED
        if m <= zone.high + EPS:
            return PARTIALLY_MITIGATED
        return VALID
    if (c[first:last + 1] > zone.high + EPS).any():
        return INVALIDATED
    m = h[first:last + 1].max()
    if m >= zone.high - EPS:
        return FULLY_MITIGATED
    if m >= zone.low - EPS:
        return PARTIALLY_MITIGATED
    return VALID


# --------------------------------------------------------------------------------------------
# Prices
# --------------------------------------------------------------------------------------------
def round_to_tick(price: float, tick: float) -> float:
    return round(round(price / tick) * tick, 10)


def floor_to_tick(price: float, tick: float) -> float:
    return round(math.floor(price / tick + 1e-9) * tick, 10)


def ceil_to_tick(price: float, tick: float) -> float:
    return round(math.ceil(price / tick - 1e-9) * tick, 10)


def entry_price(direction: int, zone: Zone, depth: float, tick: float) -> Optional[float]:
    """Entry inside the allowed zone. depth 0 = proximal edge, 1 = distal edge [U configurable].

    Returns None when no tick-aligned price exists inside the zone.
    """
    if direction > 0:
        raw = zone.high - depth * (zone.high - zone.low)
    else:
        raw = zone.low + depth * (zone.high - zone.low)
    lo_t, hi_t = ceil_to_tick(zone.low, tick), floor_to_tick(zone.high, tick)
    if lo_t > hi_t + EPS:
        return None
    return min(max(round_to_tick(raw, tick), lo_t), hi_t)


def stop_loss_price(direction: int, ob: Zone, impulse_lo: float, impulse_hi: float, anchor: str,
                    buffer: float, tick: float, spread_add: float = 0.0) -> float:
    """SL beyond the structural invalidation, rounded away from the entry."""
    if direction > 0:
        if anchor == "OB_DISTAL":
            base = ob.low
        elif anchor == "IMPULSE_ORIGIN":
            base = impulse_lo
        else:
            base = min(ob.low, impulse_lo)
        return floor_to_tick(base - buffer, tick)
    if anchor == "OB_DISTAL":
        base = ob.high
    elif anchor == "IMPULSE_ORIGIN":
        base = impulse_hi
    else:
        base = max(ob.high, impulse_hi)
    return ceil_to_tick(base + buffer + spread_add, tick)
