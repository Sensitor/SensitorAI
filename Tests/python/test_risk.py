"""Volume sizing, partial-close volumes, R and break-even rules."""
import pytest

from sensitor.risk import (break_even_sl, compute_volume, floor_step, partial_close_volume,
                           r_multiple, tighter_sl)


def test_volume_reference_example():
    # 10 000 USD, 1 % => 100 USD. XAU 100 oz/lot, SL distance 5.00 USD => 500 USD per lot
    # raw 0.2 lot ; commission 7 USD/lot => 100/507 = 0.1972 -> 0.19
    assert compute_volume(100.0, 500.0, 0.0, 0.01, 0.01, 100.0) == (0.2, "OK")
    assert compute_volume(100.0, 500.0, 7.0, 0.01, 0.01, 100.0) == (0.19, "OK")


def test_volume_never_rounds_up():
    vol, _ = compute_volume(100.0, 333.0, 0.0, 0.01, 0.01, 100.0)   # raw 0.3003
    assert vol == 0.30 and vol * 333.0 <= 100.0


def test_min_lot_exceeding_risk_is_refused():
    # 100 USD risk, SL 15 USD wide => 1500 USD/lot => raw 0.0667 OK ; with 200 USD/lot*... :
    assert compute_volume(5.0, 600.0, 0.0, 0.01, 0.01, 100.0) == (0.0, "REJECT_MIN_LOT_EXCEEDS_RISK")


def test_volume_capped_by_max_and_limit():
    assert compute_volume(1e6, 100.0, 0.0, 0.01, 0.01, 50.0)[0] == 50.0
    assert compute_volume(1e6, 100.0, 0.0, 0.01, 0.01, 50.0, vlimit=20.0)[0] == 20.0


def test_volume_bad_inputs():
    assert compute_volume(0.0, 500.0, 0.0, 0.01, 0.01, 100)[1] == "REJECT_RISK_MONEY"
    assert compute_volume(100.0, 0.0, 0.0, 0.01, 0.01, 100)[1] == "REJECT_LOSS_PER_LOT"


def test_floor_step_float_safety():
    assert floor_step(0.2999999999999, 0.01) == 0.3   # within EPS -> not degraded to 0.29
    assert floor_step(0.2999, 0.01) == 0.29


@pytest.mark.parametrize("init,cur,exp", [
    (0.20, 0.20, (0.10, "PARTIAL")),
    (0.15, 0.15, (0.07, "PARTIAL")),            # floor(0.075) = 0.07, remainder 0.08
    (0.01, 0.01, (0.01, "FALLBACK_CLOSE_ALL")),  # cannot split the minimum lot
    (0.03, 0.03, (0.01, "PARTIAL")),
])
def test_partial_volume(init, cur, exp):
    assert partial_close_volume(init, cur, 0.5, 0.01, 0.01, "CLOSE_ALL") == exp


def test_partial_volume_keep_all_fallback():
    assert partial_close_volume(0.01, 0.01, 0.5, 0.01, 0.01, "KEEP_ALL") == (0.0, "FALLBACK_KEEP_ALL")


def test_partial_uses_initial_volume_not_current():
    # initial 1.0, current 1.0 -> 0.5 ; if computed on a later current volume it would differ
    assert partial_close_volume(1.0, 1.0, 0.5, 0.1, 0.1)[0] == 0.5


def test_r_multiple_uses_initial_risk():
    assert r_multiple(1, 100.0, 99.0, 103.0) == 3.0
    assert r_multiple(-1, 100.0, 101.0, 97.0) == 3.0
    assert r_multiple(1, 100.0, 99.0, 99.5) == -0.5


def test_break_even_never_widens():
    assert break_even_sl(1, 100.0, 99.0, 0.0, 0.01) == 100.0
    assert break_even_sl(1, 100.0, 100.5, 0.0, 0.01) is None      # current SL already better
    assert break_even_sl(-1, 100.0, 101.0, 0.0, 0.01) == 100.0
    assert break_even_sl(-1, 100.0, 99.5, 0.0, 0.01) is None
    assert tighter_sl(1, 99.0, 99.5) and not tighter_sl(1, 99.5, 99.0)
    assert tighter_sl(-1, 101.0, 100.5) and not tighter_sl(-1, 100.5, 101.0)
