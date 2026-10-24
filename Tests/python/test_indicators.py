"""Indicators: expected values computed by hand before execution."""
import math

import numpy as np
import pytest

from sensitor.indicators import atr_sma, rsi_mt5, rsi_window_blocks, true_range


def test_true_range_uses_previous_close():
    h = np.array([10.0, 12.0, 11.0])
    l = np.array([9.0, 11.0, 8.0])
    c = np.array([9.5, 11.5, 10.0])
    # TR0 = 1 ; TR1 = max(12,9.5)-min(11,9.5) = 2.5 ; TR2 = max(11,11.5)-min(8,11.5) = 3.5
    assert true_range(h, l, c).tolist() == [1.0, 2.5, 3.5]


def test_atr_is_simple_average_like_mt5():
    n = 20
    h = np.full(n, 11.0)
    l = np.full(n, 10.0)
    c = np.full(n, 10.5)
    a = atr_sma(h, l, c, 14)
    assert np.isnan(a[:14]).all()
    assert a[14] == pytest.approx(1.0)
    # one wider bar enters then leaves the 14-bar window
    h2 = h.copy(); h2[15] = 13.0          # TR15 = 3.0
    a2 = atr_sma(h2, l, c, 14)
    assert a2[15] == pytest.approx((13 * 1.0 + 3.0) / 14)
    assert a2[19] == pytest.approx((13 * 1.0 + 3.0) / 14)


def test_rsi_monotonic_up_is_100_and_down_is_0():
    up = np.arange(30, dtype=float)
    r = rsi_mt5(up, 14)
    assert np.isnan(r[:14]).all()
    assert r[14] == 100.0 and r[-1] == 100.0
    down = up[::-1].copy()
    assert rsi_mt5(down, 14)[-1] == pytest.approx(0.0)


def test_rsi_flat_is_50():
    assert rsi_mt5(np.full(20, 5.0), 14)[-1] == 50.0


def test_rsi_seed_and_wilder_step():
    # 14 changes: 7 x +1, 7 x -1 => seed avg gain = avg loss = 0.5 => RSI 50
    c = [100.0]
    for i in range(14):
        c.append(c[-1] + (1.0 if i % 2 == 0 else -1.0))
    c.append(c[-1] + 2.0)  # change +2 at index 15
    r = rsi_mt5(np.array(c), 14)
    assert r[14] == pytest.approx(50.0)
    pos = (0.5 * 13 + 2.0) / 14
    neg = (0.5 * 13) / 14
    assert r[15] == pytest.approx(100 - 100 / (1 + pos / neg))


@pytest.mark.parametrize("vals,direction,blocked", [
    ([60, 65, 69.99, 50, 55], 1, False),
    ([60, 65, 70.0, 50, 55], 1, True),        # exactly 70 blocks a buy [U]
    ([40, 35, 30.01, 45, 50], -1, False),
    ([40, 35, 30.0, 45, 50], -1, True),       # exactly 30 blocks a sell [U]
    ([75, 40, 40, 40, 40, 40], 1, False),     # 75 is 6 bars back: outside the 5-bar window
])
def test_rsi_window_rule(vals, direction, blocked):
    r = np.array(vals, dtype=float)
    b, _ = rsi_window_blocks(r, len(r) - 1, 5, direction, 70, 30)
    assert b is blocked


def test_rsi_window_insufficient_data_blocks():
    r = np.array([np.nan, 50, 50, 50, 50])
    assert rsi_window_blocks(r, 4, 5, 1)[0] is True
