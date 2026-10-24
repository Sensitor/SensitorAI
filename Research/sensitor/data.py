"""Historical data loading: Dukascopy M1 BID/ASK candles -> minute arrays and resampled bars.

Bars of every timeframe are built from BID M1 candles (MT5 charts are Bid based) and aligned on
*broker server time* (default UTC+2 / UTC+3 during US DST, i.e. server midnight = 17:00 New York).
This matters for H4 bars and for the daily risk limits. The broker's real offset must be checked
(Docs/LIMITATIONS.md).
"""
from __future__ import annotations

import datetime as dt
import lzma
import pathlib
import struct
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .setups import Bars

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "Research" / "data" / "raw" / "dukascopy"
CACHE = ROOT / "Research" / "data" / "cache"
POINT = {"XAUUSD": 0.001}
REC = struct.Struct(">5if")


def read_bi5(path: pathlib.Path, day: dt.date, point: float) -> pd.DataFrame | None:
    blob = path.read_bytes()
    if not blob:
        return None
    raw = lzma.decompress(blob)
    n = len(raw) // REC.size
    arr = np.frombuffer(raw[: n * REC.size], dtype=np.dtype([("t", ">i4"), ("o", ">i4"), ("c", ">i4"),
                                                              ("l", ">i4"), ("h", ">i4"), ("v", ">f4")]))
    base = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp())
    return pd.DataFrame({
        "time": base + arr["t"].astype(np.int64),
        "o": arr["o"].astype(np.float64) * point,
        "h": arr["h"].astype(np.float64) * point,
        "l": arr["l"].astype(np.float64) * point,
        "c": arr["c"].astype(np.float64) * point,
        "v": arr["v"].astype(np.float64),
    })


def build_year(symbol: str, year: int) -> pd.DataFrame:
    """Merge BID and ASK minute candles of one year. Minutes without ticks (volume 0) are dropped."""
    point = POINT.get(symbol, 0.001)
    rows = []
    d = dt.date(year, 1, 1)
    while d.year == year:
        sides = {}
        for side in ("BID", "ASK"):
            p = RAW / symbol / side / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}.bi5"
            sides[side] = read_bi5(p, d, point) if p.exists() else None
        if sides["BID"] is not None and sides["ASK"] is not None:
            b, a = sides["BID"], sides["ASK"]
            m = b.merge(a, on="time", suffixes=("_b", "_a"))
            m = m[(m["v_b"] > 0) & (m["v_a"] > 0)]
            rows.append(m)
        d += dt.timedelta(days=1)
    if not rows:
        return pd.DataFrame()
    df = pd.concat(rows, ignore_index=True)
    df = df.rename(columns={"o_b": "bo", "h_b": "bh", "l_b": "bl", "c_b": "bc", "v_b": "vol",
                            "o_a": "ao", "h_a": "ah", "l_a": "al", "c_a": "ac"}).drop(columns=["v_a"])
    return df.sort_values("time").reset_index(drop=True)


def load_m1(symbol: str = "XAUUSD", start: str = "2018-01-01", end: str = "2026-10-01") -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    y0, y1 = int(start[:4]), int(end[:4])
    parts = []
    for y in range(y0, y1 + 1):
        # the cache key includes the number of raw daily files so that a partially downloaded year
        # is never frozen: new files => new cache entry
        nraw = sum(1 for _ in (RAW / symbol).glob(f"*/{y:04d}/*/*.bi5"))
        if nraw == 0:
            continue
        f = CACHE / f"{symbol}_M1_{y}_{nraw}.parquet"
        if not f.exists():
            df = build_year(symbol, y)
            if df.empty:
                continue
            df.to_parquet(f)
        parts.append(pd.read_parquet(f))
    df = pd.concat(parts, ignore_index=True)
    t0 = int(pd.Timestamp(start, tz="UTC").timestamp())
    t1 = int(pd.Timestamp(end, tz="UTC").timestamp())
    return df[(df["time"] >= t0) & (df["time"] < t1)].reset_index(drop=True)


def server_offset_seconds(utc_seconds: np.ndarray, winter: int = 2, summer: int = 3) -> np.ndarray:
    """Broker server offset assuming the common 'New York close' convention (US DST rules)."""
    ts = pd.to_datetime(utc_seconds, unit="s", utc=True)
    dst = _dst_fast(ts)
    return np.where(dst, summer, winter).astype(np.int64) * 3600


def _dst_fast(ts: pd.DatetimeIndex) -> np.ndarray:
    # US DST: second Sunday of March 07:00 UTC -> first Sunday of November 06:00 UTC
    years = np.unique(ts.year)
    out = np.zeros(len(ts), dtype=bool)
    tsec = ts.asi8 // 10**9
    for y in years:
        mar = pd.Timestamp(year=y, month=3, day=1, tz="UTC")
        start = mar + pd.Timedelta(days=(6 - mar.weekday()) % 7 + 7, hours=7)
        nov = pd.Timestamp(year=y, month=11, day=1, tz="UTC")
        end = nov + pd.Timedelta(days=(6 - nov.weekday()) % 7, hours=6)
        out |= (tsec >= start.timestamp()) & (tsec < end.timestamp())
    return out


@dataclass
class MinuteData:
    time: np.ndarray
    bo: np.ndarray
    bh: np.ndarray
    bl: np.ndarray
    bc: np.ndarray
    ao: np.ndarray
    ah: np.ndarray
    al: np.ndarray
    ac: np.ndarray
    server_offset: np.ndarray

    @classmethod
    def from_df(cls, df: pd.DataFrame, winter: int = 2, summer: int = 3) -> "MinuteData":
        t = df["time"].to_numpy(np.int64)
        return cls(t, *(df[c].to_numpy(np.float64) for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")),
                   server_offset=server_offset_seconds(t, winter, summer))

    def index_at_or_after(self, t: int) -> int:
        return int(np.searchsorted(self.time, t, side="left"))

    def spread_at(self, t: int) -> float:
        j = self.index_at_or_after(t)
        if j >= len(self.time):
            j = len(self.time) - 1
        return float(self.ao[j] - self.bo[j])


def resample(m1: MinuteData, tf: int) -> Bars:
    """Bid OHLC bars of `tf` minutes aligned on server time."""
    server = m1.time + m1.server_offset
    key = server // (tf * 60)
    change = np.flatnonzero(np.diff(key)) + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [len(key)]))
    o = m1.bo[starts]
    c = m1.bc[ends - 1]
    h = np.maximum.reduceat(m1.bh, starts)
    l = np.minimum.reduceat(m1.bl, starts)
    open_server = key[starts] * tf * 60
    open_utc = open_server - m1.server_offset[starts]
    return Bars(tf, open_utc.astype(np.int64), o, h, l, c)


def session_of(utc_seconds: int) -> str:
    """UTC session buckets used for analysis (Docs/SPECIFICATION.md RK-15)."""
    hour = (utc_seconds // 3600) % 24
    if hour < 7:
        return "ASIA"
    if hour < 12:
        return "LONDON"
    if hour < 16:
        return "LDN_NY_OVERLAP"
    if hour < 21:
        return "NEW_YORK"
    return "LATE"
