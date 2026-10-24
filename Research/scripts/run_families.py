#!/usr/bin/env python3
"""Cycle 4 (Research/EXPERIMENT_PLAN.md): established strategy families + rolling walk-forward.

  python3 Research/scripts/run_families.py     -> Reports/11_STRATEGY_FAMILIES.md
"""
from __future__ import annotations

import math
import multiprocessing as mp
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))
from sensitor import families as F  # noqa: E402
from sensitor.config import CostModel  # noqa: E402
from sensitor.data import resample  # noqa: E402
from sensitor.metrics import summarize_r  # noqa: E402
from sensitor.pipeline import Market  # noqa: E402

OUT = ROOT / "Research" / "output" / "families"
REP = ROOT / "Reports"
COSTS = CostModel()
STRESS = CostModel(commission_per_lot_rt=10.5, stop_slippage=0.30, swap_long_per_lot=-80.0,
                   swap_short_per_lot=-30.0, extra_spread=0.20)
MK: Market | None = None
BARS: dict = {}


def variants() -> list[tuple[str, str, tuple]]:
    v = []
    for tf in (240, 1440):
        for N in (20, 55):
            for k in (2.0, 3.0):
                v.append(("F1_DONCHIAN", f"tf{tf}_N{N}_k{k:g}", ("donchian", tf, N, k)))
    for sess in ("LONDON", "NY"):
        for mins in (15, 30, 60):
            for tp in (1.0, 2.0, float("nan")):
                v.append(("F2_ORB", f"{sess}_{mins}m_tp{'EOS' if math.isnan(tp) else f'{tp:g}R'}", ("orb", sess, mins, tp)))
    for s in (5.0, 10.0):
        for filt in (True, False):
            for both in (False, True):
                v.append(("F3_RSI2", f"s{s:g}_{'sma200' if filt else 'nofilt'}_{'both' if both else 'long'}", ("rsi2", s, filt, both)))
    for tp in (1.5, 2.0, 3.0):
        for both in (False, True):
            v.append(("F4_PULLBACK", f"tp{tp:g}R_{'both' if both else 'long'}", ("pullback", tp, both)))
    for kind in ("NR7", "INSIDE"):
        for tp in (1.0, 2.0, float("nan")):
            v.append(("F5_COMPRESSION", f"{kind}_tp{'EOD' if math.isnan(tp) else f'{tp:g}R'}", ("compression", kind, tp)))
    return v


def specs_for(p: tuple):
    kind = p[0]
    if kind == "donchian":
        return F.donchian(BARS[p[1]], p[2], p[3])
    if kind == "orb":
        return F.orb(MK.m1, p[1], p[2], p[3])
    if kind == "rsi2":
        return F.rsi2(BARS[60], p[1], p[2], p[3])
    if kind == "pullback":
        return F.pullback(BARS[60], BARS[240], p[1], p[2])
    return F.compression(BARS[1440], p[1], p[2])


def work(item):
    fam, name, p = item
    specs = specs_for(p)
    out = []
    for label, costs in (("base", COSTS), ("stress", STRESS)):
        df = F.Executor(MK.m1, costs).run_all(specs)
        if len(df):
            df["costs"] = label
            out.append(df)
    df = pd.concat(out) if out else pd.DataFrame()
    df["family"], df["variant"] = fam, name
    return df


def ts(s):
    return int(pd.Timestamp(s, tz="UTC").timestamp())


def months(a, b):
    return (pd.Timestamp(b) - pd.Timestamp(a)).days / 30.4375


def table(df, a, b):
    sub = df[(df.fill_time >= ts(a)) & (df.fill_time < ts(b))]
    rows = []
    for (fam, var), g in sub.groupby(["family", "variant"]):
        s = summarize_r(g.r_net.to_numpy())
        L, S = g[g.direction > 0].r_net, g[g.direction < 0].r_net
        rows.append(dict(family=fam, variant=var, trades=s["trades"], trades_month=s["trades"] / months(a, b),
                         expectancy=s["expectancy_r"], pf=s["profit_factor_r"], t=s["t_stat"],
                         R_month=s["total_r"] / months(a, b), max_dd_r=s["max_dd_r"],
                         E_long=L.mean() if len(L) else np.nan, E_short=S.mean() if len(S) else np.nan))
    return pd.DataFrame(rows)


def walk_forward(df, fam=None):
    tests = [("2022-01-01", "2023-01-01"), ("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"),
             ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-01")]
    pool = df if fam is None else df[df.family == fam]
    log, oos = [], []
    for a, b in tests:
        ta = f"{int(a[:4]) - 3}{a[4:]}"
        tab = table(pool, ta, a)
        tab = tab[(tab.trades >= 20) & (tab.pf >= 1.1)]
        if tab.empty:
            log.append(dict(test=a[:4], choice="aucune variante admissible", test_trades=0, test_R=0.0))
            continue
        best = tab.sort_values("R_month", ascending=False).iloc[0]
        sel = pool[(pool.variant == best.variant) & (pool.family == best.family) & (pool.fill_time >= ts(a)) & (pool.fill_time < ts(b))]
        oos.append(sel)
        log.append(dict(test=a[:4], choice=f"{best.family}/{best.variant}", train_R_month=round(best.R_month, 2),
                        test_trades=len(sel), test_R=round(sel.r_net.sum(), 2),
                        test_R_month=round(sel.r_net.sum() / months(a, b), 2)))
    return (pd.concat(oos) if oos else pd.DataFrame(columns=df.columns)), log


def main():
    global MK, BARS
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "trades.parquet"
    if not f.exists():
        t = time.time()
        MK = Market.load("2018-01-01", "2026-10-01")
        BARS = {60: MK.bars[60], 240: MK.bars[240], 1440: resample(MK.m1, 1440)}
        with mp.get_context("fork").Pool(4) as pool:
            parts = pool.map(work, variants(), chunksize=1)
        pd.concat([p for p in parts if len(p)]).to_parquet(f)
        print(f"simulated in {time.time() - t:.0f}s")
    all_ = pd.read_parquet(f)
    base = all_[all_.costs == "base"]
    stress = all_[all_.costs == "stress"]
    L = ["# Cycle 4 — familles de stratégies reconnues sur XAU/USD\n",
         "- Plan pré-enregistré : `Research/EXPERIMENT_PLAN.md` (cycle 4). 46 variantes, coûts de base du plan v1 "
         "(spread réel, 7 $/lot, slippage 0,10 $ sur entrées marché/stop et stops, swaps).",
         "- **Chiffre de référence : walk-forward** (réglage choisi sur les 3 années précédentes, appliqué à l'année "
         "suivante). Les tableaux in-sample sont fournis pour comprendre, pas pour choisir.",
         "- L'or a triplé sur la période : comparer espérance acheteuse (E_long) et vendeuse (E_short).\n"]
    full = table(base, "2019-01-01", "2026-10-01").sort_values("R_month", ascending=False)
    fs = table(stress, "2019-01-01", "2026-10-01")[["family", "variant", "R_month"]].rename(columns={"R_month": "R_month_stress"})
    full = full.merge(fs, on=["family", "variant"], how="left")
    L.append("## 1. In-sample 2019 → 2026-09 (toutes variantes, biaisé à la hausse)\n")
    L.append(full.to_markdown(index=False, floatfmt=".3f") + "\n")
    L.append(f"Seuil « hasard » pour 46 variantes (+2 400 au cycle 3) : t ≈ {math.sqrt(2 * math.log(46)):.2f} "
             f"(≈ {math.sqrt(2 * math.log(46 + 2400 + 75)):.2f} en comptant tout l'historique de recherche).\n")
    L.append("## 2. Walk-forward par famille (hors échantillon 2022 → 2026-09)\n")
    m = months("2022-01-01", "2026-10-01")
    summary, monthly = [], {}
    for fam in sorted(base.family.unique()):
        oos, log = walk_forward(base, fam)
        s = summarize_r(oos.r_net.to_numpy()) if len(oos) else {"trades": 0}
        summary.append(dict(family=fam, trades=s["trades"], trades_month=s["trades"] / m,
                            expectancy=s.get("expectancy_r"), pf=s.get("profit_factor_r"),
                            R_month=(s.get("total_r") or 0.0) / m, max_dd_r=s.get("max_dd_r")))
        L.append(f"### {fam}\n\n" + pd.DataFrame(log).to_markdown(index=False) + "\n")
        if len(oos):
            monthly[fam] = oos.assign(m=pd.to_datetime(oos.fill_time, unit="s", utc=True).dt.strftime("%Y-%m")).groupby("m").r_net.sum()
    L.append("### Synthèse walk-forward par famille\n\n" + pd.DataFrame(summary).to_markdown(index=False, floatfmt=".3f") + "\n")
    # portfolio of all families (each risking 1R per trade)
    if monthly:
        idx = pd.period_range("2022-01", "2026-09", freq="M").strftime("%Y-%m")
        pm = pd.DataFrame({k: v.reindex(idx).fillna(0.0) for k, v in monthly.items()})
        tot = pm.sum(axis=1)
        cum = tot.cumsum()
        dd = float((cum.cummax() - cum).max())
        L.append("## 3. Portefeuille : toutes les familles en même temps (walk-forward)\n")
        L.append(f"- R/mois moyen : **{tot.mean():+.2f}** ; médiane {tot.median():+.2f} ; mois positifs {int((tot > 0).sum())}/{len(tot)} ; "
                 f"meilleur {tot.max():+.1f} R, pire {tot.min():+.1f} R ; drawdown max {dd:.1f} R.")
        L.append(f"- Mois atteignant 15 R : **{int((tot >= 15).sum())}/{len(tot)}** ; mois ≥ 10 R : {int((tot >= 10).sum())}/{len(tot)}.\n")
        L.append(pm.assign(total=tot).describe().T[["mean", "std", "min", "max"]].to_markdown(floatfmt=".2f") + "\n")
    (REP / "11_STRATEGY_FAMILIES.md").write_text("\n".join(L))
    print("\n".join(L[-12:]))
    print(pd.DataFrame(summary).to_string())
    print(full.head(12).to_string())


if __name__ == "__main__":
    main()
