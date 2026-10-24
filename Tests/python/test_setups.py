"""End-to-end signal engine on the hand-built scenario of synth.py (expected values in synth.py)."""
import math

import numpy as np
import pytest

from sensitor.config import StrategyConfig
from sensitor.indicators import rsi_mt5
from sensitor.setups import Bars, SetupEngine
from synth import PREFIX, T0, mirror_rows, scenario, make_bars

BASE = StrategyConfig(entry_tf=15, rsi_mode="OFF", sl_buffer_points=10, sl_buffer_atr=0.0,
                      caution_sweep_action="LOG_ONLY", entry_depth=0.5)
SPREAD = 0.05


def run(cfg=BASE, extra=(), sell=False, **kw):
    e, h1, h4 = scenario(extra, sell=sell, **kw)
    eng = SetupEngine(cfg, e, h1, h4, lambda t: SPREAD, tick=0.01)
    eng.run()
    return eng


def only(eng):
    assert len(eng.setups) == 1, [ (s.id, s.status, s.reason) for s in eng.setups]
    return eng.setups[0]


def test_buy_setup_frozen_levels():
    eng = run()
    s = only(eng)
    assert s.direction == 1 and s.status == "SETUP_VALID"
    assert s.break_bar == PREFIX + 10 and s.break_label == "BOS" and s.broken_level == 103.0
    assert s.confirm_bar == PREFIX + 14 and s.confirm_time == T0 + (PREFIX + 15) * 900
    assert (s.origin_idx, s.origin_price) == (PREFIX + 7, 99.0)
    assert (s.extreme_idx, s.extreme_price) == (PREFIX + 12, 105.5)
    assert s.ote_low == pytest.approx(100.365) and s.ote_high == pytest.approx(101.47)
    assert (s.fvg_low, s.fvg_high, s.fvg_mid_idx) == (100.6, 100.8, PREFIX + 8)
    assert (s.ob_low, s.ob_high, s.ob_idx) == (99.0, 100.6, PREFIX + 7)
    assert s.zone_low == pytest.approx(100.365) and s.zone_high == pytest.approx(100.6)
    assert s.entry_case == "B"
    assert s.entry == pytest.approx(100.48)
    assert s.sl == pytest.approx(98.90)
    assert s.risk_dist == pytest.approx(1.58)
    assert s.place_bar == PREFIX + 14
    # no H1 liquidity above entry+3R (all HTF highs broken) -> fallback 6R
    assert s.tp_liquidity_is_fallback and s.tp_liquidity == pytest.approx(100.48 + 6 * 1.58)
    assert s.end_reason == ""


def test_sell_setup_is_exact_mirror():
    cfg = BASE.replace(sl_add_spread_for_sells=False)
    s = only(run(cfg, sell=True))
    assert s.direction == -1 and s.status == "SETUP_VALID"
    assert s.origin_price == 101.0 and s.extreme_price == pytest.approx(94.5)
    assert s.ote_low == pytest.approx(98.53) and s.ote_high == pytest.approx(99.635)
    assert (s.ob_low, s.ob_high) == pytest.approx((99.4, 101.0))
    assert (s.fvg_low, s.fvg_high) == pytest.approx((99.2, 99.4))
    assert s.entry == pytest.approx(99.52)
    assert s.sl == pytest.approx(101.10)
    assert s.entry_case == "B"


def test_sell_sl_includes_spread():
    s = only(run(sell=True))
    assert s.sl == pytest.approx(101.15)          # 101.0 + 0.10 buffer + 0.05 spread


@pytest.mark.parametrize("entry_depth,expected", [(0.0, 100.60), (0.5, 100.48), (1.0, 100.37)])
def test_entry_depth_variants(entry_depth, expected):
    s = only(run(BASE.replace(entry_depth=entry_depth)))
    assert s.entry == pytest.approx(expected)


def test_invalidation_by_close_beyond_impulse_top():
    s = only(run(extra=[(103.8, 105.7, 103.6, 105.6)]))
    assert s.status == "INVALIDATED" and s.end_reason == "INV_CONTINUATION"
    assert s.end_bar == PREFIX + 15


def test_wick_beyond_top_close_vs_wick_mode():
    wick_bar = [(103.8, 105.7, 103.6, 105.0)]           # high 105.7 > 105.5, close 105.0 < 105.5
    s = only(run(extra=wick_bar))
    assert s.status == "SETUP_VALID"                     # CLOSE mode: a wick does not invalidate
    s2 = only(run(BASE.replace(continuation_invalidation="WICK"), extra=wick_bar))
    assert s2.end_reason == "INV_CONTINUATION"


def test_deep_failure_close_below_origin():
    s = only(run(extra=[(103.8, 103.9, 98.5, 98.7)]))     # gap through entry and origin
    assert s.end_reason == "INV_DEEP_FAILURE"


def test_sell_invalidation_by_new_low():
    # `scenario(sell=True)` mirrors every row, extras included: pass the BUY-space bar
    s = only(run(extra=[(103.8, 105.7, 103.6, 105.6)], sell=True))
    assert s.end_reason == "INV_CONTINUATION"


def test_no_setup_when_htf_contradict():
    eng = run(h1_bull=False, h4_bull=True)
    assert eng.setups == []
    assert any(d.code == "BREAK_IGNORED_BIAS" for d in eng.decisions)


def test_bias_change_cancels_pending():
    """H1 turns bearish ~2h15 after the setup is confirmed => INV_BIAS_CHANGED at the next entry close."""
    quiet = [(104.0, 104.2, 103.9, 104.0)] * 40          # 10 h of neutral entry bars (no invalidation)
    e, h1, h4 = scenario(extra=quiet)
    rows = [(h1.o[i], h1.h[i], h1.l[i], h1.c[i]) for i in range(len(h1))]
    # 10 calm H1 bars after T0, then one bar closing at T0+11h far below the last H1 swing low (109.9)
    calm = [(119.0, 119.05, 118.9, 119.0)] * 10
    crash = [(119.0, 119.05, 100.0, 100.5)]
    h1b = make_bars(rows + calm + crash, 60, start_time=int(h1.time[0]))
    eng = SetupEngine(BASE, e, h1b, h4, lambda t: SPREAD, tick=0.01)
    eng.run()
    s = only(eng)
    assert s.confirm_time == T0 + (PREFIX + 15) * 900          # 8h45 after T0, bias still bullish
    assert s.end_reason == "INV_BIAS_CHANGED"
    assert s.end_time == T0 + 11 * 3600                        # first entry close after the H1 close


def test_rsi_at_setup_matches_window_rule():
    cfg = BASE.replace(rsi_mode="AT_SETUP")
    eng = run(cfg)
    s = only(eng)
    e, _, _ = scenario()
    rsi = rsi_mt5(e.c, 14)
    k = PREFIX + 14
    blocked = np.nanmax(rsi[k - 4:k + 1]) >= 70
    assert (s.status == "REJECTED" and s.reason == "REJECT_RSI") == bool(blocked)
    assert s.rsi_extreme == pytest.approx(float(np.max(rsi[k - 4:k + 1])))


def test_rsi_off_keeps_setup():
    assert only(run(BASE.replace(rsi_mode="OFF"))).status == "SETUP_VALID"


def test_bos_bar_anchor():
    s = only(run(BASE.replace(impulse_anchor="BOS_BAR")))
    assert s.confirm_bar == PREFIX + 10
    assert s.extreme_price == 104.5
    assert s.ote_low == pytest.approx(100.155) and s.ote_high == pytest.approx(101.09)
    assert s.entry == pytest.approx(100.38)
    assert s.sl == pytest.approx(98.90)


def test_touched_before_placement_is_missed():
    # with RSI gating the placement is delayed; a dip to the entry before it => MISSED
    cfg = BASE.replace(rsi_mode="GATE_PLACEMENT", rsi_overbought=101.0)   # never blocks
    s = only(run(cfg))
    assert s.status == "SETUP_VALID"
    # direct check of the rule: a bar touching 100.48 between the top and the placement
    from sensitor.setups import SetupEngine as SE
    e, h1, h4 = scenario()
    e.l[PREFIX + 13] = 100.40
    eng = SE(BASE, e, h1, h4, lambda t: SPREAD, tick=0.01)
    eng.run()
    s2 = eng.setups[0]
    assert s2.status == "MISSED" and s2.reason == "MISSED_TOUCHED_BEFORE_PLACEMENT"


def test_min_sl_distance_rejects():
    e, h1, h4 = scenario()
    eng = SetupEngine(BASE, e, h1, h4, lambda t: 0.60, tick=0.01)   # 3 x 0.60 = 1.80 > 1.58
    eng.run()
    assert eng.setups[0].reason == "REJECT_SL_TOO_TIGHT"


def test_no_lookahead_engine_truncation():
    """Setups confirmed before T on truncated data == same setups on the full data."""
    rng = np.random.default_rng(11)
    n = 6000
    c = 2000 + np.cumsum(rng.normal(0, 0.6, n)) + np.sin(np.arange(n) / 40) * 6
    o = np.concatenate(([2000.0], c[:-1]))
    h = np.maximum(o, c) + rng.uniform(0, 0.6, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.6, n)
    t = T0 + np.arange(n, dtype=np.int64) * 900
    m15 = Bars(15, t, o, h, l, c)

    def agg(b: Bars, k: int, tf: int) -> Bars:
        m = len(b) // k
        return Bars(tf, b.time[: m * k: k], b.o[: m * k: k], b.h[: m * k].reshape(m, k).max(1),
                    b.l[: m * k].reshape(m, k).min(1), b.c[k - 1: m * k: k])

    h1, h4 = agg(m15, 4, 60), agg(m15, 16, 240)
    cfg = StrategyConfig(rsi_mode="AT_SETUP", caution_sweep_action="BLOCK")
    full = SetupEngine(cfg, m15, h1, h4, lambda x: 0.2, tick=0.01)
    full.run()
    assert len(full.setups) > 5
    for cut in (1500, 3000, 4500):
        T = int(m15.close_time[cut])

        def trunc(b: Bars) -> Bars:
            i = b.last_closed_index(T) + 1
            return Bars(b.tf, b.time[:i], b.o[:i], b.h[:i], b.l[:i], b.c[:i])
        part = SetupEngine(cfg, trunc(m15), trunc(h1), trunc(h4), lambda x: 0.2, tick=0.01)
        part.run()
        fa = [x.as_dict() for x in full.setups if x.confirm_time <= T]
        pa = [x.as_dict() for x in part.setups]
        for a in fa:   # lifecycle fields after T are unknown at T
            if a["end_time"] > T:
                a["end_bar"], a["end_time"], a["end_reason"] = -1, -1, ""
                if a["status"] == "INVALIDATED":
                    a["status"] = "SETUP_VALID"
            if a["place_time"] > T:
                a["place_bar"], a["place_time"] = -1, -1
        assert fa == pa
