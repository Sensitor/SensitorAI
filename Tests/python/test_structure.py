"""Swings, breaks (BOS/CHoCH), trend, sweeps and the no-lookahead property."""
import numpy as np
import pytest

from sensitor.structure import (BEAR, BULL, NEUTRAL, BREAK_DOWN, BREAK_UP, SWEEP_HIGH, SWEEP_LOW,
                                SWING_HIGH, SWING_LOW, StructureTracker, combine_bias, is_swing_high,
                                is_swing_low)


def bars(rows):
    a = np.array(rows, dtype=float)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]


def run(rows, left=2, right=2, flip="FLIP_ON_CHOCH"):
    o, h, l, c = bars(rows)
    trk = StructureTracker(o, h, l, c, np.full(len(o), 1.0), left, right, 0.0, flip)
    per_bar = [trk.update(k) for k in range(len(o))]
    return trk, per_bar


# ---------------------------------------------------------------------------------------------
def test_swing_high_strict_left_non_strict_right():
    h = np.array([1, 2, 5, 5, 3, 2], dtype=float)
    assert is_swing_high(h, 2, 2, 2)          # first of two equal highs
    assert not is_swing_high(h, 3, 2, 2)      # left side not strictly lower
    l = np.array([5, 4, 1, 1, 3, 4], dtype=float)
    assert is_swing_low(l, 2, 2, 2)
    assert not is_swing_low(l, 3, 2, 2)


def test_swing_needs_full_window():
    h = np.array([1, 2, 5, 4], dtype=float)
    assert not is_swing_high(h, 2, 2, 2)      # only one bar on the right


# Scenario (Tests/python/synth.py): swing high 103 at bar 3 (confirmed bar 5), swing low 99 at
# bar 7 (confirmed bar 9), bar 10 closes 104.2 > 103 => BREAK_UP (BOS from neutral).
from synth import SCEN


def test_swing_confirmation_times_and_bos():
    trk, per_bar = run(SCEN[:11])
    sh = [e for e in trk.events if e.kind == SWING_HIGH]
    sl = [e for e in trk.events if e.kind == SWING_LOW]
    assert [(e.pivot, e.bar, e.price) for e in sh] == [(3, 5, 103.0)]
    assert [(e.pivot, e.bar, e.price) for e in sl] == [(7, 9, 99.0)]
    br = [e for e in trk.events if e.kind == BREAK_UP]
    assert [(e.bar, e.price, e.pivot, e.label) for e in br] == [(10, 103.0, 3, "BOS")]
    assert trk.trend_at[9] == NEUTRAL and trk.trend_at[10] == BULL
    assert trk.ref_high is None            # consumed by the break


def test_wick_beyond_level_is_a_sweep_not_a_break():
    rows2 = SCEN[:9] + [(100.9, 103.5, 100.8, 102.9)]   # wick to 103.5, close 102.9 < 103
    trk2, _ = run(rows2)
    assert not any(e.kind == BREAK_UP for e in trk2.events)
    sw = [e for e in trk2.events if e.kind == SWEEP_HIGH]
    assert [(e.bar, e.price) for e in sw] == [(9, 103.0)]
    assert trk2.ref_high is not None and trk2.ref_high.price == 103.0   # structure level kept
    assert trk2.liq_highs == []                                          # liquidity taken


def test_choch_label_and_flip_modes():
    down_then_up = SCEN[:11] + [
        (104.2, 104.3, 103.0, 103.2),
        (103.2, 103.4, 98.0, 98.5),     # closes below swing low 99 => BREAK_DOWN, CHoCH (trend was BULL)
    ]
    trk, _ = run(down_then_up)
    bd = [e for e in trk.events if e.kind == BREAK_DOWN]
    assert [(e.bar, e.price, e.label) for e in bd] == [(12, 99.0, "CHOCH")]
    assert trk.trend == BEAR
    trk2, _ = run(down_then_up, flip="NEUTRAL_ON_CHOCH")
    assert trk2.trend == NEUTRAL


def test_sweep_low_event():
    rows = SCEN[:10] + [(102.6, 102.9, 98.8, 99.5)]   # wick under swing low 99.0, close back above
    trk, _ = run(rows)
    assert [(e.bar, e.price) for e in trk.events if e.kind == SWEEP_LOW] == [(10, 99.0)]
    assert not any(e.kind == BREAK_DOWN for e in trk.events)


def test_no_lookahead_truncation_invariance():
    rng = np.random.default_rng(3)
    n = 400
    c = 100 + np.cumsum(rng.normal(0, 0.5, n))
    o = np.concatenate(([100.0], c[:-1]))
    h = np.maximum(o, c) + rng.uniform(0, 0.4, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.4, n)
    rows = list(zip(o, h, l, c))
    full, _ = run(rows, 3, 3)
    for cut in (50, 137, 260, 399):
        part, _ = run(rows[:cut + 1], 3, 3)
        a = [(e.kind, e.bar, e.price, e.pivot) for e in full.events if e.bar <= cut]
        b = [(e.kind, e.bar, e.price, e.pivot) for e in part.events]
        assert a == b
        assert full.trend_at[cut] == part.trend_at[cut]


@pytest.mark.parametrize("h4,h1,mode,exp", [
    (BULL, BULL, "REQUIRE_BOTH", BULL),
    (BEAR, BEAR, "REQUIRE_BOTH", BEAR),
    (BULL, BEAR, "REQUIRE_BOTH", NEUTRAL),
    (BULL, NEUTRAL, "REQUIRE_BOTH", NEUTRAL),
    (NEUTRAL, NEUTRAL, "REQUIRE_BOTH", NEUTRAL),
    (BULL, NEUTRAL, "H4_LEADS", BULL),
    (BULL, BEAR, "H4_LEADS", NEUTRAL),
    (NEUTRAL, BULL, "H4_LEADS", NEUTRAL),
])
def test_combine_bias(h4, h1, mode, exp):
    assert combine_bias(h4, h1, mode) == exp
