"""Portfolio overlay: applies account-level rules to independently simulated trades.

Trades only interact through the risk limits checked at order placement (max positions/pending,
max total open risk, daily loss limit), so each setup is simulated in isolation and the overlay
decides, in chronological order of placement, whether the EA would have placed it and with which
volume. Known simplifications (Docs/LIMITATIONS.md):
  * risk base = balance (closed P&L), not min(balance, equity);
  * the daily loss limit blocks new placements but pending orders already placed are not
    retro-actively cancelled when the limit is hit later the same day;
  * floating P&L is ignored in the daily loss computation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import AccountModel, CostModel, StrategyConfig
from .risk import compute_volume, partial_close_volume


def _server_day(t: int, offset: int) -> int:
    return (t + offset) // 86400


def run_portfolio(trades: pd.DataFrame, cfg: StrategyConfig, costs: CostModel,
                  acct: AccountModel, server_offset_fn) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`trades`: rows of TradeResult.as_dict() merged with setup fields (needs risk_dist_setup).

    Returns (trades with portfolio columns, equity curve).
    """
    df = trades[trades["place_time"] >= 0].sort_values("place_time").reset_index(drop=True)
    balance = acct.initial_balance
    accepted: list[dict] = []
    realized: list[tuple[int, float]] = []    # (time, pnl) realised events
    rows = []
    for _, tr in df.iterrows():
        t = int(tr["place_time"])
        rec = tr.to_dict()
        rec.update(pf_status="", volume=0.0, pnl=0.0, risk_money=0.0)
        # --- state at t -------------------------------------------------------------------------
        bal_t = acct.initial_balance + sum(p for (tt, p) in realized if tt <= t)
        n_open, n_pending, risk_pct_open = 0, 0, 0.0
        for a in accepted:
            filled = a["fill_time"] >= 0 and a["fill_time"] <= t
            if filled and t < a["exit_time"]:
                n_open += 1
                if not (a["be_time"] >= 0 and a["be_time"] <= t):
                    risk_pct_open += cfg.risk_pct
            elif not filled and t < a["pending_end"]:
                n_pending += 1
                risk_pct_open += cfg.risk_pct
        off = int(server_offset_fn(t))
        day = _server_day(t, off)
        day_start_bal = acct.initial_balance + sum(p for (tt, p) in realized if _server_day(tt, off) < day)
        day_pnl = sum(p for (tt, p) in realized if tt <= t and _server_day(tt, off) == day)
        # --- checks -----------------------------------------------------------------------------
        status = ""
        if day_pnl <= -cfg.daily_loss_limit_pct / 100.0 * day_start_bal:
            status = "REJECT_DAILY_LOSS_LIMIT"
        elif n_open + n_pending >= cfg.max_positions:
            status = "REJECT_MAX_POSITIONS"
        elif risk_pct_open + cfg.risk_pct > cfg.max_total_risk_pct + 1e-9:
            status = "REJECT_TOTAL_RISK"
        vol = 0.0
        if not status:
            risk_money = cfg.risk_pct / 100.0 * bal_t
            loss_per_lot = tr["risk_dist_setup"] * costs.contract_size
            vol, why = compute_volume(risk_money, loss_per_lot, costs.commission_per_lot_rt,
                                      acct.volume_min, acct.volume_step, acct.volume_max)
            if vol <= 0:
                status = why
            rec["risk_money"] = risk_money
        if status:
            rec["pf_status"] = status
            rows.append(rec)
            continue
        rec["pf_status"] = "PLACED"
        rec["volume"] = vol
        filled = tr["fill_time"] >= 0
        if tr["outcome"] in ("CLOSED", "OPEN_AT_END") and filled:
            r_gross = tr["r_gross"]
            if not math.isnan(tr.get("r_partial_leg", math.nan)):
                pvol, action = partial_close_volume(vol, vol, cfg.partial_fraction, acct.volume_min,
                                                    acct.volume_step, cfg.partial_fallback)
                if action == "FALLBACK_CLOSE_ALL":
                    r_gross = tr["r_partial_leg"]
                elif action == "FALLBACK_KEEP_ALL":
                    r_gross = tr["r_runner_leg"]
                else:
                    f = pvol / vol
                    r_gross = f * tr["r_partial_leg"] + (1 - f) * tr["r_runner_leg"]
                rec["partial_action"] = action
            money_per_r = tr["risk_dist"] * costs.contract_size * vol
            gross = r_gross * money_per_r
            comm = -costs.commission_per_lot_rt * vol
            swap_rate = costs.swap_long_per_lot if tr["direction"] > 0 else costs.swap_short_per_lot
            swap = tr["nights"] * swap_rate * vol
            pnl = gross + comm + swap
            rec["pnl"] = pnl
            rec["r_net_pf"] = pnl / rec["risk_money"]
            realized.append((int(tr["exit_time"]), pnl))
            pending_end = int(tr["fill_time"])
            exit_time = int(tr["exit_time"])
        else:
            pending_end = int(tr["end_time"]) if tr.get("end_time", -1) and tr.get("end_time", -1) > 0 else 2**62
            if tr["outcome"] in ("MISSED_AT_PLACEMENT",):
                pending_end = t
            exit_time = -1
        accepted.append(dict(fill_time=int(tr["fill_time"]), exit_time=exit_time,
                             be_time=int(tr["be_time"]), pending_end=pending_end))
        rows.append(rec)
    out = pd.DataFrame(rows)
    realized.sort()
    eq = pd.DataFrame(realized, columns=["time", "pnl"])
    eq["balance"] = acct.initial_balance + eq["pnl"].cumsum()
    return out, eq
