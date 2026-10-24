"""Position sizing and volume rules (pure functions, mirrored in MQL5/Include/SensitorAI/RiskManager.mqh).

In the EA the loss per lot comes from `OrderCalcProfit` (account currency, broker specification);
here it is passed in explicitly so the arithmetic can be unit-tested.
"""
from __future__ import annotations

import math

EPS = 1e-9


def floor_step(v: float, step: float) -> float:
    return round(math.floor(v / step + EPS) * step, 8)


def compute_volume(risk_money: float, loss_per_lot: float, commission_per_lot: float,
                   vmin: float, vstep: float, vmax: float, vlimit: float = 0.0) -> tuple[float, str]:
    """Largest volume whose loss at SL (+ commission) does not exceed `risk_money`.

    Returns (volume, reason). volume == 0 means the trade must be refused.
    """
    if risk_money <= 0:
        return 0.0, "REJECT_RISK_MONEY"
    per_lot = abs(loss_per_lot) + max(commission_per_lot, 0.0)
    if per_lot <= 0 or not math.isfinite(per_lot):
        return 0.0, "REJECT_LOSS_PER_LOT"
    raw = risk_money / per_lot
    vol = floor_step(raw, vstep)
    cap = vmax if vlimit <= 0 else min(vmax, vlimit)
    if vol > cap:
        vol = floor_step(cap, vstep)
    if vol < vmin - EPS:
        return 0.0, "REJECT_MIN_LOT_EXCEEDS_RISK"
    return vol, "OK"


def partial_close_volume(initial_volume: float, current_volume: float, fraction: float,
                         vmin: float, vstep: float, fallback: str = "CLOSE_ALL") -> tuple[float, str]:
    """Volume to close at the partial target (fraction of the INITIAL volume).

    Never returns an invalid volume: the result is 0 (nothing), `current_volume` (everything)
    or a multiple of `vstep` >= vmin leaving a remainder >= vmin.
    """
    target = floor_step(initial_volume * fraction, vstep)
    target = min(target, current_volume)
    remainder = round(current_volume - target, 8)
    if target >= vmin - EPS and remainder >= vmin - EPS:
        return target, "PARTIAL"
    if fallback == "CLOSE_ALL":
        return current_volume, "FALLBACK_CLOSE_ALL"
    return 0.0, "FALLBACK_KEEP_ALL"


def r_multiple(direction: int, entry: float, sl_initial: float, price: float) -> float:
    """Current profit in R using the INITIAL risk (never the post-BE stop)."""
    risk = abs(entry - sl_initial)
    if risk <= 0:
        return 0.0
    return direction * (price - entry) / risk


def break_even_sl(direction: int, entry_fill: float, current_sl: float, offset: float,
                  tick: float) -> float | None:
    """New SL for break-even, or None if it would not tighten the stop (never widen risk)."""
    new = entry_fill + direction * offset
    new = round(math.floor(new / tick + 0.5) * tick, 10)
    if direction > 0 and new > current_sl + EPS:
        return new
    if direction < 0 and new < current_sl - EPS:
        return new
    return None


def tighter_sl(direction: int, current_sl: float, candidate: float) -> bool:
    """True if `candidate` reduces risk compared to `current_sl` (trailing rule PM-3)."""
    return candidate > current_sl + EPS if direction > 0 else candidate < current_sl - EPS
