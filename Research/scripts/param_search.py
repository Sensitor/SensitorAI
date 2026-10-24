#!/usr/bin/env python3
"""Cycle 3 (Research/EXPERIMENT_PLAN.md): random parameter search + rolling walk-forward.

  python3 Research/scripts/param_search.py run      # simulate 400 configs x 6 management variants
  python3 Research/scripts/param_search.py report   # walk-forward selection + report

The reference number is the OUT-OF-SAMPLE R/month of the walk-forward procedure, not the best
in-sample variant (which is reported only with a warning).
"""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import pathlib
import random
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))
from sensitor.config import CostModel, StrategyConfig  # noqa: E402
from sensitor.metrics import summarize_r  # noqa: E402
from sensitor.pipeline import Market, run_signals  # noqa: E402
from sensitor.simulator import Simulator  # noqa: E402

OUT = ROOT / "Research" / "output" / "search"
REP = ROOT / "Reports"
N_CONFIGS = 400
SEED = 2026
COSTS = CostModel()

SPACE = {
    "entry_tf": [15, 5],
    "swing_entry": [2, 3, 5],
    "swing_htf": [2, 3, 5],
    "bias_flip_mode": ["FLIP_ON_CHOCH", "NEUTRAL_ON_CHOCH"],
    "caution_sweep_action": ["BLOCK", "LOG_ONLY"],
    "rsi": ["OFF", "AT_SETUP_ENTRY", "AT_SETUP_H1", "GATE_ENTRY"],
    "entry_depth": [0.0, 0.5, 1.0],
    "continuation_invalidation": ["CLOSE", "WICK"],
    "impulse_anchor": ["SWING_CONFIRM", "BOS_BAR"],
    "sl_buffer_atr": [0.1, 0.3],
    "fvg_min_atr": [0.0, 0.3, 0.6],
    "reject_if_touched_before_placement": [True, False],
}

# (label, be_trigger_r, partial_trigger_r, target_r, follows_user_rules)
MGMT = [
    ("M0_BE1_P3_TP5", 1.0, 3.0, 5.0, True),
    ("M1_noBE_P3_TP5", 50.0, 3.0, 5.0, False),
    ("M2_BE2_P3_TP5", 2.0, 3.0, 5.0, False),
    ("M3_noBE_TP3", 50.0, 60.0, 3.0, False),
    ("M4_noBE_TP2", 50.0, 60.0, 2.0, False),
    ("M5_BE1_TP3", 1.0, 60.0, 3.0, False),
]
MK: Market | None = None


def sample_configs() -> list[dict]:
    rng = random.Random(SEED)
    seen, out = set(), []
    while len(out) < N_CONFIGS:
        p = {k: rng.choice(v) for k, v in SPACE.items()}
        key = json.dumps(p, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def to_cfg(p: dict) -> StrategyConfig:
    rsi_mode, rsi_tf = {"OFF": ("OFF", 0), "AT_SETUP_ENTRY": ("AT_SETUP", 0), "AT_SETUP_H1": ("AT_SETUP", 60),
                        "GATE_ENTRY": ("GATE_PLACEMENT", 0)}[p["rsi"]]
    return StrategyConfig(entry_tf=p["entry_tf"], swing_left_entry=p["swing_entry"], swing_right_entry=p["swing_entry"],
                          swing_left_htf=p["swing_htf"], swing_right_htf=p["swing_htf"],
                          bias_flip_mode=p["bias_flip_mode"], caution_sweep_action=p["caution_sweep_action"],
                          rsi_mode=rsi_mode, rsi_tf=rsi_tf, entry_depth=p["entry_depth"],
                          continuation_invalidation=p["continuation_invalidation"],
                          impulse_anchor=p["impulse_anchor"], sl_buffer_atr=p["sl_buffer_atr"],
                          fvg_min_atr=p["fvg_min_atr"],
                          reject_if_touched_before_placement=p["reject_if_touched_before_placement"])


def work(args) -> pd.DataFrame:
    cid, p = args
    cfg = to_cfg(p)
    eng = run_signals(cfg, MK)
    e = MK.bars[cfg.entry_tf]
    sim = Simulator(MK.m1, cfg, COSTS, 0.01, e.close_time, eng.trk_e.events, eng.atr_e, cfg.entry_tf)
    rows = []
    placed = [s for s in eng.setups if s.place_time >= 0]
    for label, be, part, tgt, _ in MGMT:
        sim.cfg = cfg.replace(be_trigger_r=be, partial_trigger_r=part, runner_target_r=tgt)
        for s in placed:
            r = sim.run(s, variant=label, runner="FIXED_R", target_r=tgt)
            if r.fill_time >= 0 and r.outcome in ("CLOSED", "OPEN_AT_END"):
                rows.append((cid, label, r.fill_time, r.r_net, s.direction, r.risk_dist))
    return pd.DataFrame(rows, columns=["cfg", "mgmt", "fill_time", "r_net", "direction", "risk_dist"])


def run() -> None:
    global MK
    OUT.mkdir(parents=True, exist_ok=True)
    cfgs = sample_configs()
    (OUT / "configs.json").write_text(json.dumps(cfgs, indent=1))
    t = time.time()
    MK = Market.load("2018-01-01", "2026-10-01")
    print(f"market loaded {time.time() - t:.0f}s", flush=True)
    done = {int(f.stem.split("_")[1]) for f in OUT.glob("cfg_*.parquet")}
    todo = [(i, p) for i, p in enumerate(cfgs) if i not in done]
    with mp.get_context("fork").Pool(4) as pool:
        for k, df in enumerate(pool.imap_unordered(work, todo, chunksize=1), 1):
            cid = int(df["cfg"].iloc[0]) if len(df) else None
            if cid is None:
                continue
            df.to_parquet(OUT / f"cfg_{cid:04d}.parquet")
            if k % 20 == 0:
                print(f"{k}/{len(todo)} configs, {time.time() - t:.0f}s", flush=True)
    # configs that produced no trade at all
    for i, p in todo:
        f = OUT / f"cfg_{i:04d}.parquet"
        if not f.exists():
            pd.DataFrame(columns=["cfg", "mgmt", "fill_time", "r_net", "direction", "risk_dist"]).to_parquet(f)
    print(f"done in {time.time() - t:.0f}s")


# ------------------------------------------------------------------------------------------------
def ts(s: str) -> int:
    return int(pd.Timestamp(s, tz="UTC").timestamp())


def months_between(a: str, b: str) -> float:
    return (pd.Timestamp(b) - pd.Timestamp(a)).days / 30.4375


def score_table(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    sub = df[(df.fill_time >= ts(a)) & (df.fill_time < ts(b))]
    g = sub.groupby(["cfg", "mgmt"])["r_net"]
    t = g.agg(n="count", total="sum", mean="mean", std="std").reset_index()
    pos = sub[sub.r_net > 0].groupby(["cfg", "mgmt"])["r_net"].sum().rename("gp")
    neg = -sub[sub.r_net < 0].groupby(["cfg", "mgmt"])["r_net"].sum().rename("gl")
    t = t.merge(pos, on=["cfg", "mgmt"], how="left").merge(neg, on=["cfg", "mgmt"], how="left").fillna({"gp": 0, "gl": 0})
    t["pf"] = np.where(t.gl > 0, t.gp / t.gl.replace(0, np.nan), np.inf)
    t["t"] = t["mean"] / (t["std"] / np.sqrt(t["n"]))
    t["r_month"] = t["total"] / months_between(a, b)
    return t


def walk_forward(df: pd.DataFrame, objective: str, user_rules_only: bool) -> tuple[pd.DataFrame, list[dict]]:
    tests = [("2022-01-01", "2023-01-01"), ("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"),
             ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-01")]
    pool = df[df.mgmt == "M0_BE1_P3_TP5"] if user_rules_only else df
    oos, log = [], []
    for a, b in tests:
        ta = f"{int(a[:4]) - 3}{a[4:]}"
        tab = score_table(pool, ta, a)
        tab = tab[(tab.n >= 30) & (tab.pf >= 1.1)]
        if tab.empty:
            log.append({"test": a[:4], "choice": None, "reason": "no admissible variant"})
            continue
        best = tab.sort_values(objective, ascending=False).iloc[0]
        sel = pool[(pool.cfg == best.cfg) & (pool.mgmt == best.mgmt) & (pool.fill_time >= ts(a)) & (pool.fill_time < ts(b))]
        oos.append(sel.assign(test_year=a[:4]))
        s = summarize_r(sel.r_net.to_numpy())
        log.append({"test": a[:4], "cfg": int(best.cfg), "mgmt": best.mgmt, "train_n": int(best.n),
                    "train_R_month": round(best.r_month, 2), "train_pf": round(best.pf, 2),
                    "test_n": s["trades"], "test_R_total": round(s.get("total_r", 0.0), 2),
                    "test_R_month": round(s.get("total_r", 0.0) / months_between(a, b), 2),
                    "test_E": round(s.get("expectancy_r", math.nan), 3) if s["trades"] else None})
    return (pd.concat(oos) if oos else pd.DataFrame()), log


def report() -> None:
    cfgs = json.loads((OUT / "configs.json").read_text())
    df = pd.concat([pd.read_parquet(f) for f in sorted(OUT.glob("cfg_*.parquet"))], ignore_index=True)
    n_var = len(cfgs) * len(MGMT)
    lines = ["# Cycle 3 — recherche de paramètres et walk-forward\n",
             f"- {len(cfgs)} configurations de signaux × {len(MGMT)} gestions = **{n_var} variantes** (plan pré-enregistré)",
             "- Coûts de base (spread réel Dukascopy, commission 7 $/lot, slippage, swaps). R par trade, sans limites de compte.",
             "- **Le chiffre de référence est le R/mois hors échantillon du walk-forward.** Le meilleur réglage in-sample est",
             "  mécaniquement surévalué (choisi parmi des milliers d'essais sur les mêmes données).\n"]
    # --- in-sample over everything
    full = score_table(df, "2019-01-01", "2026-10-01")
    full = full[full.n >= 50]
    top = full.sort_values("total", ascending=False).head(10).copy()
    top["params"] = [json.dumps(cfgs[int(c)]) for c in top.cfg]
    lines.append("## 1. Meilleures variantes in-sample 2019 → 2026-09 (biaisées à la hausse)\n")
    lines.append(top[["cfg", "mgmt", "n", "r_month", "mean", "pf", "t", "total"]].to_markdown(index=False, floatfmt=".3f") + "\n")
    lines.append(f"Seuil « hasard » pour {n_var} variantes : t ≈ √(2 ln N) = {math.sqrt(2 * math.log(n_var)):.2f}.\n")
    lines.append("Paramètres des 3 premières :\n")
    for _, r in top.head(3).iterrows():
        lines.append(f"- cfg {int(r.cfg)} / {r.mgmt} : `{r.params}`")
    lines.append("")
    q = full["r_month"].quantile([0.1, 0.5, 0.9]).to_numpy()
    lines.append(f"Distribution du R/mois sur les {len(full)} variantes ayant ≥ 50 trades : médiane {q[1]:.2f}, "
                 f"10 % {q[0]:.2f}, 90 % {q[2]:.2f}, max {full['r_month'].max():.2f}.\n")
    # --- walk-forward
    results = {}
    for label, obj, user_only in (("A. critère R total, toutes gestions", "total", False),
                                  ("B. critère t, toutes gestions", "t", False),
                                  ("C. critère R total, gestion de l'utilisateur (M0) seulement", "total", True)):
        oos, log = walk_forward(df, obj, user_only)
        s = summarize_r(oos.r_net.to_numpy()) if len(oos) else {"trades": 0}
        m = months_between("2022-01-01", "2026-10-01")
        results[label] = (s, oos)
        lines.append(f"## 2.{label[0]} Walk-forward — {label[3:]}\n")
        lines.append(pd.DataFrame(log).to_markdown(index=False) + "\n")
        if s["trades"]:
            lines.append(f"**Hors échantillon 2022 → 2026-09 : {s['trades']} trades, espérance {s['expectancy_r']:+.3f} R "
                         f"(IC95 [{s['ci95_low']:+.3f} ; {s['ci95_high']:+.3f}]), PF {s['profit_factor_r']:.2f}, "
                         f"total {s['total_r']:+.1f} R, soit {s['total_r'] / m:+.2f} R/mois, "
                         f"drawdown max {s['max_dd_r']:.1f} R.**\n")
            mo = oos.assign(m=pd.to_datetime(oos.fill_time, unit="s", utc=True).dt.strftime("%Y-%m")).groupby("m").r_net.sum()
            lines.append(f"Mois positifs : {int((mo > 0).sum())} / {len(mo)} mois avec trades ; meilleur mois {mo.max():+.1f} R, "
                         f"pire mois {mo.min():+.1f} R.\n")
    # --- best per management (in-sample) and parameter influence
    lines.append("## 3. Influence des paramètres (moyenne du R/mois in-sample par valeur)\n")
    full_all = score_table(df, "2019-01-01", "2026-10-01")
    params = pd.DataFrame(cfgs)
    full_all = full_all.merge(params.reset_index().rename(columns={"index": "cfg"}), on="cfg")
    for k in list(SPACE) + ["mgmt"]:
        g = full_all.groupby(k).agg(r_month=("r_month", "mean"), trades_month=("n", lambda x: x.mean() / months_between("2019-01-01", "2026-10-01")),
                                    expectancy=("mean", "mean")).reset_index()
        lines.append(f"**{k}**\n\n" + g.to_markdown(index=False, floatfmt=".3f") + "\n")
    (REP / "10_PARAM_SEARCH.md").write_text("\n".join(lines))
    print("\n".join(lines[:60]))


if __name__ == "__main__":
    {"run": run, "report": report}[sys.argv[1]]()
