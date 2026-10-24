#!/usr/bin/env python3
"""Draw example setups (entry-TF candles + impulse, OTE, OB, FVG, entry, SL, exits) for visual review.

The goal is a human check that the algorithmic definitions match the trader's reading of the chart.
Usage: python3 Research/scripts/plot_setups.py --config BASE --period DEV --n 8
Output: Reports/figures/setup_<id>.png and Reports/figures/README.md
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))
from sensitor.data import load_m1, MinuteData, resample  # noqa: E402

OUT = ROOT / "Research" / "output"
FIG = ROOT / "Reports" / "figures"


def candles(ax, t, o, h, l, c, width):
    for i in range(len(t)):
        col = "#2e7d32" if c[i] >= o[i] else "#c62828"
        ax.vlines(t[i], l[i], h[i], color=col, lw=0.8)
        ax.add_patch(plt.Rectangle((t[i] - width / 2, min(o[i], c[i])), width, max(abs(c[i] - o[i]), 1e-6),
                                   color=col, lw=0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="BASE")
    ap.add_argument("--variant", default="C_FIXED_5R")
    ap.add_argument("--period", default="DEV")
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args()
    tr = pd.read_parquet(OUT / f"trades_{a.config}.parquet")
    tr = tr[(tr.variant == a.variant) & (tr.period == a.period)]
    filled = tr[tr.fill_time >= 0]
    pick = pd.concat([filled[filled.r_net > 0].head(a.n // 2), filled[filled.r_net <= 0].head(a.n - a.n // 2),
                      tr[tr.outcome == "CANCELLED"].head(2)])
    t0 = int(pick.s_origin_idx.min()) if len(pick) else 0
    df = load_m1("XAUUSD", "2018-01-01", "2024-01-01")
    m1 = MinuteData.from_df(df)
    e = resample(m1, 15)
    FIG.mkdir(parents=True, exist_ok=True)
    lines = ["# Exemples de setups (revue visuelle)\n",
             "Bougies M15 (heure UTC). Bleu : OTE 62-79 %. Vert/rouge : Order Block. Doré : FVG. Blanc/noir : entrée. "
             "Rouge pointillé : SL. Triangle : exécution. Croix : sortie. Ces graphiques servent à vérifier que les "
             "définitions algorithmiques correspondent à votre lecture ; ils ne sont pas sélectionnés pour leur résultat.\n"]
    for _, s in pick.iterrows():
        a0 = int(s.s_broken_pivot) - 10
        end_t = s.exit_time if s.exit_time > 0 else (s.s_end_time if s.s_end_time > 0 else s.s_confirm_time + 86400)
        a1 = int(np.searchsorted(e.time, end_t)) + 8
        a1 = min(a1, len(e.time) - 1, a0 + 220)
        sl = slice(a0, a1)
        x = np.arange(a0, a1)
        fig, ax = plt.subplots(figsize=(12, 5.5), dpi=110)
        candles(ax, x, e.o[sl], e.h[sl], e.l[sl], e.c[sl], 0.6)
        x0, x1 = int(s.s_extreme_idx), a1
        ax.axhspan(s.s_ote_low, s.s_ote_high, xmin=(x0 - a0) / (a1 - a0), color="#1e88e5", alpha=0.15)
        ax.fill_between([s.s_ob_idx - 0.4, x1], s.s_ob_low, s.s_ob_high, color="#43a047" if s.direction > 0 else "#e53935", alpha=0.2)
        ax.fill_between([s.s_fvg_mid_idx - 1.4, s.s_fvg_mid_idx + 1.4], s.s_fvg_low, s.s_fvg_high, color="#fbc02d", alpha=0.45)
        ax.hlines(s.s_entry, x0, x1, color="black", lw=1.2)
        ax.hlines(s.s_sl, x0, x1, color="red", lw=1.0, linestyles="dashed")
        ax.plot([s.s_origin_idx, s.s_extreme_idx], [s.s_origin_price, s.s_extreme_price], color="#6a1b9a", lw=1.2)
        ax.hlines(s.s_broken_level, s.s_broken_pivot, s.s_break_bar, color="gray", lw=1, linestyles="dotted")
        ax.annotate("BOS", (s.s_break_bar, s.s_broken_level), fontsize=8, color="gray")
        if s.fill_time > 0:
            ax.plot(np.searchsorted(e.time, s.fill_time, side="right") - 1, s.fill_price, marker="^" if s.direction > 0 else "v", color="blue", ms=9)
        if s.exit_time > 0:
            ax.plot(np.searchsorted(e.time, s.exit_time, side="right") - 1, s.exit_price, marker="x", color="black", ms=9)
        when = pd.to_datetime(e.time[a0], unit="s", utc=True)
        title = (f"{s.setup_id} {'BUY' if s.direction > 0 else 'SELL'} {when:%Y-%m-%d %H:%M} UTC | case {s.s_entry_case} | "
                 f"E={s.s_entry:.2f} SL={s.s_sl:.2f} 1R={s.s_risk_dist:.2f} | {s.outcome} {s.exit_reason or s.cancel_reason} "
                 f"R={s.r_net:+.2f}")
        ax.set_title(title, fontsize=9)
        ax.set_xlim(a0 - 1, a1)
        ax.grid(alpha=0.2)
        p = FIG / f"setup_{s.setup_id}.png"
        fig.tight_layout(); fig.savefig(p); plt.close(fig)
        lines.append(f"## {s.setup_id}\n\n{title}\n\n![{s.setup_id}]({p.name})\n")
    (FIG / "README.md").write_text("\n".join(lines))
    print(f"{len(pick)} figures in {FIG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
