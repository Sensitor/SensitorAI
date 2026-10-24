#!/usr/bin/env python3
"""Generate MQL5 test fixtures from the Python reference implementation.

Writes MQL5/Include/SensitorAI/Tests/Fixtures.mqh containing:
  * the hand-built BUY scenario of Tests/python/synth.py (entry M15 + bullish H1/H4),
  * random-walk parity datasets (M15 + aggregated H1/H4) and, for several configurations,
    the setups produced by the Python engine (expected results for the MQL5 engine).
The MQL5 script Scripts/SensitorAI/SensitorTests.mq5 replays them and compares field by field.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Research"))
sys.path.insert(0, str(ROOT / "Tests" / "python"))

from sensitor.config import StrategyConfig  # noqa: E402
from sensitor.setups import Bars, SetupEngine  # noqa: E402
import synth  # noqa: E402

OUT = ROOT / "MQL5" / "Include" / "SensitorAI" / "Tests" / "Fixtures.mqh"

ENUMS = {
    "bias_flip_mode": {"FLIP_ON_CHOCH": "FLIP_ON_CHOCH", "NEUTRAL_ON_CHOCH": "NEUTRAL_ON_CHOCH"},
    "bias_mode": {"REQUIRE_BOTH": "BIAS_REQUIRE_BOTH", "H4_LEADS": "BIAS_H4_LEADS"},
    "impulse_anchor": {"SWING_CONFIRM": "ANCHOR_SWING_CONFIRM", "BOS_BAR": "ANCHOR_BOS_BAR"},
    "ob_zone_mode": {"WICK": "OB_ZONE_WICK", "BODY": "OB_ZONE_BODY"},
    "sl_anchor": {"STRUCTURAL": "SL_STRUCTURAL", "OB_DISTAL": "SL_OB_DISTAL", "IMPULSE_ORIGIN": "SL_IMPULSE_ORIGIN"},
    "rsi_mode": {"OFF": "RSI_OFF", "AT_SETUP": "RSI_AT_SETUP", "GATE_PLACEMENT": "RSI_GATE_PLACEMENT",
                 "CONTINUOUS": "RSI_CONTINUOUS"},
    "continuation_invalidation": {"CLOSE": "CONT_CLOSE", "WICK": "CONT_WICK"},
    "caution_sweep_action": {"LOG_ONLY": "SWEEP_LOG_ONLY", "BLOCK": "SWEEP_BLOCK"},
}
SCALARS = ["swing_left_htf", "swing_right_htf", "swing_left_entry", "swing_right_entry", "bos_buffer_atr",
           "liquidity_max_levels", "require_compatible_sweep", "sweep_lookback_bars", "min_impulse_atr",
           "ote_min", "ote_max", "fvg_min_atr", "ob_max_dist_bars", "ob_pre_origin_bars", "entry_depth",
           "reject_if_touched_before_placement", "sl_buffer_points", "sl_buffer_atr", "sl_add_spread_for_sells",
           "min_sl_spread_mult", "max_sl_atr", "rsi_period", "rsi_overbought", "rsi_oversold", "rsi_window",
           "cancel_on_bias_change", "partial_trigger_r", "liquidity_fallback_r"]

PARITY_CONFIGS = [
    StrategyConfig(),
    StrategyConfig(impulse_anchor="BOS_BAR", rsi_mode="GATE_PLACEMENT", continuation_invalidation="WICK",
                   bias_mode="H4_LEADS", bias_flip_mode="NEUTRAL_ON_CHOCH", entry_depth=0.0,
                   ob_zone_mode="BODY", sl_anchor="OB_DISTAL", caution_sweep_action="LOG_ONLY"),
    StrategyConfig(rsi_mode="CONTINUOUS", entry_depth=1.0, bos_buffer_atr=0.1, sl_buffer_points=5,
                   min_impulse_atr=1.0, require_compatible_sweep=False, caution_sweep_action="LOG_ONLY",
                   sl_anchor="IMPULSE_ORIGIN", reject_if_touched_before_placement=False),
]
PARITY_SEEDS = [11, 23]
PARITY_N = 5000
SPREAD = 0.2


def f(x: float) -> str:
    if x != x:  # NaN
        return "EMPTY_VALUE"
    r = repr(float(x))
    return r if ("." in r or "e" in r or "inf" in r) else r + ".0"


def arr(name: str, vals, ctype="double") -> str:
    body = ",".join(f(v) if ctype == "double" else str(int(v)) for v in vals)
    return f"{ctype} {name}[]={{{body}}};\n"


def str_arr(name: str, vals) -> str:
    return f"string {name}[]={{" + ",".join('"' + v + '"' for v in vals) + "};\n"


def random_dataset(seed: int, n: int):
    rng = np.random.default_rng(seed)
    c = 2000 + np.cumsum(rng.normal(0, 0.6, n)) + np.sin(np.arange(n) / 40) * 6
    o = np.concatenate(([2000.0], c[:-1]))
    h = np.maximum(o, c) + rng.uniform(0, 0.6, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.6, n)
    # round to the 0.01 tick like a broker feed
    o, h, l, c = (np.round(x, 2) for x in (o, h, l, c))
    h = np.maximum.reduce([h, o, c])
    l = np.minimum.reduce([l, o, c])
    t = synth.T0 + np.arange(n, dtype=np.int64) * 900
    m15 = Bars(15, t, o, h, l, c)

    def agg(b: Bars, k: int, tf: int) -> Bars:
        m = len(b) // k
        return Bars(tf, b.time[: m * k: k], b.o[: m * k: k], b.h[: m * k].reshape(m, k).max(1),
                    b.l[: m * k].reshape(m, k).min(1), b.c[k - 1: m * k: k])
    return m15, agg(m15, 4, 60), agg(m15, 16, 240)


def cfg_block(i: int, cfg: StrategyConfig) -> str:
    lines = [f"SConfig ParityConfig{i}()\n  {{\n   SConfig c=ConfigDefaults();\n"]
    for k, mp in ENUMS.items():
        lines.append(f"   c.{k}={mp[getattr(cfg, k)]};\n")
    for k in SCALARS:
        v = getattr(cfg, k)
        if isinstance(v, bool):
            lines.append(f"   c.{k}={'true' if v else 'false'};\n")
        else:
            lines.append(f"   c.{k}={v};\n")
    lines.append("   c.entry_tf=PERIOD_M15; c.liquidity_tf=PERIOD_H1;\n   return c;\n  }\n")
    return "".join(lines)


def bars_block(prefix: str, b: Bars) -> str:
    return (arr(prefix + "_t", b.time, "long") + arr(prefix + "_o", b.o) + arr(prefix + "_h", b.h)
            + arr(prefix + "_l", b.l) + arr(prefix + "_c", b.c))


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = ["// AUTO-GENERATED by Research/scripts/gen_mql5_fixtures.py - do not edit.\n",
             "#ifndef SENSITOR_FIXTURES_MQH\n#define SENSITOR_FIXTURES_MQH\n#include \"../Config.mqh\"\n\n",
             f"#define FX_T0 {synth.T0}\n#define FX_PREFIX {synth.PREFIX}\n#define FX_SPREAD {SPREAD}\n\n"]
    e, h1, h4 = synth.scenario()
    parts.append(bars_block("SC_E", e) + bars_block("SC_H1", h1) + bars_block("SC_H4", h4))
    parts.append(f"#define PARITY_N_CONFIGS {len(PARITY_CONFIGS)}\n#define PARITY_N_SEEDS {len(PARITY_SEEDS)}\n")
    for i, cfg in enumerate(PARITY_CONFIGS):
        parts.append(cfg_block(i, cfg))
    total = 0
    for si, seed in enumerate(PARITY_SEEDS):
        m15, ph1, ph4 = random_dataset(seed, PARITY_N)
        parts.append(bars_block(f"PD{si}_E", m15) + bars_block(f"PD{si}_H1", ph1) + bars_block(f"PD{si}_H4", ph4))
        for ci, cfg in enumerate(PARITY_CONFIGS):
            eng = SetupEngine(cfg, m15, ph1, ph4, lambda t: SPREAD, tick=0.01)
            eng.run()
            S = eng.setups
            total += len(S)
            p = f"EX{si}_{ci}"
            parts.append(f"#define {p}_N {len(S)}\n")
            parts.append(str_arr(p + "_id", [s.id for s in S]))
            parts.append(str_arr(p + "_status", [s.status for s in S]))
            parts.append(str_arr(p + "_reason", [s.reason for s in S]))
            parts.append(str_arr(p + "_end_reason", [s.end_reason for s in S]))
            for fld in ("confirm_bar", "place_bar", "end_bar", "ob_idx", "fvg_mid_idx"):
                parts.append(arr(f"{p}_{fld}", [getattr(s, fld) for s in S], "int"))
            for fld in ("entry", "sl", "ote_low", "ote_high", "ob_low", "ob_high", "fvg_low", "fvg_high",
                        "tp_liquidity", "risk_dist"):
                parts.append(arr(f"{p}_{fld}", [getattr(s, fld) for s in S]))
            print(f"seed={seed} cfg={ci}: {len(S)} setups "
                  f"({sum(s.status == 'SETUP_VALID' or s.status == 'INVALIDATED' for s in S)} valid/invalidated)")
    parts.append("#endif\n")
    OUT.write_text("".join(parts))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KiB, {total} expected setups)")


if __name__ == "__main__":
    main()
