#!/usr/bin/env python3
"""Export Dukascopy M1 data as a CSV importable into an MT5 custom symbol.

The bars are expressed in *server time* (UTC+2/+3, same convention as the research engine) so that
MT5 builds the same H1/H4 bars as Research/sensitor/data.resample. Prices are rounded to the
symbol tick (0.01). The spread column is in points (ask_open - bid_open) / 0.01, which is what the
Strategy Tester uses in "1 minute OHLC" mode (ask = bid + spread for every generated tick).

Output: <MT5 Common>/Files/SensitorAI/XAUUSD_DK_M1.csv  (time;open;high;low;close;tick_volume;spread)
Usage:  python3 Research/scripts/export_mt5_custom.py --start 2018-07-01 --end 2019-07-01 [--out path]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))
from sensitor.data import load_m1, server_offset_seconds  # noqa: E402

DEFAULT_OUT = pathlib.Path("/root/.wine-mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files/SensitorAI")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(DEFAULT_OUT / "XAUUSD_DK_M1.csv"))
    ap.add_argument("--tick", type=float, default=0.01)
    a = ap.parse_args()
    df = load_m1("XAUUSD", a.start, a.end)
    t = df["time"].to_numpy(np.int64)
    server = t + server_offset_seconds(t)
    q = lambda x: np.round(df[x].to_numpy() / a.tick).astype(np.int64)   # integer ticks
    o, h, l, c = q("bo"), q("bh"), q("bl"), q("bc")
    h = np.maximum.reduce([h, o, c]); l = np.minimum.reduce([l, o, c])
    spread = np.maximum(q("ao") - o, 0)
    vol = np.maximum(np.round(df["vol"].to_numpy() * 10).astype(np.int64), 1)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write("time;open;high;low;close;tick_volume;spread\n")
        for i in range(len(t)):
            f.write(f"{server[i]};{o[i] * a.tick:.2f};{h[i] * a.tick:.2f};{l[i] * a.tick:.2f};{c[i] * a.tick:.2f};{vol[i]};{spread[i]}\n")
    print(f"wrote {len(t):,} bars to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
