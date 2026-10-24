//+------------------------------------------------------------------+
//| SensitorAI.mq5 - XAU/USD structure/OTE/OB/FVG Expert Advisor      |
//| Deterministic v0 (no AI in the execution path).                   |
//| Spec: Docs/SPECIFICATION.md   State machine: Docs/STATE_MACHINE.md|
//| WARNING: no profitability is assumed. Demo/test use only until    |
//| the validation checklist (Docs/LIVE_CHECKLIST.md) is complete.    |
//+------------------------------------------------------------------+
#property copyright "Sensitor AI"
#property version   "0.200"
#property description "Sensitor AI - automated structure/OTE/OB/FVG strategy (validation build)"
#property strict

#include <SensitorAI/Config.mqh>
#include <SensitorAI/MarketData.mqh>
#include <SensitorAI/SignalEngine.mqh>
#include <SensitorAI/RiskManager.mqh>
#include <SensitorAI/ExecutionManager.mqh>
#include <SensitorAI/PositionManager.mqh>
#include <SensitorAI/TradeLogger.mqh>
#include <SensitorAI/StateStore.mqh>
#include <SensitorAI/NewsFilter.mqh>
#include <SensitorAI/Dashboard.mqh>

//==================================================================== inputs
input group "=== General ==="
input string               InpSymbol             = "";              // Symbol ("" = chart symbol)
input long                 InpMagic              = 20250101;        // Magic number
input bool                 InpDryRun             = false;           // Dry-run: compute & log, never send orders
input bool                 InpClearErrorSafe     = false;           // Clear a persisted ERROR_SAFE state at start

input group "=== Timeframes ==="
input ENUM_TIMEFRAMES      InpEntryTF            = PERIOD_M15;      // Entry TF (M5 or M15) [U] value [C]
input ENUM_TIMEFRAMES      InpRsiTF              = PERIOD_CURRENT;  // RSI TF (CURRENT = entry TF) [C]

input group "=== Structure ==="
input int                  InpSwingLeftHTF       = 3;               // Swing left bars H1/H4 [C]
input int                  InpSwingRightHTF      = 3;               // Swing right bars H1/H4 [C]
input int                  InpSwingLeftEntry     = 2;               // Swing left bars entry TF [C]
input int                  InpSwingRightEntry    = 2;               // Swing right bars entry TF [C]
input double               InpBosBufferATR       = 0.0;             // BOS close buffer (x ATR) [H]
input ENUM_SAI_BIAS_FLIP   InpBiasFlip           = FLIP_ON_CHOCH;   // Trend after CHoCH [C]
input ENUM_SAI_BIAS_MODE   InpBiasMode           = BIAS_REQUIRE_BOTH; // H4/H1 combination [H]
input ENUM_SAI_SWEEP_ACTION InpCautionSweep      = SWEEP_BLOCK;     // Opposing HTF sweep action [C]
input bool                 InpRequireCompatSweep = false;           // Require a compatible sweep [C]
input int                  InpSweepLookback      = 10;              // Sweep lookback (bars of its TF) [H]

input group "=== Impulse / OTE / Zones ==="
input ENUM_SAI_IMPULSE     InpImpulseAnchor      = ANCHOR_SWING_CONFIRM; // Impulse end definition [C]
input double               InpMinImpulseATR      = 0.0;             // Min impulse size (x ATR, 0=off) [H]
input double               InpOteMin             = 0.62;            // OTE min retracement [U]
input double               InpOteMax             = 0.79;            // OTE max retracement [U]
input double               InpFvgMinATR          = 0.0;             // Min FVG size (x ATR) [H]
input int                  InpObMaxDistBars      = 0;               // OB bars before the FVG (0 = OB creates the FVG) [U]
input int                  InpObPreOriginBars    = 2;               // OB bars allowed before origin [C]
input ENUM_SAI_OB_ZONE     InpObZoneMode         = OB_ZONE_WICK;    // OB zone: wick or body [H]
input double               InpEntryDepth         = 0.5;             // Entry depth in OB/OTE zone (0=proximal,1=distal) [C]
input bool                 InpRejectIfTouched    = true;            // Skip if entry touched before placement [H]

input group "=== Stop loss ==="
input ENUM_SAI_SL_ANCHOR   InpSlAnchor           = SL_STRUCTURAL;   // SL anchor [H]
input double               InpSlBufferPoints     = 0.0;             // SL buffer (points) [C]
input double               InpSlBufferATR        = 0.10;            // SL buffer (x ATR) [C]
input bool                 InpSlAddSpreadSells   = true;            // Add spread to sell SL [H]
input double               InpMinSlSpreadMult    = 3.0;             // Min SL distance (x spread) [H]
input double               InpMaxSlATR           = 0.0;             // Max SL distance (x ATR, 0=off) [H]

input group "=== RSI filter (exclusion only) ==="
input ENUM_SAI_RSI_MODE    InpRsiMode            = RSI_AT_SETUP;    // RSI check moment [C]
input int                  InpRsiPeriod          = 14;              // RSI period [U]
input double               InpRsiOverbought      = 70.0;            // Buy refused if RSI >= [U]
input double               InpRsiOversold        = 30.0;            // Sell refused if RSI <= [U]
input int                  InpRsiWindow          = 5;               // Closed bars checked [U]

input group "=== Invalidation ==="
input ENUM_SAI_CONTINUATION InpContinuation      = CONT_CLOSE;      // Continuation invalidation [H]
input bool                 InpCancelOnBiasChange = true;            // Cancel pending if bias changes [H]

input group "=== Position management ==="
input double               InpBeTriggerR         = 1.0;             // Break-even trigger (R) [U]
input double               InpBeOffsetPoints     = 0.0;             // Break-even offset (points) [H]
input double               InpPartialTriggerR    = 3.0;             // Partial trigger (R) [U]
input double               InpPartialFraction    = 0.5;             // Partial fraction of initial volume [U]
input ENUM_SAI_PARTIAL_FB  InpPartialFallback    = PARTIAL_FB_CLOSE_ALL; // If volume cannot be split [C]
input ENUM_SAI_RUNNER      InpRunnerMethod       = RUNNER_FIXED_R;  // Runner method A/B/C/D [U]
input double               InpRunnerTargetR      = 5.0;             // Method C target (R) [U]
input ENUM_TIMEFRAMES      InpLiquidityTF        = PERIOD_H1;       // Method B liquidity TF [C]
input double               InpLiquidityFallbackR = 6.0;             // Method B fallback (R) [C]
input double               InpTrailingBufferATR  = 0.10;            // Method D buffer (x ATR) [H]
input bool                 InpCancelRemainder    = true;            // Cancel remainder of a partially filled order [H]

input group "=== Risk & safety ==="
input ENUM_SAI_RISK_BASE   InpRiskBase           = RISK_BASE_MIN_BAL_EQ; // Capital reference [C]
input double               InpFixedCapital       = 10000.0;         // Capital if FIXED
input double               InpRiskPct            = 1.0;             // Risk per trade (%) [U]
input int                  InpMaxPositions       = 2;               // Max positions + pending orders [H]
input double               InpMaxTotalRiskPct    = 2.0;             // Max total open risk (%) [H]
input double               InpDailyLossLimitPct  = 3.0;             // Daily loss limit (%) [H]
input int                  InpMaxSpreadPoints    = 0;               // Max spread at placement (points, 0=off) [C]
input double               InpCommissionPerLot   = 0.0;             // Estimated round-turn commission per lot
input int                  InpDeviationPoints    = 30;              // Max deviation for market closes (points)
input int                  InpMaxConsecErrors    = 5;               // Consecutive trade errors before ERROR_SAFE

input group "=== News filter (not testable in the Strategy Tester) ==="
input bool                 InpNewsFilter         = false;           // Enable high-impact news blackout
input int                  InpNewsBeforeMin      = 30;              // Minutes before event
input int                  InpNewsAfterMin       = 30;              // Minutes after event
input string               InpNewsCurrencies     = "USD";           // Currencies (comma separated)

input group "=== Warm-up / logging / display ==="
input int                  InpWarmupEntryBars    = 3000;            // Entry TF bars replayed at start
input int                  InpWarmupH1Bars       = 2000;            // H1 bars loaded at start
input int                  InpWarmupH4Bars       = 800;             // H4 bars loaded at start
input bool                 InpLogEnabled         = true;            // CSV journals (Common\Files\SensitorAI)
input bool                 InpLogDecisions       = true;            // Log every engine decision
input bool                 InpVerbose            = false;           // Echo journal lines in the Experts tab
input bool                 InpDashboard          = true;            // Chart panel (informative only)
input bool                 InpDrawZones          = true;            // Draw OTE/OB/FVG/entry/SL objects

//==================================================================== state
struct STrack
  {
   int               setup_idx;
   string            id;
   ENUM_SAI_STATE    state;
   ulong             order;
   int               retries;
  };

CMarketData       g_md;
CSignalEngine     g_eng;
CRiskManager      g_risk;
CExecutionManager g_ex;
CPositionManager  g_pm;
CTradeLogger      g_log;
CStateStore       g_store;
CNewsFilter       g_news;
CDashboard        g_dash;
SConfig           g_cfg;
STrack            g_tracks[];
datetime          g_last_bar=0;
int               g_logged_decisions=0;
bool              g_error_safe=false;
string            g_error_reason="";
bool              g_day_blocked=false;
datetime          g_day_blocked_on=0;
int               g_data_failures=0;
datetime          g_last_heartbeat=0;
double            g_equity_peak=0;
string            g_tag="";

//==================================================================== config
SConfig BuildConfig()
  {
   SConfig c=ConfigDefaults();
   c.entry_tf=InpEntryTF; c.rsi_tf=InpRsiTF;
   c.swing_left_htf=InpSwingLeftHTF; c.swing_right_htf=InpSwingRightHTF;
   c.swing_left_entry=InpSwingLeftEntry; c.swing_right_entry=InpSwingRightEntry;
   c.bos_buffer_atr=InpBosBufferATR; c.bias_flip_mode=InpBiasFlip; c.bias_mode=InpBiasMode;
   c.caution_sweep_action=InpCautionSweep; c.require_compatible_sweep=InpRequireCompatSweep; c.sweep_lookback_bars=InpSweepLookback;
   c.impulse_anchor=InpImpulseAnchor; c.min_impulse_atr=InpMinImpulseATR; c.ote_min=InpOteMin; c.ote_max=InpOteMax;
   c.fvg_min_atr=InpFvgMinATR; c.ob_max_dist_bars=InpObMaxDistBars; c.ob_pre_origin_bars=InpObPreOriginBars;
   c.ob_zone_mode=InpObZoneMode; c.entry_depth=InpEntryDepth; c.reject_if_touched_before_placement=InpRejectIfTouched;
   c.sl_anchor=InpSlAnchor; c.sl_buffer_points=InpSlBufferPoints; c.sl_buffer_atr=InpSlBufferATR;
   c.sl_add_spread_for_sells=InpSlAddSpreadSells; c.min_sl_spread_mult=InpMinSlSpreadMult; c.max_sl_atr=InpMaxSlATR;
   c.rsi_mode=InpRsiMode; c.rsi_period=InpRsiPeriod; c.rsi_overbought=InpRsiOverbought; c.rsi_oversold=InpRsiOversold;
   c.rsi_window=InpRsiWindow; c.continuation_invalidation=InpContinuation; c.cancel_on_bias_change=InpCancelOnBiasChange;
   c.be_trigger_r=InpBeTriggerR; c.be_offset_points=InpBeOffsetPoints; c.partial_trigger_r=InpPartialTriggerR;
   c.partial_fraction=InpPartialFraction; c.partial_fallback=InpPartialFallback; c.runner_method=InpRunnerMethod;
   c.runner_target_r=InpRunnerTargetR; c.liquidity_tf=InpLiquidityTF; c.liquidity_fallback_r=InpLiquidityFallbackR;
   c.trailing_buffer_atr=InpTrailingBufferATR; c.risk_base=InpRiskBase; c.fixed_capital=InpFixedCapital;
   c.risk_pct=InpRiskPct; c.max_positions=InpMaxPositions; c.max_total_risk_pct=InpMaxTotalRiskPct;
   c.daily_loss_limit_pct=InpDailyLossLimitPct; c.max_spread_points=InpMaxSpreadPoints; c.commission_per_lot=InpCommissionPerLot;
   return c;
  }

//==================================================================== helpers
int FindTrack(const string id)
  {
   for(int i=0;i<ArraySize(g_tracks);i++) if(g_tracks[i].id==id) return i;
   return -1;
  }

int AddTrack(const int setup_idx)
  {
   int i=FindTrack(g_eng.setups[setup_idx].id);
   if(i>=0) return i;
   i=ArraySize(g_tracks);
   ArrayResize(g_tracks,i+1);
   g_tracks[i].setup_idx=setup_idx; g_tracks[i].id=g_eng.setups[setup_idx].id;
   g_tracks[i].state=ST_SETUP_VALID; g_tracks[i].order=0; g_tracks[i].retries=0;
   return i;
  }

void SetState(const int ti,const ENUM_SAI_STATE st,const double price,const string detail)
  {
   if(g_tracks[ti].state==st) return;
   g_log.Event(g_tracks[ti].id,0,StateName(g_tracks[ti].state),StateName(st),price,detail);
   g_tracks[ti].state=st;
  }

void FlushDecisions()
  {
   int n=ArraySize(g_eng.decisions);
   if(InpLogDecisions)
      for(int i=g_logged_decisions;i<n;i++) g_log.Decision(g_md.symbol,EnumToString(g_cfg.entry_tf),g_eng.decisions[i]);
   g_logged_decisions=n;
  }

void EnterErrorSafe(const string reason)
  {
   if(g_error_safe) return;
   g_error_safe=true; g_error_reason=reason;
   g_store.Set("error_safe",reason);
   g_log.Error("ERROR_SAFE",reason);
   g_log.Event("-",0,"*","ERROR_SAFE",0,reason);
   CancelAllPending("ERROR_SAFE");
  }

void CancelAllPending(const string reason)
  {
   for(int i=0;i<ArraySize(g_tracks);i++)
     {
      if(g_tracks[i].state!=ST_PENDING_ORDER && g_tracks[i].state!=ST_SETUP_VALID) continue;
      if(g_tracks[i].order>0) g_ex.Cancel(g_tracks[i].order,g_tracks[i].id,reason);
      g_eng.ForceEnd(g_tracks[i].setup_idx,"INV_SAFETY_"+reason);
      SetState(i,ST_INVALIDATED,0,reason);
     }
   //--- any other order of ours (e.g. left by a previous instance)
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);
      if(tk>0 && OrderGetInteger(ORDER_MAGIC)==InpMagic && OrderGetString(ORDER_SYMBOL)==g_md.symbol)
         g_ex.Cancel(tk,CExecutionManager::SetupFromComment(OrderGetString(ORDER_COMMENT)),reason);
     }
  }

double InitialTP(const SSetup &s)
  {
   if(g_cfg.runner_method==RUNNER_FIXED_R) return s.entry+s.direction*g_cfg.runner_target_r*s.risk_dist;
   if(g_cfg.runner_method==RUNNER_LIQUIDITY)
     {
      double part=s.entry+s.direction*g_cfg.partial_trigger_r*s.risk_dist;
      if(s.direction*(s.tp_liquidity-part)>0) return s.tp_liquidity;
      return s.entry+s.direction*g_cfg.liquidity_fallback_r*s.risk_dist;
     }
   return 0.0;
  }

//--- try to place the order of a READY setup (mirrors simulator placement rules)
void TryPlace(const int ti)
  {
   int idx=g_tracks[ti].setup_idx;
   if(g_eng.setups[idx].status!=SETUP_STATUS_VALID || g_eng.setups[idx].end_bar>=0) return;
   string id=g_tracks[ti].id;
   if(g_error_safe) { g_eng.ForceEnd(idx,"REJECT_ERROR_SAFE"); SetState(ti,ST_INVALIDATED,0,"ERROR_SAFE"); return; }
   if(g_day_blocked) { g_eng.ForceEnd(idx,"REJECT_DAILY_LOSS_LIMIT"); SetState(ti,ST_INVALIDATED,0,"daily loss limit"); return; }
   string why;
   if(g_news.Blocked(TimeTradeServer(),why)) { g_log.Info("placement deferred (news): "+why); return; }   // retried next bar
   if(!g_md.TradingAllowed()) { g_log.Info("placement deferred: trading not allowed on symbol"); return; }
   if(!g_risk.CanOpenNew())
     {
      if(g_risk.last_reason=="REJECT_SPREAD") { g_log.Info("placement deferred: spread"); return; }   // retried next bar
      g_eng.ForceEnd(idx,g_risk.last_reason);
      SetState(ti,ST_INVALIDATED,0,g_risk.last_reason);
      return;
     }
   if(g_store.Has("sent_"+id) || g_ex.EverSent(id,g_eng.setups[idx].confirm_time))
     {
      SetState(ti,ST_CLOSED,0,"setup already sent once: never re-sent");
      return;
     }
   SSetup s=g_eng.setups[idx];
   double vol=g_risk.VolumeFor(s.direction,s.entry,s.sl);
   if(vol<=0)
     {
      g_eng.ForceEnd(idx,g_risk.last_reason);
      SetState(ti,ST_INVALIDATED,0,g_risk.last_reason);
      return;
     }
   ulong ticket;
   ENUM_SAI_SEND_RESULT r=g_ex.PlaceLimit(id,s.direction,vol,s.entry,s.sl,InitialTP(s),ticket);
   if(r==SEND_OK || r==SEND_UNKNOWN)
     {
      g_tracks[ti].order=ticket;
      g_store.Set("sent_"+id,IntegerToString((long)ticket));
      SetState(ti,ST_PENDING_ORDER,s.entry,StringFormat("vol=%.2f SL=%s TP=%s %s",vol,DoubleToString(s.sl,g_md.spec.digits),
               DoubleToString(InitialTP(s),g_md.spec.digits),r==SEND_UNKNOWN ? "(to be confirmed)" : ""));
      g_dash.DrawSetup(s,g_eng.entry.time[s.extreme_idx],TimeCurrent()+PeriodSeconds(g_cfg.entry_tf)*40);
      return;
     }
   if(g_ex.last_error=="PRICE_THROUGH_ENTRY")
     {
      g_eng.ForceEnd(idx,"MISSED_AT_PLACEMENT");
      SetState(ti,ST_INVALIDATED,s.entry,"price already through the entry: never chase");
      return;
     }
   if(r==SEND_RETRY && ++g_tracks[ti].retries<5) return;   // retried on next tick
   g_eng.ForceEnd(idx,"REJECT_ORDER_FAILED");
   SetState(ti,ST_INVALIDATED,s.entry,"order failed: "+g_ex.last_error);
  }

//--- act on the setups changed by the last engine step
void HandleEngineChanges(const bool live)
  {
   if(!live) return;          // warm-up replay: Reconcile() restores the active setups afterwards
   for(int c=0;c<ArraySize(g_eng.changed);c++)
     {
      int idx=g_eng.changed[c];
      SSetup s=g_eng.setups[idx];
      g_log.Setup(g_md.symbol,EnumToString(g_cfg.entry_tf),s);
      int ti=FindTrack(s.id);
      //--- ended: cancel its order if any
      if(s.end_bar>=0)
        {
         if(ti>=0 && (g_tracks[ti].state==ST_PENDING_ORDER || g_tracks[ti].state==ST_SETUP_VALID))
           {
            bool ok=true;
            if(g_tracks[ti].order>0) ok=g_ex.Cancel(g_tracks[ti].order,s.id,s.end_reason);
            if(ok) SetState(ti,ST_INVALIDATED,0,s.end_reason);
           }
         continue;
        }
      if(s.status!=SETUP_STATUS_VALID) continue;
      if(ti<0) ti=AddTrack(idx);
      if(s.place_bar>=0 && g_tracks[ti].state==ST_SETUP_VALID) TryPlace(ti);
     }
  }

//--- load closed bars of every timeframe up to `upto`; false if data not ready
bool LoadBars(const datetime upto,const bool warmup)
  {
   ENUM_TIMEFRAMES tfs[3]={PERIOD_H4,PERIOD_H1,PERIOD_CURRENT};
   tfs[2]=g_cfg.entry_tf;
   if(!warmup)
     {
      for(int i=0;i<3;i++) if(!g_md.SeriesReady(tfs[i],upto)) return false;
      if(!g_eng.rsi_on_entry && !g_md.SeriesReady(g_cfg.rsi_tf,upto)) return false;
     }
   if(g_md.AppendClosed(g_eng.h4,PERIOD_H4,upto,InpWarmupH4Bars)<0) return false;
   if(g_md.AppendClosed(g_eng.h1,PERIOD_H1,upto,InpWarmupH1Bars)<0) return false;
   if(!g_eng.rsi_on_entry && g_md.AppendClosed(g_eng.rsi_bars,g_cfg.rsi_tf,upto,InpWarmupEntryBars)<0) return false;
   if(g_md.AppendClosed(g_eng.entry,g_cfg.entry_tf,upto,InpWarmupEntryBars)<0) return false;
   return true;
  }

//--- process every newly appended entry bar (normally exactly one)
void ProcessNewBars(const bool live)
  {
   while(g_eng.ProcessedEntryBars()<g_eng.entry.Size())
     {
      int k=g_eng.ProcessedEntryBars();
      //--- anti look-ahead guard: a bar may only be processed once it is closed
      if(live && g_eng.entry.CloseTime(k)>TimeCurrent()+1)
        {
         EnterErrorSafe("look-ahead guard: bar "+TimeToString(g_eng.entry.time[k])+" not closed");
         return;
        }
      //--- live: spread of the current tick. Replay: historical spread of the next bar (what the
      //--- EA saw when that bar opened; same convention as the Python reference). Using the current
      //--- spread for old bars could reject setups that were valid and orphan their orders.
      double sp=g_md.Spread();
      if(!live && k+1<g_eng.entry.Size() && g_eng.entry.spread[k+1]>0) sp=g_eng.entry.spread[k+1];
      g_eng.ProcessEntryBar(k,sp);
      HandleEngineChanges(live);
      if(live)
        {
         FlushDecisions();
         g_pm.OnEntryBar(g_eng.trk_e.new_events,g_eng.entry,g_md.Spread());
        }
     }
   if(!live) g_logged_decisions=ArraySize(g_eng.decisions);
  }

//--- restore pending-order tracking after (re)start
void Reconcile()
  {
   g_pm.Sync();
   for(int s=0;s<2;s++)
     {
      int d=(s==0) ? SAI_BULL : SAI_BEAR;
      int idx=g_eng.ActiveIndex(d);
      if(idx<0) continue;
      int ti=AddTrack(idx);
      ulong tk=g_ex.FindOrder(g_tracks[ti].id);
      if(tk>0) { g_tracks[ti].order=tk; SetState(ti,ST_PENDING_ORDER,g_eng.setups[idx].entry,"restored from terminal"); continue; }
      if(g_store.Has("sent_"+g_tracks[ti].id) || g_ex.EverSent(g_tracks[ti].id,g_eng.setups[idx].confirm_time))
        {
         SetState(ti,ST_CLOSED,0,"order already sent before restart (filled or removed)");
         continue;
        }
      if(g_eng.setups[idx].place_bar>=0) TryPlace(ti);
     }
   //--- orphan orders (not matching an active setup of the engine) are cancelled
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);
      if(tk==0 || OrderGetInteger(ORDER_MAGIC)!=InpMagic || OrderGetString(ORDER_SYMBOL)!=g_md.symbol) continue;
      string id=CExecutionManager::SetupFromComment(OrderGetString(ORDER_COMMENT));
      int ti=FindTrack(id);
      if(ti<0 || g_tracks[ti].state!=ST_PENDING_ORDER)
         g_ex.Cancel(tk,id,"orphan order: setup not active after restart");
     }
  }

void UpdateDashboard()
  {
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   g_equity_peak=MathMax(g_equity_peak,eq);
   double dd=(g_equity_peak>0) ? (g_equity_peak-eq)/g_equity_peak*100.0 : 0;
   string active="";
   for(int i=0;i<ArraySize(g_tracks);i++)
      if(g_tracks[i].state==ST_PENDING_ORDER || g_tracks[i].state==ST_SETUP_VALID)
        {
         SSetup s=g_eng.setups[g_tracks[i].setup_idx];
         active+=StringFormat("\n  %s %s %s E=%s SL=%s",s.id,DirName(s.direction),StateName(g_tracks[i].state),
                              DoubleToString(s.entry,g_md.spec.digits),DoubleToString(s.sl,g_md.spec.digits));
        }
   string positions="";
   for(int i=0;i<ArraySize(g_pm.pos);i++)
      positions+=StringFormat("\n  #%I64u %s %s R=%s",g_pm.pos[i].ticket,DirName(g_pm.pos[i].dir),StateName(g_pm.pos[i].state),
                              DoubleToString(g_pm.pos[i].R,g_md.spec.digits));
   string txt=StringFormat("SENSITOR AI v%s %s%s\nState: %s%s\nSymbol: %s  TF: %s  Runner: %s\nBias H4=%d H1=%d => %s\n"
                           "Open risk: %.2f%%  Day P&L: %.2f  DD from peak: %.2f%%\nConnected: %s  News: %s\nSetups:%s\nPositions:%s",
                           SAI_VERSION,InpDryRun ? "[DRY-RUN] " : "",MQLInfoInteger(MQL_TESTER) ? "[TESTER]" : "",
                           g_error_safe ? "ERROR_SAFE ("+g_error_reason+")" : (g_day_blocked ? "SUSPENDED (daily loss limit)" : "RUNNING"),
                           "",g_md.symbol,EnumToString(g_cfg.entry_tf),RunnerName(g_cfg.runner_method),
                           g_eng.last_h4,g_eng.last_h1,DirName(g_eng.last_bias),g_risk.OpenRiskPct(),g_risk.DayPnL(),dd,
                           TerminalInfoInteger(TERMINAL_CONNECTED) ? "yes" : "NO",g_news.status,
                           active=="" ? " none" : active,positions=="" ? " none" : positions);
   g_dash.Show(txt);
  }

void Heartbeat()
  {
   if(MQLInfoInteger(MQL_TESTER)) return;
   datetime now=TimeLocal();
   if(now-g_last_heartbeat<60) return;
   g_last_heartbeat=now;
   int h=FileOpen("SensitorAI\\"+g_tag+"_heartbeat.txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h,StringFormat("%s,%s,%s,%d,%d\n",TimeToString(TimeLocal(),TIME_DATE|TIME_SECONDS),
                                  TimeToString(TimeTradeServer(),TIME_DATE|TIME_SECONDS),
                                  g_error_safe ? "ERROR_SAFE" : "OK",(int)TerminalInfoInteger(TERMINAL_CONNECTED),ArraySize(g_pm.pos)));
   FileClose(h);
  }

//==================================================================== events
int OnInit()
  {
   g_cfg=BuildConfig();
   string err=ConfigValidate(g_cfg);
   if(err!="") { Print("Sensitor AI: invalid configuration: ",err); return INIT_PARAMETERS_INCORRECT; }
   string sym=(InpSymbol=="") ? _Symbol : InpSymbol;
   if(!g_md.Init(sym)) { Print("Sensitor AI: symbol error: ",g_md.last_error); return INIT_FAILED; }
   g_tag=sym+"_"+IntegerToString(InpMagic);
   g_log.Init(g_tag,InpLogEnabled,InpVerbose);
   g_store.Init(g_tag);
   g_log.Info("Sensitor AI "+SAI_VERSION+" "+g_md.SpecSummary());
   g_log.Event("-",0,"INIT","INIT",0,g_md.SpecSummary());
   if(g_md.spec.tick_size<=0) return INIT_FAILED;
   g_eng.Init(g_cfg,g_md.spec.tick_size);
   g_risk.Init(g_cfg,GetPointer(g_md),InpMagic);
   g_ex.Init(GetPointer(g_md),GetPointer(g_log),InpMagic,InpDeviationPoints,InpDryRun);
   g_pm.Init(g_cfg,GetPointer(g_md),GetPointer(g_ex),GetPointer(g_risk),GetPointer(g_log),GetPointer(g_store),InpMagic);
   g_news.Init(InpNewsFilter,InpNewsBeforeMin,InpNewsAfterMin,InpNewsCurrencies);
   g_dash.Init(InpDashboard,InpDrawZones,InpMagic);
   if(InpClearErrorSafe) g_store.Remove("error_safe");
   if(g_store.Has("error_safe")) { g_error_safe=true; g_error_reason="persisted: "+g_store.Get("error_safe"); }
   if(!InpDryRun && !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && !MQLInfoInteger(MQL_TESTER))
      g_log.Info("WARNING: algo trading is disabled in the terminal");
   //--- deterministic warm-up: replay recent closed bars through the engine
   datetime now=TimeCurrent();
   g_last_bar=iTime(g_md.symbol,g_cfg.entry_tf,0);
   if(!LoadBars(g_last_bar,true)) { g_log.Error("OnInit","warm-up data unavailable: "+g_md.last_error); return INIT_FAILED; }
   int gaps=CMarketData::CountGaps(g_eng.entry,0,6);
   if(gaps>0) g_log.Info(StringFormat("data quality: %d abnormal gaps in the entry-TF warm-up window",gaps));
   ProcessNewBars(false);
   g_log.Info(StringFormat("warm-up: %d entry bars, %d H1, %d H4, %d setups seen, bias=%d",g_eng.entry.Size(),
                           g_eng.h1.Size(),g_eng.h4.Size(),ArraySize(g_eng.setups),g_eng.last_bias));
   Reconcile();
   g_equity_peak=AccountInfoDouble(ACCOUNT_EQUITY);
   EventSetTimer(5);
   UpdateDashboard();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   g_log.Event("-",0,"RUN","DEINIT",0,"reason="+IntegerToString(reason));
   g_dash.Clear();
  }

void OnTick()
  {
   //--- protection first: management of open positions never waits for the signal engine
   g_pm.OnTick();
   datetime cur=iTime(g_md.symbol,g_cfg.entry_tf,0);
   if(cur!=0 && cur!=g_last_bar)
     {
      if(!LoadBars(cur,false))
        {
         if(++g_data_failures%20==1) g_log.Info("data not ready: "+g_md.last_error);
         if(g_data_failures>600) EnterErrorSafe("market data unavailable for too long: "+g_md.last_error);
         return;   // retried on the next tick; the bar is not lost
        }
      g_data_failures=0;
      g_last_bar=cur;
      ProcessNewBars(true);
      //--- deferred placements (spread / news) are retried once per new bar
      for(int i=0;i<ArraySize(g_tracks);i++)
         if(g_tracks[i].state==ST_SETUP_VALID && g_eng.setups[g_tracks[i].setup_idx].place_bar>=0) TryPlace(i);
     }
   //--- transient send failures are retried on the next ticks
   for(int i=0;i<ArraySize(g_tracks);i++)
      if(g_tracks[i].state==ST_SETUP_VALID && g_tracks[i].retries>0) TryPlace(i);
  }

void OnTimer()
  {
   g_risk.RollDay();
   datetime today=CMarketData::BarStart(TimeTradeServer(),PERIOD_D1);
   if(g_day_blocked && today!=g_day_blocked_on) { g_day_blocked=false; g_log.Event("-",0,"SUSPENDED","RUNNING",0,"new server day"); }
   if(!g_day_blocked && g_risk.DailyLimitHit())
     {
      g_day_blocked=true; g_day_blocked_on=today;
      g_log.Event("-",0,"RUNNING","SUSPENDED",0,"daily loss limit reached");
      CancelAllPending("DAILY_LOSS_LIMIT");
     }
   g_pm.Sync();
   if(g_pm.critical) EnterErrorSafe(g_pm.critical_reason);
   if(g_ex.consecutive_errors>=InpMaxConsecErrors) EnterErrorSafe(StringFormat("%d consecutive trade errors (last %u %s)",g_ex.consecutive_errors,g_ex.last_retcode,g_ex.last_error));
   //--- pending orders that disappeared: filled (position appears) or removed/expired
   for(int i=0;i<ArraySize(g_tracks);i++)
     {
      if(g_tracks[i].state!=ST_PENDING_ORDER || g_tracks[i].order==0 || InpDryRun) continue;
      if(OrderSelect(g_tracks[i].order)) continue;
      if(HistoryOrderSelect(g_tracks[i].order) || (HistorySelect(TimeCurrent()-30*86400,TimeCurrent()+86400) && HistoryOrderSelect(g_tracks[i].order)))
        {
         ENUM_ORDER_STATE st=(ENUM_ORDER_STATE)HistoryOrderGetInteger(g_tracks[i].order,ORDER_STATE);
         if(st==ORDER_STATE_FILLED || st==ORDER_STATE_PARTIAL) SetState(i,ST_POSITION_OPEN,HistoryOrderGetDouble(g_tracks[i].order,ORDER_PRICE_OPEN),"fill confirmed by history");
         else if(st==ORDER_STATE_EXPIRED && g_eng.setups[g_tracks[i].setup_idx].end_bar<0)
           {
            //--- DAY-expiry brokers: the setup is still structurally valid, place it again
            g_store.Remove("sent_"+g_tracks[i].id);
            g_tracks[i].order=0; g_tracks[i].state=ST_SETUP_VALID;
            g_log.Event(g_tracks[i].id,0,"PENDING_ORDER","SETUP_VALID",0,"order expired by broker; re-placing");
            TryPlace(i);
           }
         else SetState(i,ST_INVALIDATED,0,"order removed outside the EA: "+EnumToString(st));
        }
     }
   Heartbeat();
   UpdateDashboard();
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
  {
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=g_md.symbol) return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(entry==DEAL_ENTRY_IN)
     {
      ulong order=(ulong)HistoryDealGetInteger(trans.deal,DEAL_ORDER);
      ulong position=(ulong)HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID);
      double price=HistoryDealGetDouble(trans.deal,DEAL_PRICE);
      int ti=-1;
      for(int i=0;i<ArraySize(g_tracks);i++) if(g_tracks[i].order==order) ti=i;
      if(ti<0) ti=FindTrack(CExecutionManager::SetupFromComment(HistoryDealGetString(trans.deal,DEAL_COMMENT)));
      if(ti>=0)
        {
         SSetup s=g_eng.setups[g_tracks[ti].setup_idx];
         g_pm.OnFill(position,s.id,s.entry,s.sl,s.tp_liquidity,g_md.Spread());
         SetState(ti,ST_POSITION_OPEN,price,StringFormat("filled %.2f lots slippage=%s",HistoryDealGetDouble(trans.deal,DEAL_VOLUME),
                  DoubleToString(s.direction*(s.entry-price),g_md.spec.digits)));
         //--- partial fill: cancel the remainder (managed volume = filled volume)
         if(InpCancelRemainder && OrderSelect(order) && OrderGetDouble(ORDER_VOLUME_CURRENT)>0)
            g_ex.Cancel(order,s.id,"remainder of a partially filled order");
        }
      else g_pm.Sync();
     }
   else g_pm.Sync();
  }
//+------------------------------------------------------------------+
