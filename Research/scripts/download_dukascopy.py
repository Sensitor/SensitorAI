#!/usr/bin/env python3
"""Download Dukascopy M1 BID and ASK candles for a symbol (default XAUUSD).

Dukascopy publishes one LZMA-compressed file per day and per side:
    https://datafeed.dukascopy.com/datafeed/{SYM}/{YYYY}/{MM0}/{DD}/{SIDE}_candles_min_1.bi5
where MM0 is the 0-based month. Each record is 24 bytes, big endian:
    int32 seconds_from_day_start, int32 open, int32 close, int32 low, int32 high, float32 volume
Prices are integers in units of `point` (0.001 for XAUUSD).

Files are cached under Research/data/raw/dukascopy/{SYM}/{SIDE}/YYYY/MM/DD.bi5.
An empty file (0 bytes) marks a day for which the server returned no data (weekends, holidays).

Usage:
    python3 Research/scripts/download_dukascopy.py --start 2018-01-01 --end 2026-10-01
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "Research" / "data" / "raw" / "dukascopy"
URL = "https://datafeed.dukascopy.com/datafeed/{sym}/{y:04d}/{m0:02d}/{d:02d}/{side}_candles_min_1.bi5"


def fetch(sym: str, side: str, day: dt.date, retries: int = 8) -> str:
    out = RAW / sym / side / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}.bi5"
    if out.exists():
        return "cached"
    out.parent.mkdir(parents=True, exist_ok=True)
    url = URL.format(sym=sym, y=day.year, m0=day.month - 1, d=day.day, side=side)
    delay = 2.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            tmp = out.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.rename(out)
            return "ok" if data else "empty"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                out.write_bytes(b"")
                return "404"
            err = f"http {e.code}"
        except Exception as e:  # network errors, timeouts
            err = repr(e)
        time.sleep(delay + random.random())
        delay = min(delay * 2, 60)
    return f"failed: {err}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-10-01", help="exclusive")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    jobs = []
    d = start
    while d < end:
        if d.weekday() != 5:  # Saturday never trades; Sunday evening does
            for side in ("BID", "ASK"):
                jobs.append((side, d))
        d += dt.timedelta(days=1)

    stats: dict[str, int] = {}
    failed = []
    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(fetch, args.symbol, s, day): (s, day) for s, day in jobs}
        for i, f in enumerate(cf.as_completed(futs), 1):
            res = f.result()
            key = res.split(":")[0]
            stats[key] = stats.get(key, 0) + 1
            if key == "failed":
                failed.append((futs[f], res))
            if i % 200 == 0:
                print(f"{i}/{len(jobs)} {stats}", flush=True)
    print("done", stats)
    for (side, day), res in failed:
        print("FAILED", side, day, res)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
