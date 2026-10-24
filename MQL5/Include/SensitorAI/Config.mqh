//+------------------------------------------------------------------+
//| Config.mqh - strategy configuration (mirrors config.py)          |
//| Tags: [U] user rule, [H] hypothesis, [C] value to confirm         |
//| The EA fills SConfig from its inputs (Inputs.mqh); test scripts  |
//| build it directly with ConfigDefaults().                          |
//+------------------------------------------------------------------+
#ifndef SENSITOR_CONFIG_MQH
#define SENSITOR_CONFIG_MQH

#include "Types.mqh"

struct SConfig
  {
   //--- timeframes
   ENUM_TIMEFRAMES   entry_tf;              // [U] M5/M15, default M15 [C]
   ENUM_TIMEFRAMES   rsi_tf;                // [C] PERIOD_CURRENT = entry TF
   //--- structure
   int               swing_left_htf, swing_right_htf;      // [C] 3/3
   int               swing_left_entry, swing_right_entry;  // [C] 2/2
   double            bos_buffer_atr;        // [H] 0
   ENUM_SAI_BIAS_FLIP bias_flip_mode;       // [C]
   ENUM_SAI_BIAS_MODE bias_mode;            // [H]
   int               liquidity_max_levels;  // [H] 30
   //--- sweeps
   ENUM_SAI_SWEEP_ACTION caution_sweep_action; // [C] BLOCK
   bool              require_compatible_sweep; // [C] false
   int               sweep_lookback_bars;   // [H] 10
   //--- impulse / zones
   ENUM_SAI_IMPULSE  impulse_anchor;        // [C]
   double            min_impulse_atr;       // [H] 0
   double            ote_min, ote_max;      // [U] 0.62 / 0.79
   double            fvg_min_atr;           // [H] 0
   int               ob_max_dist_bars;      // [C] 5
   int               ob_pre_origin_bars;    // [C] 2
   ENUM_SAI_OB_ZONE  ob_zone_mode;          // [H] WICK
   double            entry_depth;           // [C] 0.5
   bool              reject_if_touched_before_placement; // [H] true
   //--- stop loss
   ENUM_SAI_SL_ANCHOR sl_anchor;            // [H]
   double            sl_buffer_points;      // [C] 0
   double            sl_buffer_atr;         // [C] 0.10
   bool              sl_add_spread_for_sells; // [H] true
   double            min_sl_spread_mult;    // [H] 3
   double            max_sl_atr;            // [H] 0 = off
   //--- RSI
   ENUM_SAI_RSI_MODE rsi_mode;              // [C] AT_SETUP
   int               rsi_period;            // [U] 14
   double            rsi_overbought;        // [U] 70
   double            rsi_oversold;          // [U] 30
   int               rsi_window;            // [U] 5
   //--- invalidation
   ENUM_SAI_CONTINUATION continuation_invalidation; // [H] CLOSE
   bool              cancel_on_bias_change; // [H] true
   //--- management
   double            be_trigger_r;          // [U] 1
   double            be_offset_points;      // [H] 0
   double            partial_trigger_r;     // [U] 3
   double            partial_fraction;      // [U] 0.5
   ENUM_SAI_PARTIAL_FB partial_fallback;    // [C] CLOSE_ALL
   ENUM_SAI_RUNNER   runner_method;         // [U] compared
   double            runner_target_r;       // [U] 5 / 6
   ENUM_TIMEFRAMES   liquidity_tf;          // [C] H1
   double            liquidity_fallback_r;  // [C] 6
   double            trailing_buffer_atr;   // [H] 0.10
   //--- risk
   ENUM_SAI_RISK_BASE risk_base;            // [C]
   double            fixed_capital;         // used with RISK_BASE_FIXED
   double            risk_pct;              // [U] 1.0
   int               max_positions;         // [H] 2
   double            max_total_risk_pct;    // [H] 2.0
   double            daily_loss_limit_pct;  // [H] 3.0
   int               max_spread_points;     // [C] 0 = off
   double            commission_per_lot;    // estimated round-turn commission (account currency)
  };

SConfig ConfigDefaults()
  {
   SConfig c;
   c.entry_tf=PERIOD_M15;  c.rsi_tf=PERIOD_CURRENT;
   c.swing_left_htf=3; c.swing_right_htf=3; c.swing_left_entry=2; c.swing_right_entry=2;
   c.bos_buffer_atr=0.0; c.bias_flip_mode=FLIP_ON_CHOCH; c.bias_mode=BIAS_REQUIRE_BOTH;
   c.liquidity_max_levels=30;
   c.caution_sweep_action=SWEEP_BLOCK; c.require_compatible_sweep=false; c.sweep_lookback_bars=10;
   c.impulse_anchor=ANCHOR_SWING_CONFIRM; c.min_impulse_atr=0.0; c.ote_min=0.62; c.ote_max=0.79;
   c.fvg_min_atr=0.0; c.ob_max_dist_bars=5; c.ob_pre_origin_bars=2; c.ob_zone_mode=OB_ZONE_WICK;
   c.entry_depth=0.5; c.reject_if_touched_before_placement=true;
   c.sl_anchor=SL_STRUCTURAL; c.sl_buffer_points=0.0; c.sl_buffer_atr=0.10;
   c.sl_add_spread_for_sells=true; c.min_sl_spread_mult=3.0; c.max_sl_atr=0.0;
   c.rsi_mode=RSI_AT_SETUP; c.rsi_period=14; c.rsi_overbought=70.0; c.rsi_oversold=30.0; c.rsi_window=5;
   c.continuation_invalidation=CONT_CLOSE; c.cancel_on_bias_change=true;
   c.be_trigger_r=1.0; c.be_offset_points=0.0; c.partial_trigger_r=3.0; c.partial_fraction=0.5;
   c.partial_fallback=PARTIAL_FB_CLOSE_ALL; c.runner_method=RUNNER_FIXED_R; c.runner_target_r=5.0;
   c.liquidity_tf=PERIOD_H1; c.liquidity_fallback_r=6.0; c.trailing_buffer_atr=0.10;
   c.risk_base=RISK_BASE_MIN_BAL_EQ; c.fixed_capital=10000.0; c.risk_pct=1.0; c.max_positions=2;
   c.max_total_risk_pct=2.0; c.daily_loss_limit_pct=3.0; c.max_spread_points=0; c.commission_per_lot=0.0;
   return c;
  }

//--- returns "" when valid, otherwise the first problem found
string ConfigValidate(const SConfig &c)
  {
   if(c.entry_tf!=PERIOD_M5 && c.entry_tf!=PERIOD_M15) return "entry_tf must be M5 or M15";
   if(c.swing_left_htf<1 || c.swing_right_htf<1 || c.swing_left_entry<1 || c.swing_right_entry<1)
      return "swing windows must be >= 1";
   if(!(c.ote_min>=0.0 && c.ote_min<c.ote_max && c.ote_max<=1.0)) return "invalid OTE bounds";
   if(c.entry_depth<0.0 || c.entry_depth>1.0) return "entry_depth must be in [0,1]";
   if(c.partial_fraction<=0.0 || c.partial_fraction>=1.0) return "partial_fraction must be in ]0,1[";
   if(c.be_trigger_r<=0.0 || c.partial_trigger_r<=c.be_trigger_r) return "need 0 < BE R < partial R";
   if(c.risk_pct<=0.0 || c.risk_pct>2.0) return "risk_pct must be in ]0,2] (safety cap)";
   if(c.max_total_risk_pct<c.risk_pct) return "max_total_risk_pct < risk_pct";
   if(c.daily_loss_limit_pct<=0.0) return "daily_loss_limit_pct must be > 0";
   if(c.max_positions<1) return "max_positions must be >= 1";
   if(c.rsi_period<2 || c.rsi_window<1) return "invalid RSI settings";
   if(c.liquidity_tf!=PERIOD_H1 && c.liquidity_tf!=PERIOD_H4 && c.liquidity_tf!=c.entry_tf)
      return "liquidity_tf must be H1, H4 or the entry TF";
   if(c.runner_target_r<=c.partial_trigger_r) return "runner_target_r must exceed partial_trigger_r";
   return "";
  }

int TfMinutes(const ENUM_TIMEFRAMES tf) { return PeriodSeconds(tf)/60; }

#endif
