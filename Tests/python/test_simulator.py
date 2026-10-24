"""Execution simulator on hand-written M1 candles. Buy: entry 100.00, SL 99.00 (1R = 1.00).

Costs: commission 0, swaps 0, stop slippage 0.10, partial slippage 0.05 unless stated.
"""
import math

import numpy as np
import pytest

from sensitor.config import CostModel, StrategyConfig
from sensitor.data import MinuteData
from sensitor.setups import Setup
from sensitor.simulator import Simulator
from sensitor.structure import BREAK_DOWN, SWING_LOW, Event

T0 = 1_700_006_400   # Tuesday 2023-11-14 00:00 UTC
COSTS = CostModel(commission_per_lot_rt=0.0, swap_long_per_lot=0.0, swap_short_per_lot=0.0,
                  stop_slippage=0.10, partial_slippage=0.05)
CFG = StrategyConfig(runner_method="FIXED_R", runner_target_r=5.0)


def m1(bid_rows, spread=0.0, start=T0, step=60):
    """bid_rows: (o, h, l, c). Ask = bid + spread."""
    a = np.array(bid_rows, dtype=float)
    n = len(a)
    t = start + np.arange(n, dtype=np.int64) * step
    return MinuteData(t, a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 0] + spread, a[:, 1] + spread,
                      a[:, 2] + spread, a[:, 3] + spread, server_offset=np.full(n, 7200, dtype=np.int64))


def setup(direction=1, entry=100.0, sl=99.0, place_time=T0, end_time=-1, tp_liq=math.nan):
    return Setup(id="X", direction=direction, break_bar=0, break_time=0, break_label="BOS",
                 broken_level=0, broken_pivot=0, origin_idx=0, origin_price=0, extreme_idx=0,
                 extreme_price=0, confirm_bar=0, confirm_time=place_time, bias_h4=direction,
                 bias_h1=direction, atr=1.0, spread=0.0, entry=entry, sl=sl,
                 risk_dist=abs(entry - sl), tp_liquidity=tp_liq, place_bar=0,
                 place_time=place_time, end_time=end_time)


def sim(data, cfg=CFG, costs=COSTS, events=(), entry_close_times=None, atr=None):
    ect = entry_close_times if entry_close_times is not None else np.array([T0], dtype=np.int64)
    at = atr if atr is not None else np.zeros(max(len(ect), 1))
    return Simulator(data, cfg, costs, 0.01, ect, list(events), at, 15)


FILL = (100.5, 100.6, 99.95, 100.2)   # ask (spread 0) dips to 99.95 => buy limit 100 filled


def test_fill_then_stop():
    d = m1([(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 100.3, 98.9, 99.0)])
    r = sim(d).run(setup())
    assert r.outcome == "CLOSED" and r.fill_time == T0 + 60 and r.fill_price == 100.0
    assert r.exit_reason == "SL"
    assert r.r_gross == pytest.approx(-1.10)       # 99.00 - 0.10 slippage


def test_gap_fill_at_better_open():
    d = m1([(100.5, 100.6, 100.3, 100.4), (99.8, 100.2, 99.7, 100.1), (100.1, 100.2, 98.0, 98.5)])
    r = sim(d).run(setup())
    assert r.fill_price == pytest.approx(99.8) and r.risk_dist == pytest.approx(0.8)


def test_break_even_then_stopped_at_entry():
    d = m1([(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 101.05, 100.1, 101.0),
            (101.0, 101.1, 99.9, 100.0)])
    r = sim(d).run(setup())
    assert r.be_time == T0 + 120
    assert r.exit_reason == "BE" and r.r_gross == pytest.approx(-0.10)


def test_partial_then_fixed_target():
    d = m1([(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 101.2, 100.1, 101.1),
            (101.1, 103.1, 101.0, 103.0), (103.0, 105.1, 102.9, 105.0)])
    r = sim(d).run(setup())
    assert r.partial_time == T0 + 180 and r.partial_price == pytest.approx(102.95)
    assert r.exit_reason == "TP" and r.exit_price == pytest.approx(105.0)
    assert r.r_gross == pytest.approx(0.5 * 2.95 + 0.5 * 5.0)
    assert r.r_partial_leg == pytest.approx(2.95) and r.r_runner_leg == pytest.approx(5.0)


def test_six_r_target():
    d = m1([(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 103.2, 100.1, 103.1),
            (103.1, 105.1, 103.0, 105.0), (105.0, 106.1, 104.9, 106.0)])
    r = sim(d, CFG.replace(runner_target_r=6.0)).run(setup())
    assert r.exit_reason == "TP" and r.r_gross == pytest.approx(0.5 * 2.95 + 0.5 * 6.0)


def test_same_candle_stop_and_target_is_pessimistic():
    d = m1([(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 106.0, 98.5, 105.0)])
    r = sim(d).run(setup())
    assert r.exit_reason == "SL" and r.r_gross == pytest.approx(-1.10)


def test_fill_candle_only_checks_stop():
    d = m1([(100.5, 100.6, 100.3, 100.4), (100.5, 105.5, 99.95, 101.0), (101.0, 101.1, 100.9, 101.0)])
    r = sim(d).run(setup())
    assert r.partial_time == -1 and r.be_time == T0 + 120   # BE only from the next candle (high 101.1)


def test_cancelled_before_fill():
    d = m1([(100.5, 100.6, 100.3, 100.4), (100.4, 100.5, 100.1, 100.2), FILL])
    r = sim(d).run(setup(end_time=T0 + 120))
    assert r.outcome == "CANCELLED"


def test_missed_at_placement_never_chases():
    d = m1([(99.9, 100.1, 99.8, 100.0), (100.0, 101.0, 99.9, 100.8)])
    r = sim(d).run(setup())
    assert r.outcome == "MISSED_AT_PLACEMENT" and r.fill_time == -1


def test_buy_fills_on_ask_not_bid():
    # bid low 99.96 but spread 0.05 => ask low 100.01 > 100 : no fill
    d = m1([(100.5, 100.6, 100.3, 100.4), (100.5, 100.6, 99.96, 100.2)], spread=0.05)
    assert sim(d).run(setup()).outcome == "NOT_FILLED_END"


def test_sell_mirror_stop_on_ask():
    # sell 100.00, SL 101.00. Bid rises to 100.05 => filled ; ask (bid+0.05) reaches 101.00 => stopped
    d = m1([(99.5, 99.6, 99.4, 99.5), (99.8, 100.05, 99.7, 99.9), (100.0, 100.95, 99.9, 100.9)],
           spread=0.05)
    r = sim(d).run(setup(direction=-1, entry=100.0, sl=101.0))
    assert r.fill_price == 100.0 and r.exit_reason == "SL"
    assert r.r_gross == pytest.approx(-1.10)


def test_sell_partial_and_target():
    d = m1([(99.5, 99.6, 99.4, 99.5), (99.8, 100.05, 99.7, 99.9), (99.9, 99.9, 98.9, 99.0),
            (99.0, 99.0, 96.9, 97.0), (97.0, 97.0, 94.9, 95.0)])
    r = sim(d).run(setup(direction=-1, entry=100.0, sl=101.0))
    assert r.exit_reason == "TP" and r.r_gross == pytest.approx(0.5 * 2.95 + 0.5 * 5.0)


def test_runner_structure_exit_after_partial():
    rows = [(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 103.1, 100.1, 103.0),
            (103.0, 103.5, 102.9, 103.4), (103.4, 103.6, 103.3, 103.5), (103.5, 103.7, 103.4, 103.6)]
    d = m1(rows)
    # entry-TF bearish break known at T0+240 (close of an entry bar) => exit at the open of that minute
    ect = np.array([T0 + 240], dtype=np.int64)
    ev = [Event(BREAK_DOWN, 0, 103.0, 0)]
    r = sim(d, CFG.replace(runner_method="STRUCTURE"), events=ev, entry_close_times=ect).run(setup())
    assert r.exit_reason == "STRUCTURE_BREAK" and r.exit_time == T0 + 240
    # the minute starting at T0+240 is row 4, open 103.4
    assert r.r_gross == pytest.approx(0.5 * 2.95 + 0.5 * (103.4 - 0.10 - 100.0))


def test_runner_trailing_moves_stop_only_tighter():
    rows = [(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 103.1, 100.1, 103.0),
            (103.0, 104.0, 102.9, 103.9), (103.9, 104.2, 103.8, 104.1), (104.1, 104.2, 102.4, 102.5)]
    d = m1(rows)
    ect = np.array([T0 + 180, T0 + 240], dtype=np.int64)
    ev = [Event(SWING_LOW, 0, 101.0, 0), Event(SWING_LOW, 1, 102.5, 0)]
    cfg = CFG.replace(runner_method="TRAILING", trailing_buffer_atr=0.0)
    r = sim(d, cfg, events=ev, entry_close_times=ect, atr=np.zeros(2)).run(setup())
    # swing 101.0 (known T0+180) tightens BE (100) -> 101.0 ; swing 102.5 (T0+240) -> 102.5
    assert r.exit_reason == "TRAIL_SL"
    assert r.r_gross == pytest.approx(0.5 * 2.95 + 0.5 * (102.5 - 0.10 - 100.0))


def test_liquidity_target_used_when_beyond_partial():
    d = m1([(100.5, 100.6, 100.3, 100.4), FILL, (100.2, 103.1, 100.1, 103.0),
            (103.0, 104.3, 102.9, 104.2)])
    r = sim(d, CFG.replace(runner_method="LIQUIDITY")).run(setup(tp_liq=104.25))
    assert r.exit_reason == "TP" and r.exit_price == pytest.approx(104.25)


def test_commission_and_swap_in_r():
    costs = COSTS.replace(commission_per_lot_rt=7.0, swap_long_per_lot=-40.0)
    # fill Tuesday 00:01 UTC (02:01 server), stopped Thursday 00:02 UTC => crosses Tue and Wed
    # server midnights: 1 + 3 (Wednesday triple) = 4 nights
    rows = [(100.5, 100.6, 100.3, 100.4), FILL]
    d = m1(rows + [(100.2, 100.3, 98.9, 99.0)], start=T0)
    d.time[2] = T0 + 2 * 86400 + 120
    r = sim(d, costs=costs).run(setup())
    assert r.nights == 4
    assert r.r_commission == pytest.approx(-7.0 / (1.0 * 100))
    assert r.r_swap == pytest.approx(4 * -40.0 / 100.0)
    assert r.r_net == pytest.approx(-1.10 - 0.07 - 1.6)
