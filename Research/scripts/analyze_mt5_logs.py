#!/usr/bin/env python3
"""Analyse the CSV journals written by the EA (Common\\Files\\SensitorAI\\<tag>_*.csv).

Produces the same headline metrics as the research pipeline from LIVE / DEMO / TESTER logs:
  trades, win rate, average win/loss, net expectancy (money and R), profit factor, net result,
  max drawdown, holding time, breakdown by session / year / month / side / exit reason,
  costs (commission, swap), entry slippage, setup funnel and rejection reasons.

Optional parity check against the Python engine on the same bars:
  --python-setups Research/output/setups_BASE.parquet --server-offset-hours 2
compares setup identifiers (bar open time; the EA uses server time, Python UTC).

Usage: python3 Research/scripts/analyze_mt5_logs.py --dir <Common/Files/SensitorAI> --tag XAUUSD_20250101
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))
from sensitor.data import session_of  # noqa: E402
from sensitor.metrics import max_drawdown, summarize_r  # noqa: E402


def read(d: pathlib.Path, tag: str, name: str) -> pd.DataFrame:
    p = d / f"{tag}_{name}.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--tag", required=True, help="<symbol>_<magic>")
    ap.add_argument("--initial-balance", type=float, default=None)
    ap.add_argument("--python-setups", default=None)
    ap.add_argument("--server-offset-hours", type=float, default=2.0)
    a = ap.parse_args()
    d = pathlib.Path(a.dir)
    trades, setups, decisions = read(d, a.tag, "trades"), read(d, a.tag, "setups"), read(d, a.tag, "decisions")
    errors = read(d, a.tag, "errors")
    print(f"# Sensitor AI journal analysis ({a.tag})\n")
    if not setups.empty:
        print("## Setup funnel\n")
        print(setups.groupby(["status", "reason"]).size().rename("n").reset_index().to_string(index=False))
        ends = setups[setups["end_reason"].notna() & (setups["end_reason"] != "")]
        if len(ends):
            print("\nInvalidation reasons:\n" + ends.groupby("end_reason").size().rename("n").to_string())
    if not decisions.empty:
        print("\n## Decision codes\n")
        print(decisions["code"].value_counts().to_string())
    if trades.empty:
        print("\nNo closed trade in the journal.")
        return 0
    trades["fill_time"] = pd.to_datetime(trades["fill_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    s = summarize_r(trades["r_net"].to_numpy(dtype=float))
    print("\n## Trades (R based)\n")
    for k, v in s.items():
        print(f"{k:>18}: {v:.4f}" if isinstance(v, float) else f"{k:>18}: {v}")
    net = trades["net"].to_numpy(dtype=float)
    bal0 = a.initial_balance or 10_000.0
    dd, ddp = max_drawdown(bal0 + np.cumsum(net), bal0)
    gp, gl = net[net > 0].sum(), -net[net < 0].sum()
    print(f"\nNet result: {net.sum():.2f} | profit factor (money): {gp / gl if gl > 0 else float('inf'):.2f} | "
          f"max drawdown: {dd:.2f} ({ddp:.2f} % of peak, initial balance {bal0:.0f})")
    print(f"Costs: commission {trades['commission'].sum():.2f}, swap {trades['swap'].sum():.2f}; "
          f"mean entry slippage {trades['slippage_entry'].mean():.4f} (positive = better than planned)")
    print(f"Mean holding time: {trades['hold_minutes'].mean() / 60:.1f} h")
    trades["session"] = [session_of(int(t.timestamp()) - int(a.server_offset_hours * 3600)) for t in trades["fill_time"]]
    trades["year"] = trades["fill_time"].dt.year
    trades["month"] = trades["fill_time"].dt.strftime("%Y-%m")
    for key in ("session", "year", "month", "direction", "exit_reason", "runner"):
        g = trades.groupby(key)["r_net"].agg(["count", "mean", "sum"])
        print(f"\n### By {key}\n{g.to_string()}")
    if not errors.empty:
        print(f"\n## Errors ({len(errors)})\n{errors.tail(20).to_string(index=False)}")
    if a.python_setups:
        py = pd.read_parquet(a.python_setups)
        off = int(a.server_offset_hours * 3600)
        py_ids = {f"{x[0]}{int(x[1:]) + off}" for x in py["id"]}
        ea_ids = set(setups["setup_id"]) if not setups.empty else set()
        common = py_ids & ea_ids
        print(f"\n## Parity with Python setups\nEA {len(ea_ids)} | Python {len(py_ids)} | common {len(common)} | "
              f"only EA {len(ea_ids - py_ids)} | only Python {len(py_ids - ea_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
