"""Strategy configuration shared by the reference engine and the research backtester.

Every field mirrors an `input` of the MQL5 Expert Advisor (MQL5/Include/SensitorAI/Config.mqh).
Tags in comments: [U] user rule, [H] development hypothesis, [C] value to be confirmed.
See Docs/SPECIFICATION.md and Docs/ASSUMPTIONS.md.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

# Enumerations are plain strings to keep configs JSON-serialisable and readable in reports.
BIAS_FLIP_MODES = ("FLIP_ON_CHOCH", "NEUTRAL_ON_CHOCH")
BIAS_MODES = ("REQUIRE_BOTH", "H4_LEADS")
IMPULSE_ANCHORS = ("SWING_CONFIRM", "BOS_BAR")
OB_ZONE_MODES = ("WICK", "BODY")
SL_ANCHORS = ("STRUCTURAL", "OB_DISTAL", "IMPULSE_ORIGIN")
RSI_MODES = ("OFF", "AT_SETUP", "GATE_PLACEMENT", "CONTINUOUS")
CONTINUATION_MODES = ("CLOSE", "WICK")
SWEEP_ACTIONS = ("LOG_ONLY", "BLOCK")
RUNNER_METHODS = ("STRUCTURE", "LIQUIDITY", "FIXED_R", "TRAILING")
PARTIAL_FALLBACKS = ("CLOSE_ALL", "KEEP_ALL")


@dataclass(frozen=True)
class StrategyConfig:
    # --- timeframes (minutes) -------------------------------------------------
    entry_tf: int = 15            # [U] M5 or M15 ; default M15 [C]
    bias_tfs: tuple = (240, 60)   # [U] H4, H1
    rsi_tf: int = 0               # [C] 0 = same as entry_tf

    # --- swings / structure ---------------------------------------------------
    swing_left_htf: int = 3       # [C]
    swing_right_htf: int = 3      # [C]
    swing_left_entry: int = 2     # [C]
    swing_right_entry: int = 2    # [C]
    bos_buffer_atr: float = 0.0   # [H] 0 => plain close beyond the level
    bias_flip_mode: str = "FLIP_ON_CHOCH"   # [C]
    bias_mode: str = "REQUIRE_BOTH"         # [H]
    liquidity_max_levels: int = 30          # [H]

    # --- sweeps -----------------------------------------------------------------
    caution_sweep_action: str = "BLOCK"     # [C]
    require_compatible_sweep: bool = False  # [C]
    sweep_lookback_bars: int = 10           # [H] in bars of the TF where the sweep happened

    # --- impulse / OTE / zones --------------------------------------------------
    impulse_anchor: str = "SWING_CONFIRM"   # [C]
    min_impulse_atr: float = 0.0            # [H] 0 = disabled
    ote_min: float = 0.62                   # [U]
    ote_max: float = 0.79                   # [U]
    fvg_min_atr: float = 0.0                # [H]
    ob_max_dist_bars: int = 0               # [U] the OB is the 1st candle of the FVG (it creates the gap)
    ob_pre_origin_bars: int = 2             # [C]
    ob_zone_mode: str = "WICK"              # [H]
    entry_depth: float = 0.5                # [U configurable] value [C]
    reject_if_touched_before_placement: bool = True  # [H]

    # --- stop loss --------------------------------------------------------------
    sl_anchor: str = "STRUCTURAL"           # [H]
    sl_buffer_points: float = 0.0           # [C] in broker points
    sl_buffer_atr: float = 0.10             # [C]
    sl_add_spread_for_sells: bool = True    # [H]
    min_sl_spread_mult: float = 3.0         # [H]
    max_sl_atr: float = 0.0                 # [H] 0 = disabled

    # --- RSI filter -------------------------------------------------------------
    rsi_mode: str = "AT_SETUP"              # [U] modes to compare ; default [C]
    rsi_period: int = 14                    # [U]
    rsi_overbought: float = 70.0            # [U]
    rsi_oversold: float = 30.0              # [U]
    rsi_window: int = 5                     # [U]

    # --- invalidation -----------------------------------------------------------
    continuation_invalidation: str = "CLOSE"  # [H]
    cancel_on_bias_change: bool = True        # [H]

    # --- position management ----------------------------------------------------
    be_trigger_r: float = 1.0               # [U]
    be_offset_points: float = 0.0           # [H]
    partial_trigger_r: float = 3.0          # [U]
    partial_fraction: float = 0.5           # [U]
    partial_fallback: str = "CLOSE_ALL"     # [C]
    runner_method: str = "FIXED_R"          # [U] four methods compared
    runner_target_r: float = 5.0            # [U] 5R and 6R compared
    liquidity_tf: int = 60                  # [C]
    liquidity_fallback_r: float = 6.0       # [C]
    trailing_buffer_atr: float = 0.10       # [H]

    # --- risk -------------------------------------------------------------------
    risk_pct: float = 1.0                   # [U]
    max_positions: int = 2                  # [H]
    max_total_risk_pct: float = 2.0         # [H]
    daily_loss_limit_pct: float = 3.0       # [H]
    max_spread_price: float = 0.0           # [C] 0 = no spread filter (set from data study)

    def replace(self, **kw) -> "StrategyConfig":
        return dataclasses.replace(self, **kw)

    def validate(self) -> None:
        assert self.entry_tf in (5, 15), "entry_tf must be M5 or M15"
        assert self.bias_flip_mode in BIAS_FLIP_MODES
        assert self.bias_mode in BIAS_MODES
        assert self.impulse_anchor in IMPULSE_ANCHORS
        assert self.ob_zone_mode in OB_ZONE_MODES
        assert self.sl_anchor in SL_ANCHORS
        assert self.rsi_mode in RSI_MODES
        assert self.continuation_invalidation in CONTINUATION_MODES
        assert self.caution_sweep_action in SWEEP_ACTIONS
        assert self.runner_method in RUNNER_METHODS
        assert self.partial_fallback in PARTIAL_FALLBACKS
        assert 0.0 <= self.ote_min < self.ote_max <= 1.0
        assert 0.0 <= self.entry_depth <= 1.0
        assert 0.0 < self.partial_fraction < 1.0
        assert self.be_trigger_r > 0 and self.partial_trigger_r > self.be_trigger_r

    @property
    def rsi_timeframe(self) -> int:
        return self.rsi_tf or self.entry_tf

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class CostModel:
    """Execution cost assumptions for the research simulator (all in USD, account = USD)."""
    contract_size: float = 100.0            # oz per lot (verified per broker in the EA via SYMBOL_TRADE_CONTRACT_SIZE)
    commission_per_lot_rt: float = 7.0      # round turn, USD
    stop_slippage: float = 0.10             # price units, adverse, on SL / market exits
    partial_slippage: float = 0.05          # price units, adverse, on local market partial close
    swap_long_per_lot: float = -40.0        # USD per lot per night (broker dependent)
    swap_short_per_lot: float = -15.0       # USD per lot per night (broker dependent)
    triple_swap_weekday: int = 2            # 0=Mon ... 2=Wed
    extra_spread: float = 0.0               # added to the historical ask (stress tests)

    def replace(self, **kw) -> "CostModel":
        return dataclasses.replace(self, **kw)

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class AccountModel:
    initial_balance: float = 10_000.0
    volume_min: float = 0.01
    volume_step: float = 0.01
    volume_max: float = 100.0
    server_utc_offset_winter: int = 2       # hours, NY-close convention
    server_utc_offset_summer: int = 3

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)
