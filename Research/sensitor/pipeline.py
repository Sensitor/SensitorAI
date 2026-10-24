"""Research pipeline: market data -> signals -> per-runner trade simulation -> tables.

Every function is deterministic for a given dataset and configuration.
"""
from __future__ import annotations

import dataclasses
import json
import math
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import AccountModel, CostModel, StrategyConfig
from .data import MinuteData, load_m1, resample
from .metrics import summarize_r
from .setups import Bars, SetupEngine
from .simulator import Simulator

PERIODS = {
    "WARMUP": ("2018-01-01", "2019-01-01"),
    "DEV": ("2019-01-01", "2023-01-01"),
    "VAL": ("2023-01-01", "2024-07-01"),
    "TEST": ("2024-07-01", "2026-10-01"),
}

RUNNERS = {
    "A_STRUCTURE": ("STRUCTURE", None),
    "B_LIQUIDITY": ("LIQUIDITY", None),
    "C_FIXED_5R": ("FIXED_R", 5.0),
    "C_FIXED_6R": ("FIXED_R", 6.0),
    "D_TRAILING": ("TRAILING", None),
}


def ts(s: str) -> int:
    return int(pd.Timestamp(s, tz="UTC").timestamp())


def period_of(t: int) -> str:
    for name, (a, b) in PERIODS.items():
        if ts(a) <= t < ts(b):
            return name
    return "OUT"


@dataclass
class Market:
    m1: MinuteData
    bars: dict          # tf minutes -> Bars
    df: pd.DataFrame

    @classmethod
    def load(cls, start="2018-01-01", end="2026-10-01", acct: AccountModel = AccountModel()) -> "Market":
        df = load_m1("XAUUSD", start, end)
        m1 = MinuteData.from_df(df, acct.server_utc_offset_winter, acct.server_utc_offset_summer)
        bars = {tf: resample(m1, tf) for tf in (5, 15, 60, 240)}
        return cls(m1, bars, df)


def run_signals(cfg: StrategyConfig, mk: Market, tick: float = 0.01) -> SetupEngine:
    e = mk.bars[cfg.entry_tf]
    rsi_bars = mk.bars.get(cfg.rsi_timeframe)
    eng = SetupEngine(cfg, e, mk.bars[60], mk.bars[240], mk.m1.spread_at, tick=tick, rsi_bars=rsi_bars)
    eng.run()
    return eng


def simulate(eng: SetupEngine, mk: Market, cfg: StrategyConfig, costs: CostModel,
             runners=RUNNERS, tick: float = 0.01) -> pd.DataFrame:
    """One row per (setup placed, runner variant)."""
    e = mk.bars[cfg.entry_tf]
    sim = Simulator(mk.m1, cfg, costs, tick, e.close_time, eng.trk_e.events, eng.atr_e, cfg.entry_tf)
    rows = []
    setups = [s for s in eng.setups if s.place_time >= 0]
    for s in setups:
        base = {f"s_{k}": v for k, v in s.as_dict().items()}
        for name, (method, target) in runners.items():
            r = sim.run(s, variant=name, runner=method, target_r=target)
            d = r.as_dict()
            d.update(base)
            rows.append(d)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["risk_dist_setup"] = df["s_risk_dist"]
    df["end_time"] = df["s_end_time"]
    df["period"] = [period_of(int(t if t >= 0 else p)) for t, p in zip(df["fill_time"], df["place_time"])]
    return df


def setups_frame(eng: SetupEngine) -> pd.DataFrame:
    df = pd.DataFrame([s.as_dict() for s in eng.setups])
    if not df.empty:
        df["period"] = [period_of(int(t)) for t in df["confirm_time"]]
    return df


def closed(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["outcome"].isin(["CLOSED", "OPEN_AT_END"])]


def variant_table(trades: pd.DataFrame, period: str, label: str) -> pd.DataFrame:
    rows = []
    sub = trades[trades["period"] == period]
    for v, g in sub.groupby("variant"):
        c = closed(g)
        s = summarize_r(c["r_net"].to_numpy())
        placed = len(g)
        s.update(variant=v, config=label, period=period, placed=placed,
                 fill_rate=len(c) / placed if placed else math.nan,
                 avg_cost_r=float((c["r_commission"] + c["r_swap"]).mean()) if len(c) else math.nan,
                 avg_hold_h=float(((c["exit_time"] - c["fill_time"]) / 3600).mean()) if len(c) else math.nan)
        rows.append(s)
    return pd.DataFrame(rows)


def paired_diff(trades: pd.DataFrame, a: str, b: str, period: str, n: int = 5000, seed: int = 3) -> dict:
    """Paired bootstrap of mean(r_a - r_b) over the SAME filled setups."""
    sub = closed(trades[trades["period"] == period])
    pa = sub[sub["variant"] == a].set_index("setup_id")["r_net"]
    pb = sub[sub["variant"] == b].set_index("setup_id")["r_net"]
    common = pa.index.intersection(pb.index)
    d = (pa.loc[common] - pb.loc[common]).to_numpy()
    if len(d) < 2:
        return {"n": len(d)}
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return {"n": len(d), "mean_diff_r": float(d.mean()), "ci_low": float(np.quantile(means, 0.025)),
            "ci_high": float(np.quantile(means, 0.975)), "p_le_0": float((means <= 0).mean())}


def by_year(trades: pd.DataFrame, variant: str) -> pd.DataFrame:
    c = closed(trades[trades["variant"] == variant]).copy()
    c["year"] = pd.to_datetime(c["fill_time"], unit="s", utc=True).dt.year
    rows = []
    for y, g in c.groupby("year"):
        s = summarize_r(g["r_net"].to_numpy())
        rows.append({"year": y, "trades": s["trades"], "expectancy_r": s["expectancy_r"],
                     "total_r": s["total_r"], "win_rate": s["win_rate"], "pf_r": s["profit_factor_r"]})
    return pd.DataFrame(rows)


def cfg_json(cfg: StrategyConfig) -> str:
    return json.dumps(dataclasses.asdict(cfg), sort_keys=True)
