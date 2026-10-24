"""Synthetic market data with known, hand-verified structure (shared by Python and MQL5 tests).

Reference BUY scenario on the entry timeframe (prices, indices before the flat prefix):
  - swing high 103.0 at bar 3 (confirmed at bar 5 with R=2)
  - swing low  99.0 at bar 7 (confirmed at bar 9) = impulse origin, bar 7 is the bearish OB
  - bar 10 closes 104.2 > 103.0  => BREAK_UP (BOS)
  - impulse top 105.5 at bar 12, confirmed as swing high at bar 14 => setup confirmed at bar 14
  - FVG m=8: [100.6, 100.8] ; OB bar 7: [99.0, 100.6]
  - OTE (62-79 %) of 99.0 -> 105.5: [100.365, 101.47] ; OB ∩ OTE = [100.365, 100.6] (case B)
  - entry depth 0.5 -> 100.4825 -> 100.48 ; SL = 99.0 - 0.10 = 98.90 ; 1R = 1.58
"""
from __future__ import annotations

import numpy as np

from sensitor.setups import Bars

T0 = (1_700_000_000 // 14400) * 14400   # multiple of 4h

SCEN = [
    (100.0, 100.5, 99.5, 100.2),   # 0
    (100.2, 101.0, 100.0, 100.8),  # 1
    (100.8, 102.0, 100.6, 101.8),  # 2
    (101.8, 103.0, 101.5, 102.5),  # 3  swing high 103.0
    (102.5, 102.8, 101.8, 102.0),  # 4
    (102.0, 102.4, 101.0, 101.2),  # 5  -> confirms swing high @3
    (101.2, 101.5, 100.0, 100.3),  # 6
    (100.3, 100.6, 99.0, 99.4),    # 7  bearish OB, swing low 99.0
    (99.4, 101.0, 99.3, 100.9),    # 8  FVG middle candle (m=8)
    (100.9, 102.8, 100.8, 102.6),  # 9  -> confirms swing low @7
    (102.6, 104.5, 102.0, 104.2),  # 10 BREAK_UP (close 104.2 > 103.0)
    (104.2, 105.0, 103.8, 104.8),  # 11
    (104.8, 105.5, 104.5, 105.2),  # 12 impulse top 105.5
    (105.2, 105.3, 104.0, 104.3),  # 13
    (104.3, 104.6, 103.5, 103.8),  # 14 -> confirms swing high @12 => SETUP
]
FLAT = (100.0, 100.6, 99.2, 100.0)
PREFIX = 20


def entry_rows(extra=(), prefix: int = PREFIX):
    return [FLAT] * prefix + SCEN + list(extra)


def mirror_rows(rows, k: float = 200.0):
    """Price mirror p -> k - p (turns a buy scenario into the equivalent sell scenario)."""
    return [(k - o, k - l, k - h, k - c) for (o, h, l, c) in rows]


def make_bars(rows, tf: int, end_time: int | None = None, start_time: int | None = None) -> Bars:
    a = np.array(rows, dtype=float)
    n = len(a)
    if start_time is None:
        start_time = end_time - n * tf * 60
    t = start_time + np.arange(n, dtype=np.int64) * tf * 60
    return Bars(tf, t, a[:, 0].copy(), a[:, 1].copy(), a[:, 2].copy(), a[:, 3].copy())


def zigzag_rows(points, up_bars=10, down_bars=5, w=0.1):
    """OHLC rows following straight legs between pivot prices; peaks/troughs are strict swings."""
    rows = []
    prev = points[0]
    for a, b in zip(points[:-1], points[1:]):
        n = up_bars if b > a else down_bars
        for i in range(n):
            c = a + (b - a) * (i + 1) / n
            o = prev
            up = c > o
            h = max(o, c) + (w if up else w / 2)
            l = min(o, c) - (w if not up else w / 2)
            rows.append((o, h, l, c))
            prev = c
    return rows


BULL_POINTS = [100, 110, 105, 115, 110, 120]


def htf_bars(bullish: bool = True, end_time: int = T0):
    rows = zigzag_rows(BULL_POINTS)
    if not bullish:
        rows = mirror_rows(rows, 220.0)
    return make_bars(rows, 60, end_time=end_time), make_bars(rows, 240, end_time=end_time)


def scenario(extra=(), sell: bool = False, h1_bull: bool | None = None, h4_bull: bool | None = None):
    """(entry M15 bars, H1 bars, H4 bars). HTF bars all close before the first entry bar."""
    rows = entry_rows(extra)
    if sell:
        rows = mirror_rows(rows)
    entry = make_bars(rows, 15, start_time=T0)
    h1_bull = (not sell) if h1_bull is None else h1_bull
    h4_bull = (not sell) if h4_bull is None else h4_bull
    h1, _ = htf_bars(h1_bull)
    _, h4 = htf_bars(h4_bull)
    return entry, h1, h4
