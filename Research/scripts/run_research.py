#!/usr/bin/env python3
"""Run the pre-registered experiments (Research/EXPERIMENT_PLAN.md).

Stages (run in this order, each only once for VAL/TEST):
  dev   : experiments E1-E6 + walk-forward on DEV; applies the selection rule -> Reports/selected_config.json
  val   : selected config (and baseline) on VAL -> Reports/05_VALIDATION.md
  test  : frozen config on TEST (holdout, run once) -> Reports/06_FINAL_TEST.md

Raw outputs go to Research/output/ (not versioned); markdown reports to Reports/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))

from sensitor.config import AccountModel, CostModel, StrategyConfig  # noqa: E402
from sensitor.metrics import funnel, max_drawdown, summarize_r  # noqa: E402
from sensitor.data import session_of  # noqa: E402
from sensitor.pipeline import (PERIODS, RUNNERS, Market, by_year, closed, paired_diff, period_of,  # noqa: E402
                               run_signals, setups_frame, simulate, variant_table, ts)
from sensitor.portfolio import run_portfolio  # noqa: E402

OUT = ROOT / "Research" / "output"
REP = ROOT / "Reports"
BASE = StrategyConfig()
COSTS = CostModel()
STRESS = CostModel(commission_per_lot_rt=10.5, stop_slippage=0.30, partial_slippage=0.15,
                   swap_long_per_lot=-80.0, swap_short_per_lot=-30.0, extra_spread=0.20)
ZERO = CostModel(commission_per_lot_rt=0.0, stop_slippage=0.0, partial_slippage=0.0,
                 swap_long_per_lot=0.0, swap_short_per_lot=0.0)

SIGNAL_CONFIGS = {
    "BASE": BASE,
    "RSI_OFF": BASE.replace(rsi_mode="OFF"),
    "RSI_GATE": BASE.replace(rsi_mode="GATE_PLACEMENT"),
    "RSI_CONTINUOUS": BASE.replace(rsi_mode="CONTINUOUS"),
    "DEPTH_0": BASE.replace(entry_depth=0.0),
    "DEPTH_1": BASE.replace(entry_depth=1.0),
    "ENTRY_M5": BASE.replace(entry_tf=5),
    "SWEEP_LOG_ONLY": BASE.replace(caution_sweep_action="LOG_ONLY"),
    "INV_WICK": BASE.replace(continuation_invalidation="WICK"),
    "BIAS_H4_LEADS": BASE.replace(bias_mode="H4_LEADS"),
    "FLIP_NEUTRAL": BASE.replace(bias_flip_mode="NEUTRAL_ON_CHOCH"),
    "IMPULSE_BOS_BAR": BASE.replace(impulse_anchor="BOS_BAR"),
    "SWING_ENTRY_3": BASE.replace(swing_left_entry=3, swing_right_entry=3),
    "SL_BUFFER_025": BASE.replace(sl_buffer_atr=0.25),
}
EXPERIMENT = {
    "BASE": "E1/E2", "RSI_OFF": "E3", "RSI_GATE": "E3", "RSI_CONTINUOUS": "E3", "DEPTH_0": "E4", "DEPTH_1": "E4",
    "ENTRY_M5": "E5", "SWEEP_LOG_ONLY": "E6", "INV_WICK": "E6", "BIAS_H4_LEADS": "E6", "FLIP_NEUTRAL": "E6",
    "IMPULSE_BOS_BAR": "E6", "SWING_ENTRY_3": "E6", "SL_BUFFER_025": "E6",
}
BASE_RUNNER = "C_FIXED_5R"


def git_rev() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def md(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if df is None or df.empty:
        return "_(aucune donnée)_\n"
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_integer_dtype(df[col]):
            df[col] = df[col].astype(str)       # keep integers (years, counts) unformatted
    return df.to_markdown(index=False, floatfmt=floatfmt) + "\n\n"


def fmt_pct(x):
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f} %"


def header(title: str, mk: Market, extra: str = "") -> str:
    t0 = pd.to_datetime(mk.m1.time[0], unit="s", utc=True)
    t1 = pd.to_datetime(mk.m1.time[-1], unit="s", utc=True)
    return (f"# {title}\n\n"
            f"- Généré le {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC, code `{git_rev()}`\n"
            f"- Données : Dukascopy XAUUSD M1 Bid/Ask, {t0:%Y-%m-%d} → {t1:%Y-%m-%d} ({len(mk.m1.time):,} minutes)\n"
            f"- Coûts de base : {json.dumps(COSTS.as_dict())}\n"
            f"- Périodes : {json.dumps(PERIODS)}\n{extra}\n"
            "> Résultats de simulation sur données historiques d'un fournisseur qui n'est pas le broker final. "
            "Ils ne constituent ni une preuve ni une promesse de rentabilité future.\n\n")


# ------------------------------------------------------------------------------------------------
def load() -> Market:
    t = time.time()
    mk = Market.load("2018-01-01", "2026-10-01")
    print(f"market loaded in {time.time() - t:.0f}s: {len(mk.m1.time):,} M1 bars", flush=True)
    return mk


def run_all_configs(mk: Market) -> dict:
    res = {}
    for name, cfg in SIGNAL_CONFIGS.items():
        t = time.time()
        eng = run_signals(cfg, mk)
        tr = simulate(eng, mk, cfg, COSTS)
        st = setups_frame(eng)
        OUT.mkdir(parents=True, exist_ok=True)
        tr.to_parquet(OUT / f"trades_{name}.parquet")
        st.to_parquet(OUT / f"setups_{name}.parquet")
        res[name] = (cfg, eng, tr, st)
        print(f"{name}: {len(st)} setups, {tr['setup_id'].nunique() if len(tr) else 0} placed, {time.time() - t:.0f}s", flush=True)
    return res


def selection(dev_table: pd.DataFrame, res: dict) -> tuple[str, str, list[str]]:
    """Apply the pre-registered rule. Returns (signal config, runner, log lines)."""
    log = []
    base_row = dev_table[(dev_table.config == "BASE") & (dev_table.variant == BASE_RUNNER)].iloc[0]
    log.append(f"Baseline BASE/{BASE_RUNNER}: n={base_row.trades}, E={base_row.expectancy_r:.3f}R, PF={base_row.profit_factor_r:.2f}")
    cands = []
    for _, r in dev_table.iterrows():
        tr = res[r.config][2]
        c = closed(tr[(tr.period == "DEV") & (tr.variant == r.variant)])
        rr = np.sort(c["r_net"].to_numpy())
        ok_n = r.trades >= 100
        ok_pf = r.profit_factor_r >= 1.10
        ok_best = len(rr) > 1 and rr[:-1].mean() > 0
        yr = by_year(tr[tr.period == "DEV"], r.variant)
        ok_years = (yr["expectancy_r"] > 0).sum() >= 3 if len(yr) else False
        if ok_n and ok_pf and ok_best and ok_years:
            cands.append((r.expectancy_r, r.config, r.variant, r.t_stat))
    if not cands:
        log.append("Aucune variante ne satisfait toutes les contraintes (n>=100, PF>=1.10, espérance hors meilleur "
                   "trade > 0, >=3 années positives sur 4). Conformément au plan, la baseline est conservée et la "
                   "conclusion DEV est : pas d'avantage démontré.")
        return "BASE", BASE_RUNNER, log
    cands.sort(reverse=True)
    best = cands[0]
    log.append(f"Meilleure variante admissible : {best[1]}/{best[2]} E={best[0]:.3f}R t={best[3]:.2f}")
    if best[1] == "BASE" and best[2] == BASE_RUNNER:
        return "BASE", BASE_RUNNER, log
    # a runner-only change on BASE signals must beat the base runner on paired differences
    if best[1] == "BASE":
        pdiff = paired_diff(res["BASE"][2], best[2], BASE_RUNNER, "DEV")
        log.append(f"Différence appariée {best[2]} - {BASE_RUNNER}: {pdiff}")
        if pdiff.get("ci_low", -1) <= 0:
            log.append("IC de la différence appariée inclut 0 : baseline conservée.")
            return "BASE", BASE_RUNNER, log
    else:
        # different signal set: require a clearly better expectancy than the baseline (CI of best above base E)
        tr = res[best[1]][2]
        c = closed(tr[(tr.period == "DEV") & (tr.variant == best[2])])
        s = summarize_r(c["r_net"].to_numpy())
        log.append(f"IC95 espérance {best[1]}/{best[2]}: [{s['ci95_low']:.3f}, {s['ci95_high']:.3f}] vs baseline {base_row.expectancy_r:.3f}")
        if s["ci95_low"] <= base_row.expectancy_r:
            log.append("L'IC de la variante recouvre l'espérance de la baseline : la variante est retenue seulement "
                       "si la baseline n'est elle-même pas admissible.")
            base_ok = any(c_[1] == "BASE" and c_[2] == BASE_RUNNER for c_ in cands)
            if base_ok:
                return "BASE", BASE_RUNNER, log
    log.append(f"Sélection : {best[1]}/{best[2]}")
    return best[1], best[2], log


def walk_forward(res: dict) -> tuple[pd.DataFrame, list[str]]:
    """Anchored yearly WF over 2020..2024 choosing {runner x entry depth} on [2019, Y-1]."""
    pool = {k: res[k][2] for k in ("BASE", "DEPTH_0", "DEPTH_1")}
    rows, log = [], []
    for Y in range(2020, 2025):
        a, b = ts("2019-01-01"), ts(f"{Y}-01-01")
        best = None
        for cname, tr in pool.items():
            c = closed(tr)
            ins = c[(c.fill_time >= a) & (c.fill_time < b)]
            for v, g in ins.groupby("variant"):
                e = g["r_net"].mean() if len(g) >= 20 else -math.inf
                if best is None or e > best[0]:
                    best = (e, cname, v)
        if best is None or best[0] == -math.inf:
            log.append(f"{Y}: pas assez de trades in-sample (< 20) pour choisir, année ignorée")
            continue
        cname, v = best[1], best[2]
        c = closed(pool[cname])
        oos = c[(c.variant == v) & (c.fill_time >= ts(f"{Y}-01-01")) & (c.fill_time < ts(f"{Y + 1}-01-01"))]
        for _, r in oos.iterrows():
            rows.append({"year": Y, "config": cname, "variant": v, "r_net": r["r_net"]})
        log.append(f"{Y}: choisi {cname}/{v} (E in-sample={best[0]:.3f}R) -> OOS n={len(oos)} E={oos['r_net'].mean() if len(oos) else float('nan'):.3f}R")
    return pd.DataFrame(rows), log


def money_stats(trades: pd.DataFrame, cfg: StrategyConfig, variant: str, mk: Market, costs: CostModel) -> dict:
    sub = trades[trades.variant == variant]
    if sub.empty:
        return {}
    acct = AccountModel()
    pf, eq = run_portfolio(sub, cfg, costs, acct, lambda t: int(mk.m1.server_offset[min(mk.m1.index_at_or_after(t), len(mk.m1.time) - 1)]))
    placed = pf[pf.pf_status == "PLACED"]
    traded = placed[placed.pnl != 0]
    dd, ddp = max_drawdown(eq["balance"].to_numpy(), acct.initial_balance) if len(eq) else (0.0, 0.0)
    gp = traded.loc[traded.pnl > 0, "pnl"].sum()
    gl = -traded.loc[traded.pnl < 0, "pnl"].sum()
    return {"trades": len(traded), "rejected_by_limits": int((pf.pf_status != "PLACED").sum()),
            "net_profit": float(traded.pnl.sum()), "final_balance": float(acct.initial_balance + traded.pnl.sum()),
            "profit_factor": float(gp / gl) if gl > 0 else math.inf, "max_dd": dd, "max_dd_pct": ddp,
            "reject_reasons": pf.pf_status.value_counts().to_dict()}


def breakdowns(trades: pd.DataFrame, variant: str, period: str) -> str:
    c = closed(trades[(trades.variant == variant) & (trades.period == period)]).copy()
    if c.empty:
        return "_(aucun trade)_\n"
    c["session"] = [session_of(int(t)) for t in c.fill_time]
    c["side"] = np.where(c.direction > 0, "BUY", "SELL")
    c["month"] = pd.to_datetime(c.fill_time, unit="s", utc=True).dt.strftime("%Y-%m")
    c["year"] = pd.to_datetime(c.fill_time, unit="s", utc=True).dt.year
    vol = c["s_atr"] / c["fill_price"]
    c["vol_regime"] = pd.qcut(vol, 3, labels=["LOW_VOL", "MID_VOL", "HIGH_VOL"]) if len(c) >= 6 else "ALL"
    out = []
    for key in ("year", "session", "side", "vol_regime", "exit_reason", "s_entry_case"):
        rows = []
        for g, sub in c.groupby(key, observed=True):
            s = summarize_r(sub["r_net"].to_numpy())
            rows.append({key: g, "trades": s["trades"], "win_rate": s["win_rate"], "expectancy_r": s["expectancy_r"],
                         "total_r": s["total_r"], "pf_r": s["profit_factor_r"]})
        out.append(f"**Par {key}**\n\n" + md(pd.DataFrame(rows)))
    months = c.groupby("month")["r_net"].sum()
    out.append(f"**Par mois** : {int((months > 0).sum())} mois positifs / {len(months)} ; "
               f"meilleur {months.max():.2f}R, pire {months.min():.2f}R\n")
    out.append(f"**Coûts moyens** (R/trade) : commission {c.r_commission.mean():.3f}, swap {c.r_swap.mean():.3f} ; "
               f"spread moyen à l'exécution {c.spread_at_fill.mean():.3f} $ ; 1R moyen {c.risk_dist.mean():.2f} $ ; "
               f"détention moyenne {((c.exit_time - c.fill_time) / 3600).mean():.1f} h\n")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------
def stage_dev(mk: Market) -> None:
    res = run_all_configs(mk)
    n_variants = len(SIGNAL_CONFIGS) * len(RUNNERS)
    tables = pd.concat([variant_table(res[k][2], "DEV", k) for k in res], ignore_index=True)
    tables["experiment"] = tables["config"].map(EXPERIMENT)
    tables.to_csv(OUT / "dev_variants.csv", index=False)
    cols = ["experiment", "config", "variant", "trades", "placed", "fill_rate", "win_rate", "expectancy_r", "ci95_low",
            "ci95_high", "t_stat", "profit_factor_r", "total_r", "max_dd_r", "avg_cost_r"]
    base_cfg, base_eng, base_tr, base_st = res["BASE"]
    # --- E1 funnel
    st_dev = base_st[base_st.period == "DEV"]
    tr_dev = base_tr[(base_tr.period == "DEV") & (base_tr.variant == BASE_RUNNER)]
    fun = funnel(st_dev, tr_dev)
    reasons = st_dev.groupby(["status", "reason"]).size().reset_index(name="n").sort_values("n", ascending=False)
    ends = st_dev[st_dev.end_reason != ""].groupby("end_reason").size().reset_index(name="n")
    # --- E2 runner comparison on identical signals
    e2 = tables[tables.config == "BASE"][cols]
    pdiffs = []
    for v in RUNNERS:
        if v != BASE_RUNNER:
            d = paired_diff(base_tr, v, BASE_RUNNER, "DEV")
            d["comparison"] = f"{v} - {BASE_RUNNER}"
            pdiffs.append(d)
    years = {v: by_year(base_tr[base_tr.period == "DEV"], v) for v in RUNNERS}
    # --- cost sensitivity on baseline signals
    cost_rows = []
    for cname, cm in (("zéro coût", ZERO), ("base", COSTS), ("stress", STRESS)):
        trc = simulate(base_eng, mk, base_cfg, cm)
        for v in RUNNERS:
            c = closed(trc[(trc.period == "DEV") & (trc.variant == v)])
            s = summarize_r(c["r_net"].to_numpy())
            cost_rows.append({"costs": cname, "variant": v, "trades": s["trades"], "expectancy_r": s.get("expectancy_r"),
                              "profit_factor_r": s.get("profit_factor_r"), "total_r": s.get("total_r")})
    # --- selection + walk-forward
    sel_cfg, sel_runner, sel_log = selection(tables, res)
    wf, wf_log = walk_forward(res)
    wf_s = summarize_r(wf["r_net"].to_numpy()) if len(wf) else {"trades": 0}
    money = money_stats(base_tr[base_tr.period == "DEV"], base_cfg, BASE_RUNNER, mk, COSTS)
    best_t = tables["t_stat"].replace([np.inf, -np.inf], np.nan).max()
    thr = math.sqrt(2 * math.log(n_variants))

    selected = {"signal_config": sel_cfg, "runner": sel_runner,
                "config": SIGNAL_CONFIGS[sel_cfg].replace(
                    runner_method=RUNNERS[sel_runner][0],
                    runner_target_r=RUNNERS[sel_runner][1] or SIGNAL_CONFIGS[sel_cfg].runner_target_r).as_dict(),
                "selected_on": "DEV", "code": git_rev(), "n_variants_tested": n_variants}
    (REP / "selected_config.json").write_text(json.dumps(selected, indent=2))

    # ---------------- report: backtest DEV
    txt = header("Rapport de backtest — période de développement (DEV 2019-2022)", mk,
                 f"- Variantes testées : **{n_variants}** ({len(SIGNAL_CONFIGS)} configurations de signaux × {len(RUNNERS)} runners)\n")
    txt += "## 1. Entonnoir des signaux (baseline, DEV)\n\n" + md(pd.DataFrame([fun]))
    txt += "\n**Raisons de rejet / statut des setups (DEV)**\n\n" + md(reasons)
    txt += "\n**Invalidations des setups valides (DEV)**\n\n" + md(ends)
    txt += f"\n## 2. Baseline {BASE_RUNNER} — statistiques (DEV)\n\n" + md(e2[e2.variant == BASE_RUNNER])
    txt += "\n**Simulation de compte (10 000 $, 1 %, limites de risque)**\n\n```\n" + json.dumps(money, indent=2, default=str) + "\n```\n"
    txt += "\n## 3. Ventilations (baseline, DEV)\n\n" + breakdowns(base_tr, BASE_RUNNER, "DEV")
    txt += "\n## 4. Toutes les variantes (DEV)\n\n" + md(tables[cols].sort_values(["experiment", "config", "variant"]))
    txt += (f"\n## 5. Comparaisons multiples\n\n- Nombre de variantes : {n_variants}\n"
            f"- Meilleur t observé : {best_t:.2f} ; seuil « hasard » √(2 ln N) ≈ {thr:.2f}\n"
            f"- Conclusion : {'au-dessus du seuil' if best_t > thr else 'aucune variante ne dépasse ce qui est attendu par le seul hasard'}\n")
    txt += "\n## 6. Sensibilité aux coûts (signaux baseline, DEV)\n\n" + md(pd.DataFrame(cost_rows))
    txt += "\n## 7. Walk-forward ancré (choix runner × profondeur d'entrée)\n\n" + "\n".join(f"- {l}" for l in wf_log)
    txt += "\n\n" + md(pd.DataFrame([wf_s]))
    txt += "\n## 8. Application de la règle de sélection pré-enregistrée\n\n" + "\n".join(f"- {l}" for l in sel_log)
    txt += f"\n\nConfiguration retenue pour la validation : `{sel_cfg}` / `{sel_runner}` (Reports/selected_config.json)\n"
    (REP / "03_BACKTEST_DEV.md").write_text(txt)

    # ---------------- report: runner comparison
    txt = header("Comparaison des méthodes de sortie du runner (mêmes signaux, DEV)", mk)
    txt += ("Toutes les méthodes utilisent **exactement les mêmes setups exécutés** (signaux baseline), les mêmes coûts "
            "et la même période. Seule la gestion des 50 % restants après la prise partielle à +3R diffère.\n\n")
    txt += md(e2)
    txt += "\n**Différences appariées (bootstrap, mêmes trades)**\n\n" + md(pd.DataFrame(pdiffs))
    txt += "\n**Stabilité par année**\n\n"
    for v, y in years.items():
        txt += f"_{v}_\n\n" + md(y)
    txt += "\n**Sensibilité aux coûts**\n\n" + md(pd.DataFrame(cost_rows))
    txt += (f"\n**Avertissement** : {n_variants} variantes ont été évaluées au total ; les écarts entre méthodes "
            "doivent être lus à la lumière des intervalles de confiance ci-dessus. Le choix d'une méthode ne repose "
            "pas sur le profit total.\n")
    (REP / "04_RUNNER_COMPARISON.md").write_text(txt)
    print("\n".join(sel_log))


def stage_eval(mk: Market, period: str, report: str, title: str) -> None:
    sel = json.loads((REP / "selected_config.json").read_text())
    cfg = StrategyConfig(**{k: tuple(v) if k == "bias_tfs" else v for k, v in sel["config"].items()})
    runner = sel["runner"]
    eng = run_signals(cfg, mk)
    tr = simulate(eng, mk, cfg, COSTS)
    st = setups_frame(eng)
    tr.to_parquet(OUT / f"trades_{period}_selected.parquet")
    tab = variant_table(tr, period, sel["signal_config"])
    c = closed(tr[(tr.period == period) & (tr.variant == runner)])
    s = summarize_r(c["r_net"].to_numpy())
    fun = funnel(st[st.period == period], tr[(tr.period == period) & (tr.variant == runner)])
    money = money_stats(tr[tr.period == period], cfg, runner, mk, COSTS)
    trs = simulate(eng, mk, cfg, STRESS)
    cs = closed(trs[(trs.period == period) & (trs.variant == runner)])
    ss = summarize_r(cs["r_net"].to_numpy())
    txt = header(title, mk, f"- Configuration gelée : `{sel['signal_config']}` / `{runner}` sélectionnée sur DEV (code {sel['code']})\n"
                            f"- Variantes testées en amont : {sel['n_variants_tested']}\n")
    txt += f"## Résultat principal ({runner})\n\n" + md(pd.DataFrame([s]))
    txt += "\n## Entonnoir\n\n" + md(pd.DataFrame([fun]))
    txt += "\n## Compte simulé (10 000 $, 1 %)\n\n```\n" + json.dumps(money, indent=2, default=str) + "\n```\n"
    txt += "\n## Coûts « stress »\n\n" + md(pd.DataFrame([ss]))
    txt += "\n## Autres méthodes de runner (information, non utilisées pour décider)\n\n" + md(tab)
    txt += "\n## Ventilations\n\n" + breakdowns(tr, runner, period)
    (REP / report).write_text(txt)
    summary = {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in s.items()}
    summary.update(period=period, runner=runner, signal_config=sel["signal_config"], code=git_rev())
    (REP / ("validation_summary.json" if period == "VAL" else "test_summary.json")).write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["dev", "val", "test"])
    args = ap.parse_args()
    mk = load()
    if args.stage == "dev":
        stage_dev(mk)
    elif args.stage == "val":
        stage_eval(mk, "VAL", "05_VALIDATION.md", "Validation hors échantillon (VAL 2023-01 → 2024-06)")
    else:
        marker = REP / ".test_stage_done"
        if marker.exists():
            print("TEST stage already executed once; refusing to re-run (see EXPERIMENT_PLAN.md).")
            return 1
        stage_eval(mk, "TEST", "06_FINAL_TEST.md", "Test final sur données jamais utilisées (TEST 2024-07 → 2026-09)")
        marker.write_text(dt.datetime.utcnow().isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
