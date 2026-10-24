#!/usr/bin/env python3
"""Phase 9 - optional ML filter on top of the deterministic strategy (NOT in the execution path).

Gate: runs only if Reports/validation_summary.json shows a positive validated edge
(expectancy_r > 0 and P(mean <= 0) < 0.10 on VAL), as required by the specification. With
--exploratory it runs anyway, but every output is labelled EXPLORATORY and must not be used to
justify live trading.

Design (no look-ahead):
  * features are computed only from fields frozen at setup confirmation (Setup dataclass);
  * labels = net R of the frozen runner method;
  * chronological split: train on DEV fills, choose the threshold on the last DEV year (inner split),
    evaluate once on VAL; TEST is never touched here;
  * compared: deterministic without RSI, with RSI, ML on non-RSI signals, ML on RSI signals.
Model: gradient boosted trees (scikit-learn HistGradientBoosting) with a logistic-regression
baseline; LightGBM/XGBoost are not required for a dataset of a few hundred rows.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))
from sensitor.metrics import summarize_r  # noqa: E402

OUT = ROOT / "Research" / "output"
REP = ROOT / "Reports"


def features(df: pd.DataFrame) -> pd.DataFrame:
    d = df["direction"].astype(float)
    atr = df["s_atr"].replace(0, np.nan)
    t = pd.to_datetime(df["s_confirm_time"], unit="s", utc=True)
    rsi = df["s_rsi_extreme"].astype(float)
    return pd.DataFrame({
        "dir": d,
        "hour": t.dt.hour, "dow": t.dt.dayofweek,
        "atr_rel": atr / df["s_entry"],
        "risk_atr": df["s_risk_dist"] / atr,
        "spread_risk": df["s_spread"] / df["s_risk_dist"],
        "impulse_atr": (df["s_extreme_price"] - df["s_origin_price"]).abs() / atr,
        "ote_w_atr": (df["s_ote_high"] - df["s_ote_low"]) / atr,
        "ob_w_atr": (df["s_ob_high"] - df["s_ob_low"]) / atr,
        "fvg_w_atr": (df["s_fvg_high"] - df["s_fvg_low"]) / atr,
        "zone_w_atr": (df["s_zone_high"] - df["s_zone_low"]) / atr,
        "case_a": (df["s_entry_case"] == "A").astype(float),
        "rsi_dir": np.where(d > 0, rsi, 100 - rsi),
        "n_comp": df["s_sweeps_compatible"].fillna("").map(lambda x: 0 if x == "" else x.count(";") + 1),
        "n_caut": df["s_sweeps_caution"].fillna("").map(lambda x: 0 if x == "" else x.count(";") + 1),
        "choch": (df["s_break_label"] == "CHOCH").astype(float),
        "wait_bars": df["s_confirm_bar"] - df["s_break_bar"],
        "tp_liq_r": (df["s_tp_liquidity"] - df["s_entry"]) * d / df["s_risk_dist"],
    })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exploratory", action="store_true")
    ap.add_argument("--runner", default=None)
    a = ap.parse_args()
    gate = REP / "validation_summary.json"
    ok = False
    if gate.exists():
        g = json.loads(gate.read_text())
        ok = g.get("expectancy_r", -1) > 0 and g.get("p_mean_le_0", 1) < 0.10
    if not ok and not a.exploratory:
        print("Gate closed: the deterministic strategy has not shown a validated out-of-sample edge "
              "(Reports/validation_summary.json). Phase 9 is not run (use --exploratory for a labelled study).")
        return 0
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        print("scikit-learn is required: pip install scikit-learn")
        return 1
    sel = json.loads((REP / "selected_config.json").read_text())
    runner = a.runner or sel["runner"]
    label = "EXPLORATORY - NOT VALID EVIDENCE" if not ok else "gated"
    rows = []
    for sig in ("RSI_OFF", "BASE"):
        tr = pd.read_parquet(OUT / f"trades_{sig}.parquet")
        c = tr[(tr.variant == runner) & tr.outcome.isin(["CLOSED", "OPEN_AT_END"])].copy()
        c = c.sort_values("fill_time")
        X, y = features(c).fillna(0.0), (c["r_net"] > 0).astype(int)
        dev, val = c.period == "DEV", c.period == "VAL"
        inner_tr = dev & (pd.to_datetime(c.fill_time, unit="s", utc=True).dt.year < 2022)
        inner_va = dev & ~inner_tr
        for mname, model in (("gbt", HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05,
                                                                    min_samples_leaf=20, random_state=0)),
                             ("logit", make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=500)))):
            model.fit(X[inner_tr], y[inner_tr])
            p_in = model.predict_proba(X[inner_va])[:, 1]
            best_thr, best_e = 0.0, -math.inf
            for thr in np.quantile(p_in, [0.0, 0.2, 0.4, 0.6]) if len(p_in) else [0.0]:
                keep = p_in >= thr
                if keep.sum() >= 15:
                    e = c.loc[inner_va, "r_net"].to_numpy()[keep].mean()
                    if e > best_e:
                        best_thr, best_e = thr, e
            model.fit(X[dev], y[dev])
            p_val = model.predict_proba(X[val])[:, 1]
            keep = p_val >= best_thr
            base = summarize_r(c.loc[val, "r_net"].to_numpy())
            filt = summarize_r(c.loc[val, "r_net"].to_numpy()[keep])
            rows.append({"signals": sig, "model": mname, "threshold": best_thr,
                         "val_trades_all": base["trades"], "val_E_all": base.get("expectancy_r"),
                         "val_trades_kept": filt["trades"], "val_E_kept": filt.get("expectancy_r"),
                         "val_pf_kept": filt.get("profit_factor_r")})
    res = pd.DataFrame(rows)
    txt = (f"# Phase 9 — filtre IA ({label})\n\nRunner : {runner}. Entraînement DEV, seuil choisi sur 2022 (DEV), "
           f"évaluation unique sur VAL.\n\n{res.to_markdown(index=False, floatfmt='.3f')}\n")
    (REP / "08_ML_FILTER.md").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
