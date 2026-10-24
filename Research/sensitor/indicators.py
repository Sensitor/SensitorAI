"""Indicators replicating the exact MetaTrader 5 reference algorithms.

- ATR: MT5 `ATR.mq5` = simple moving average of the True Range (NOT Wilder smoothing).
- RSI: MT5 `RSI.mq5` = Wilder smoothing seeded with a simple average of the first `period` changes.

The MQL5 port lives in MQL5/Include/SensitorAI/Indicators.mqh and is tested against the same
fixtures. Values before the warm-up are NaN.
"""
from __future__ import annotations

import math

import numpy as np


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    n = len(high)
    tr = np.empty(n)
    if n == 0:
        return tr
    tr[0] = high[0] - low[0]
    if n > 1:
        prev_c = close[:-1]
        tr[1:] = np.maximum(high[1:], prev_c) - np.minimum(low[1:], prev_c)
    return tr


def atr_sma(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """ATR as in MT5: mean of TR[i-period+1 .. i] for i >= period (TR[0] is never used)."""
    tr = true_range(high, low, close)
    n = len(tr)
    out = np.full(n, np.nan)
    if n <= period:
        return out
    csum = np.cumsum(np.concatenate(([0.0], tr)))
    i = np.arange(period, n)
    out[period:] = (csum[i + 1] - csum[i + 1 - period]) / period
    return out


def rsi_mt5(close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    out = np.full(n, np.nan)
    if n <= period:
        return out
    sum_pos = 0.0
    sum_neg = 0.0
    for i in range(1, period + 1):
        d = close[i] - close[i - 1]
        if d > 0:
            sum_pos += d
        elif d < 0:
            sum_neg -= d
    pos = sum_pos / period
    neg = sum_neg / period
    out[period] = _rsi_value(pos, neg)
    for i in range(period + 1, n):
        d = close[i] - close[i - 1]
        pos = (pos * (period - 1) + (d if d > 0 else 0.0)) / period
        neg = (neg * (period - 1) + (-d if d < 0 else 0.0)) / period
        out[i] = _rsi_value(pos, neg)
    return out


def _rsi_value(pos: float, neg: float) -> float:
    if neg != 0.0:
        return 100.0 - 100.0 / (1.0 + pos / neg)
    return 100.0 if pos != 0.0 else 50.0


def rsi_window_blocks(rsi: np.ndarray, k: int, window: int, direction: int,
                      overbought: float = 70.0, oversold: float = 30.0) -> tuple[bool, float]:
    """RSI exclusion rule [U].

    Returns (blocked, extreme_value) for the `window` last closed bars ending at index k inclusive.
    Buy (direction=+1): blocked if max(RSI) >= overbought. Sell: blocked if min(RSI) <= oversold.
    Insufficient data (NaN in window or k < window-1) => blocked (conservative).
    """
    if k < window - 1:
        return True, math.nan
    w = rsi[k - window + 1:k + 1]
    if np.isnan(w).any():
        return True, math.nan
    if direction > 0:
        m = float(w.max())
        return m >= overbought, m
    m = float(w.min())
    return m <= oversold, m
