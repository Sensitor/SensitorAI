"""Generic executor of cycle 4 (market / stop / OCO entries, SL, TP, time exit)."""
import numpy as np
import pytest

from sensitor.config import CostModel
from sensitor.families import Executor, Spec
from test_simulator import m1, T0

C = CostModel(commission_per_lot_rt=0.0, swap_long_per_lot=0.0, swap_short_per_lot=0.0,
              stop_slippage=0.10, partial_slippage=0.0)


def test_market_entry_tp():
    d = m1([(100.0, 100.2, 99.9, 100.1), (100.1, 101.0, 100.0, 100.9), (100.9, 102.5, 100.8, 102.4)])
    r = Executor(d, C).run(Spec(1, T0, sl_dist=1.0, tp_r=2.0))
    # fill 100.0 + 0.10 = 100.10 ; SL 99.10 ; TP 102.10 hit on bar 2
    assert r["exit"] == "TP" and r["r_gross"] == pytest.approx(2.0)


def test_market_entry_stop_with_slippage():
    d = m1([(100.0, 100.2, 99.9, 100.1), (100.1, 100.2, 99.0, 99.2)])
    r = Executor(d, C).run(Spec(1, T0, sl_dist=1.0))
    assert r["exit"] == "SL" and r["r_gross"] == pytest.approx(-1.10)


def test_stop_entry_and_time_exit():
    d = m1([(100.0, 100.3, 99.9, 100.2), (100.2, 100.8, 100.1, 100.7), (100.7, 100.9, 100.6, 100.8),
            (100.8, 100.9, 100.7, 100.85)])
    s = Spec(1, T0, "stop", 100.5, T0 + 240, sl_abs=99.5, t_exit=T0 + 180)
    r = Executor(d, C).run(s)
    # triggered bar 1 at 100.5 (+0.10) = 100.6 ; R = 1.1 ; exit at open of bar 3 (100.8) - 0.10
    assert r["fill_time"] == T0 + 60 and r["exit"] == "TIME"
    assert r["r_gross"] == pytest.approx((100.7 - 100.6) / 1.1)


def test_oco_takes_first_trigger_short():
    d = m1([(100.0, 100.1, 99.9, 100.0), (100.0, 100.05, 99.0, 99.1), (99.1, 99.2, 97.0, 97.1)])
    long = Spec(1, T0, "stop", 100.5, T0 + 600, sl_abs=99.5, tp_r=1.0)
    long.oco = Spec(-1, T0, "stop", 99.5, T0 + 600, sl_abs=100.5, tp_r=1.0)
    r = Executor(d, C).run(long)
    # short fills at 99.5 - 0.10 = 99.40 ; R = 1.10 ; TP = 98.30 reached bar 2
    assert r["direction"] == -1 and r["exit"] == "TP" and r["r_gross"] == pytest.approx(1.0)


def test_run_all_no_overlap():
    d = m1([(100.0, 100.2, 99.9, 100.1)] * 10)
    specs = [Spec(1, T0, sl_dist=1.0, t_exit=T0 + 300), Spec(1, T0 + 120, sl_dist=1.0, t_exit=T0 + 400),
             Spec(1, T0 + 360, sl_dist=1.0, t_exit=T0 + 480)]
    out = Executor(d, C).run_all(specs)
    assert list(out["fill_time"]) == [T0, T0 + 360]
