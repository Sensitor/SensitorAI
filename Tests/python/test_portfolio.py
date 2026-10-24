"""Portfolio overlay: limits checked at placement, sizing and partial fallback."""
import math

import pandas as pd
import pytest

from sensitor.config import AccountModel, CostModel, StrategyConfig
from sensitor.portfolio import run_portfolio

COSTS = CostModel(commission_per_lot_rt=0.0, swap_long_per_lot=0.0, swap_short_per_lot=0.0)


def row(pt, ft, xt, r_gross=2.0, risk=5.0, be=-1, partial=math.nan, runner=math.nan, outcome="CLOSED"):
    return dict(place_time=pt, fill_time=ft, exit_time=xt, be_time=be, r_gross=r_gross, risk_dist=risk,
                risk_dist_setup=risk, direction=1, nights=0.0, outcome=outcome, end_time=-1,
                r_partial_leg=partial, r_runner_leg=runner)


def run(rows, cfg=StrategyConfig(), acct=AccountModel()):
    return run_portfolio(pd.DataFrame(rows), cfg, COSTS, acct, lambda t: 7200)


def test_sizing_and_pnl():
    # 10 000 * 1 % = 100 USD ; SL 5 USD * 100 oz = 500 USD/lot => 0.20 lot ; +2R => +200 USD
    pf, eq = run([row(0, 10, 100)])
    assert pf.loc[0, "volume"] == pytest.approx(0.20)
    assert pf.loc[0, "pnl"] == pytest.approx(200.0)
    assert eq["balance"].iloc[-1] == pytest.approx(10_200.0)


def test_max_positions_blocks_overlapping_trade():
    pf, _ = run([row(0, 10, 1000), row(50, 60, 2000)], StrategyConfig(max_positions=1))
    assert list(pf["pf_status"]) == ["PLACED", "REJECT_MAX_POSITIONS"]


def test_position_at_breakeven_frees_risk_budget():
    cfg = StrategyConfig(max_positions=3, max_total_risk_pct=1.0)
    pf, _ = run([row(0, 10, 1000, be=20), row(50, 60, 2000)], cfg)
    assert list(pf["pf_status"]) == ["PLACED", "PLACED"]
    pf2, _ = run([row(0, 10, 1000), row(50, 60, 2000)], cfg)
    assert list(pf2["pf_status"]) == ["PLACED", "REJECT_TOTAL_RISK"]


def test_daily_loss_limit():
    # volumes are floored: losses = 100 + 95 + 95 = 290 USD (< 300 = 3 %) -> 4th trade still placed;
    # after the 4th loss (385 USD) the 5th trade is refused
    rows = [row(t, t + 10, t + 20, r_gross=-1.0) for t in (0, 30, 60, 90)] + [row(120, 130, 140)]
    pf, _ = run(rows, StrategyConfig(daily_loss_limit_pct=3.0, max_positions=5))
    assert pf["pf_status"].tolist() == ["PLACED"] * 4 + ["REJECT_DAILY_LOSS_LIMIT"]
    assert pf["pnl"].iloc[:4].sum() == pytest.approx(-385.0)


def test_min_lot_split_fallback_close_all():
    # tiny account: 100 USD * 1 % = 1 USD ; SL 0.10 USD => 10 USD/lot => 0.10 lot ... make it 0.01:
    acct = AccountModel(initial_balance=600.0)          # 6 USD risk / 500 USD per lot -> 0.01 lot
    pf, _ = run([row(0, 10, 100, r_gross=2.0, partial=2.95, runner=-0.1)], acct=acct)
    assert pf.loc[0, "volume"] == pytest.approx(0.01)
    assert pf.loc[0, "partial_action"] == "FALLBACK_CLOSE_ALL"
    assert pf.loc[0, "pnl"] == pytest.approx(2.95 * 5.0 * 100 * 0.01)


def test_min_lot_refused():
    acct = AccountModel(initial_balance=400.0)          # 4 USD risk < 0.01 lot * 500 USD
    pf, _ = run([row(0, 10, 100)], acct=acct)
    assert pf.loc[0, "pf_status"] == "REJECT_MIN_LOT_EXCEEDS_RISK"
