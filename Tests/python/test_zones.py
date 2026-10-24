"""OTE, FVG, OB, intersection, entry price, SL and zone states — hand-computed expectations."""
import numpy as np
import pytest

from sensitor import zones as Z


def test_ote_buy_reference_example():
    z = Z.ote_zone(1, 2000.0, 2010.0)
    assert z.low == pytest.approx(2002.10) and z.high == pytest.approx(2003.80)


def test_ote_sell_reference_example():
    z = Z.ote_zone(-1, 2000.0, 2010.0)
    assert z.low == pytest.approx(2006.20) and z.high == pytest.approx(2007.90)


def test_retracement_convention():
    # 0 = impulse extreme, 1 = origin
    assert Z.retracement_level(1, 2000, 2010, 0.0) == 2010
    assert Z.retracement_level(1, 2000, 2010, 1.0) == 2000
    assert Z.retracement_level(-1, 2000, 2010, 0.0) == 2000
    assert Z.retracement_level(-1, 2000, 2010, 1.0) == 2010


def test_find_fvgs_bullish_and_bearish():
    h = np.array([10.0, 12.0, 13.0, 14.0])
    l = np.array([9.0, 10.5, 12.5, 13.5])
    # m=1: L[2]=12.5 > H[0]=10 -> [10, 12.5] ; m=2: L[3]=13.5 > H[1]=12 -> [12, 13.5]
    f = Z.find_fvgs(1, h, l, 0, 3)
    assert [(z.low, z.high, z.index) for z in f] == [(10.0, 12.5, 1), (12.0, 13.5, 2)]
    # mirror for bearish
    hb, lb = 30 - l, 30 - h
    fb = Z.find_fvgs(-1, hb, lb, 0, 3)
    assert [(z.low, z.high, z.index) for z in fb] == [(17.5, 20.0, 1), (16.5, 18.0, 2)]


def test_no_fvg_when_candles_overlap():
    h = np.array([10.0, 11.0, 11.5])
    l = np.array([9.0, 9.5, 9.9])
    assert Z.find_fvgs(1, h, l, 0, 2) == []
    # min size filter
    h2 = np.array([10.0, 12.0, 13.0]); l2 = np.array([9.0, 10.5, 10.05])
    assert len(Z.find_fvgs(1, h2, l2, 0, 2)) == 1
    assert Z.find_fvgs(1, h2, l2, 0, 2, min_size=0.1) == []


def test_order_block_last_opposite_candle():
    o = np.array([10.0, 10.5, 10.2, 10.1, 10.6])
    c = np.array([10.5, 10.2, 10.1, 10.6, 12.0])   # bars 1 and 2 bearish
    h = np.array([10.6, 10.6, 10.3, 10.7, 12.1])
    l = np.array([9.9, 10.1, 9.8, 10.0, 10.5])
    ob = Z.find_order_block(1, o, h, l, c, fvg_mid=4, origin=2, max_dist=5, pre_origin=2)
    assert (ob.index, ob.low, ob.high) == (2, 9.8, 10.3)       # last bearish before m-1=3
    body = Z.find_order_block(1, o, h, l, c, 4, 2, 5, 2, "BODY")
    assert (body.low, body.high) == (10.1, 10.2)
    # window too short: only bar 3 (bullish) searchable -> None
    assert Z.find_order_block(1, o, h, l, c, 4, 3, 0, 0) is None


def test_intersection_cases():
    ote = Z.Zone(100.0, 101.0)
    a = Z.intersect(Z.Zone(100.2, 100.6), ote)          # case A: OB inside OTE
    assert (a.low, a.high) == (100.2, 100.6) and Z.is_inside(Z.Zone(100.2, 100.6), ote)
    b = Z.intersect(Z.Zone(99.5, 100.4), ote)           # case B: partial overlap
    assert (b.low, b.high) == (100.0, 100.4) and not Z.is_inside(Z.Zone(99.5, 100.4), ote)
    assert Z.intersect(Z.Zone(98.0, 99.9), ote) is None  # no overlap -> no setup
    t = Z.intersect(Z.Zone(99.0, 100.0), ote)           # touching edge -> single price
    assert (t.low, t.high) == (100.0, 100.0)


@pytest.mark.parametrize("d,depth,exp", [
    (1, 0.0, 100.40), (1, 0.5, 100.20), (1, 1.0, 100.00),
    (-1, 0.0, 100.00), (-1, 0.5, 100.20), (-1, 1.0, 100.40),
])
def test_entry_depth(d, depth, exp):
    assert Z.entry_price(d, Z.Zone(100.0, 100.4), depth, 0.01) == pytest.approx(exp)


def test_entry_rounding_stays_inside_zone():
    # zone [100.003, 100.008]: no 0.01 tick inside -> rejected
    assert Z.entry_price(1, Z.Zone(100.003, 100.008), 0.5, 0.01) is None
    # zone [100.004, 100.016]: only 100.01 is inside
    assert Z.entry_price(1, Z.Zone(100.004, 100.016), 0.0, 0.01) == pytest.approx(100.01)
    assert Z.entry_price(1, Z.Zone(100.004, 100.016), 1.0, 0.01) == pytest.approx(100.01)


def test_stop_loss_anchors_and_rounding():
    ob = Z.Zone(99.2, 100.6)
    assert Z.stop_loss_price(1, ob, 99.0, 105.5, "STRUCTURAL", 0.1, 0.01) == pytest.approx(98.90)
    assert Z.stop_loss_price(1, ob, 99.0, 105.5, "OB_DISTAL", 0.1, 0.01) == pytest.approx(99.10)
    assert Z.stop_loss_price(1, ob, 99.0, 105.5, "IMPULSE_ORIGIN", 0.1, 0.01) == pytest.approx(98.90)
    # rounding away from entry
    assert Z.stop_loss_price(1, ob, 99.0, 105.5, "STRUCTURAL", 0.105, 0.01) == pytest.approx(98.89)
    obs = Z.Zone(104.0, 105.2)
    assert Z.stop_loss_price(-1, obs, 99.0, 105.5, "STRUCTURAL", 0.1, 0.01, spread_add=0.05) == pytest.approx(105.65)
    assert Z.stop_loss_price(-1, obs, 99.0, 105.5, "STRUCTURAL", 0.104, 0.01) == pytest.approx(105.61)


def test_zone_states_bullish():
    z = Z.Zone(100.0, 101.0)
    h = np.full(6, 105.0); c = np.full(6, 104.0)
    l = np.array([103.0, 102.0, 102.0, 102.0, 102.0, 102.0])
    assert Z.zone_state(1, z, h, l, c, 0, -1) == Z.NEW
    assert Z.zone_state(1, z, h, l, c, 0, 5) == Z.VALID
    l[3] = 100.5
    assert Z.zone_state(1, z, h, l, c, 0, 5) == Z.PARTIALLY_MITIGATED
    l[4] = 100.0
    assert Z.zone_state(1, z, h, l, c, 0, 5) == Z.FULLY_MITIGATED
    c[5] = 99.9
    assert Z.zone_state(1, z, h, l, c, 0, 5) == Z.INVALIDATED


def test_zone_states_bearish():
    z = Z.Zone(100.0, 101.0)
    l = np.full(4, 95.0); c = np.full(4, 96.0)
    h = np.array([97.0, 100.2, 98.0, 98.0])
    assert Z.zone_state(-1, z, h, l, c, 0, 3) == Z.PARTIALLY_MITIGATED
    h[2] = 101.0
    assert Z.zone_state(-1, z, h, l, c, 0, 3) == Z.FULLY_MITIGATED
    c[3] = 101.1
    assert Z.zone_state(-1, z, h, l, c, 0, 3) == Z.INVALIDATED


def test_user_rule_ob_must_create_the_fvg():
    """[U] 2026-10-24: the OB is the first candle of the FVG (it creates the gap immediately)."""
    # bars: 0 bearish (candidate OB), 1 bullish, 2 bullish displacement, 3 bullish
    o = np.array([10.5, 10.1, 10.4, 12.0])
    c = np.array([10.1, 10.4, 12.0, 12.5])
    h = np.array([10.6, 10.5, 12.1, 12.6])
    l = np.array([10.0, 10.0, 10.3, 11.9])
    # FVG with middle candle m=2: L[3]=11.9 > H[1]=10.5 ; first candle (m-1=1) is bullish -> no OB
    assert Z.find_order_block(1, o, h, l, c, fvg_mid=2, origin=0, max_dist=0, pre_origin=2) is None
    # the old tolerant rule (5 bars) would have accepted bar 0
    assert Z.find_order_block(1, o, h, l, c, fvg_mid=2, origin=0, max_dist=5, pre_origin=2).index == 0
    # FVG with middle candle m=1: L[2]=10.3 > H[0]=10.6? no -> not a FVG created by bar 0
    assert all(z.index != 1 for z in Z.find_fvgs(1, h, l, 0, 3))
