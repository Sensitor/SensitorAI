"""Performance metrics and statistical uncertainty (R-based and money-based)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .data import session_of


def max_drawdown(balance: np.ndarray, start: float) -> tuple[float, float]:
    """(max drawdown in money, in % of the running peak)."""
    if len(balance) == 0:
        return 0.0, 0.0
    curve = np.concatenate(([start], balance))
    peak = np.maximum.accumulate(curve)
    dd = curve - peak
    i = int(np.argmin(dd))
    return float(-dd[i]), float(-dd[i] / peak[i] * 100.0) if peak[i] > 0 else 0.0


def max_drawdown_r(r: np.ndarray) -> float:
    if len(r) == 0:
        return 0.0
    cum = np.concatenate(([0.0], np.cumsum(r)))
    return float(-(cum - np.maximum.accumulate(cum)).min())


def bootstrap_mean_ci(x: np.ndarray, n: int = 5000, alpha: float = 0.05, seed: int = 7) -> tuple[float, float, float]:
    """Percentile bootstrap CI of the mean, plus P(mean <= 0)."""
    if len(x) < 2:
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    means = x[idx].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)),
            float((means <= 0).mean()))


def summarize_r(r: np.ndarray) -> dict:
    """Statistics of a vector of trade results in R (net of costs)."""
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n == 0:
        return {"trades": 0}
    wins, losses = r[r > 0], r[r <= 0]
    gp, gl = wins.sum(), -losses.sum()
    lo, hi, p_le0 = bootstrap_mean_ci(r)
    sd = r.std(ddof=1) if n > 1 else math.nan
    return {
        "trades": n,
        "win_rate": len(wins) / n,
        "avg_win_r": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss_r": float(losses.mean()) if len(losses) else 0.0,
        "expectancy_r": float(r.mean()),
        "median_r": float(np.median(r)),
        "std_r": float(sd),
        "t_stat": float(r.mean() / (sd / math.sqrt(n))) if n > 1 and sd > 0 else math.nan,
        "ci95_low": lo,
        "ci95_high": hi,
        "p_mean_le_0": p_le0,
        "profit_factor_r": float(gp / gl) if gl > 0 else math.inf,
        "total_r": float(r.sum()),
        "max_dd_r": max_drawdown_r(r),
        "best_r": float(r.max()),
        "worst_r": float(r.min()),
    }


def by_group(df: pd.DataFrame, key: str, rcol: str = "r_net") -> pd.DataFrame:
    rows = []
    for g, sub in df.groupby(key):
        s = summarize_r(sub[rcol].to_numpy())
        rows.append({key: g, "trades": s["trades"], "win_rate": s.get("win_rate"),
                     "expectancy_r": s.get("expectancy_r"), "total_r": s.get("total_r"),
                     "profit_factor_r": s.get("profit_factor_r")})
    return pd.DataFrame(rows)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add analysis columns (session, year, month, side, holding time)."""
    out = df.copy()
    ft = out["fill_time"].astype("int64")
    out["session"] = [session_of(int(t)) for t in ft]
    ts = pd.to_datetime(ft, unit="s", utc=True)
    out["year"] = ts.dt.year
    out["month"] = ts.dt.strftime("%Y-%m")
    out["side"] = np.where(out["direction"] > 0, "BUY", "SELL")
    out["hold_hours"] = (out["exit_time"] - out["fill_time"]) / 3600.0
    return out


def funnel(setups: pd.DataFrame, trades: pd.DataFrame) -> dict:
    """Signal funnel: candidates -> confirmed setups -> placed -> filled."""
    n_all = len(setups)
    n_rej = int((setups["status"] == "REJECTED").sum())
    placed = trades[trades["place_time"] >= 0]
    filled = trades[trades["fill_time"] >= 0]
    return {
        "setups_evaluated": n_all,
        "rejected_at_confirmation": n_rej,
        "missed_before_placement": int((setups["status"] == "MISSED").sum()),
        "orders_placed": len(placed),
        "missed_at_placement": int((trades["outcome"] == "MISSED_AT_PLACEMENT").sum()),
        "cancelled_unfilled": int((trades["outcome"] == "CANCELLED").sum()),
        "filled": len(filled),
        "fill_rate": len(filled) / len(placed) if len(placed) else math.nan,
        "invalidated_share_of_placed": float((trades["outcome"] == "CANCELLED").sum() / len(placed)) if len(placed) else math.nan,
    }
