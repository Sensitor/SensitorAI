//+------------------------------------------------------------------+
//| Types.mqh - Sensitor AI shared enums, structs and constants      |
//| Spec: Docs/SPECIFICATION.md                                       |
//+------------------------------------------------------------------+
#ifndef SENSITOR_TYPES_MQH
#define SENSITOR_TYPES_MQH

#define SAI_VERSION        "0.1.0"
#define SAI_COMMENT_PREFIX "SAI "
#define SAI_EPS            1e-9
#define SAI_BULL           1
#define SAI_BEAR          -1
#define SAI_NEUTRAL        0

//--- configuration enums (values mirror Research/sensitor/config.py strings)
enum ENUM_SAI_BIAS_FLIP     { FLIP_ON_CHOCH=0, NEUTRAL_ON_CHOCH=1 };
enum ENUM_SAI_BIAS_MODE     { BIAS_REQUIRE_BOTH=0, BIAS_H4_LEADS=1 };
enum ENUM_SAI_IMPULSE       { ANCHOR_SWING_CONFIRM=0, ANCHOR_BOS_BAR=1 };
enum ENUM_SAI_OB_ZONE       { OB_ZONE_WICK=0, OB_ZONE_BODY=1 };
enum ENUM_SAI_SL_ANCHOR     { SL_STRUCTURAL=0, SL_OB_DISTAL=1, SL_IMPULSE_ORIGIN=2 };
enum ENUM_SAI_RSI_MODE      { RSI_OFF=0, RSI_AT_SETUP=1, RSI_GATE_PLACEMENT=2, RSI_CONTINUOUS=3 };
enum ENUM_SAI_CONTINUATION  { CONT_CLOSE=0, CONT_WICK=1 };
enum ENUM_SAI_SWEEP_ACTION  { SWEEP_LOG_ONLY=0, SWEEP_BLOCK=1 };
enum ENUM_SAI_RUNNER        { RUNNER_STRUCTURE=0, RUNNER_LIQUIDITY=1, RUNNER_FIXED_R=2, RUNNER_TRAILING=3 };
enum ENUM_SAI_PARTIAL_FB    { PARTIAL_FB_CLOSE_ALL=0, PARTIAL_FB_KEEP_ALL=1 };
enum ENUM_SAI_RISK_BASE     { RISK_BASE_BALANCE=0, RISK_BASE_EQUITY=1, RISK_BASE_MIN_BAL_EQ=2, RISK_BASE_FIXED=3 };

//--- structure event kinds
enum ENUM_SAI_EVENT
  {
   EV_SWING_HIGH=0,
   EV_SWING_LOW =1,
   EV_BREAK_UP  =2,
   EV_BREAK_DOWN=3,
   EV_SWEEP_HIGH=4,
   EV_SWEEP_LOW =5
  };

//--- zone states (Docs/SPECIFICATION.md 6.3)
enum ENUM_SAI_ZONE_STATE
  {
   ZONE_NEW=0,
   ZONE_VALID=1,
   ZONE_PARTIALLY_MITIGATED=2,
   ZONE_FULLY_MITIGATED=3,
   ZONE_INVALIDATED=4
  };

//--- setup lifecycle as seen by the signal engine
enum ENUM_SAI_SETUP_STATUS
  {
   SETUP_STATUS_VALID=0,
   SETUP_STATUS_REJECTED=1,
   SETUP_STATUS_INVALIDATED=2,
   SETUP_STATUS_MISSED=3
  };

//--- trade state machine (Docs/STATE_MACHINE.md)
enum ENUM_SAI_STATE
  {
   ST_NO_SETUP=0,
   ST_SETUP_VALID=1,
   ST_PENDING_ORDER=2,
   ST_POSITION_OPEN=3,
   ST_BREAK_EVEN_SET=4,
   ST_PARTIAL_CLOSED=5,
   ST_RUNNER_ACTIVE=6,
   ST_CLOSED=7,
   ST_INVALIDATED=8,
   ST_ERROR_SAFE=9
  };

string StateName(const ENUM_SAI_STATE s)
  {
   switch(s)
     {
      case ST_NO_SETUP:       return "NO_SETUP";
      case ST_SETUP_VALID:    return "SETUP_VALID";
      case ST_PENDING_ORDER:  return "PENDING_ORDER";
      case ST_POSITION_OPEN:  return "POSITION_OPEN";
      case ST_BREAK_EVEN_SET: return "BREAK_EVEN_SET";
      case ST_PARTIAL_CLOSED: return "PARTIAL_CLOSED";
      case ST_RUNNER_ACTIVE:  return "RUNNER_ACTIVE";
      case ST_CLOSED:         return "CLOSED";
      case ST_INVALIDATED:    return "INVALIDATED";
      case ST_ERROR_SAFE:     return "ERROR_SAFE";
     }
   return "UNKNOWN";
  }

string EventName(const ENUM_SAI_EVENT e)
  {
   switch(e)
     {
      case EV_SWING_HIGH: return "SWING_HIGH";
      case EV_SWING_LOW:  return "SWING_LOW";
      case EV_BREAK_UP:   return "BREAK_UP";
      case EV_BREAK_DOWN: return "BREAK_DOWN";
      case EV_SWEEP_HIGH: return "SWEEP_HIGH";
      case EV_SWEEP_LOW:  return "SWEEP_LOW";
     }
   return "?";
  }

string ZoneStateName(const ENUM_SAI_ZONE_STATE z)
  {
   switch(z)
     {
      case ZONE_NEW:                 return "NEW";
      case ZONE_VALID:               return "VALID";
      case ZONE_PARTIALLY_MITIGATED: return "PARTIALLY_MITIGATED";
      case ZONE_FULLY_MITIGATED:     return "FULLY_MITIGATED";
      case ZONE_INVALIDATED:         return "INVALIDATED";
     }
   return "?";
  }

string RunnerName(const ENUM_SAI_RUNNER r)
  {
   switch(r)
     {
      case RUNNER_STRUCTURE: return "STRUCTURE";
      case RUNNER_LIQUIDITY: return "LIQUIDITY";
      case RUNNER_FIXED_R:   return "FIXED_R";
      case RUNNER_TRAILING:  return "TRAILING";
     }
   return "?";
  }

string DirName(const int d) { return d>0 ? "BUY" : (d<0 ? "SELL" : "NONE"); }

//--- a price level (swing / liquidity)
struct SLevel
  {
   bool              valid;
   int               index;          // pivot bar index
   double            price;
   int               confirm_index;  // bar at whose close the pivot became known
   void              Reset() { valid=false; index=-1; price=0.0; confirm_index=-1; }
  };

//--- a structure event
struct SEvent
  {
   ENUM_SAI_EVENT    kind;
   int               bar;      // bar index at whose close the event is known
   double            price;
   int               pivot;
   string            label;    // "BOS" / "CHOCH" for breaks
  };

//--- a price zone (low <= high)
struct SZone
  {
   bool              valid;
   double            low;
   double            high;
   int               index;
   void              Set(const double lo,const double hi,const int idx) { valid=true; low=lo; high=hi; index=idx; }
   void              Reset() { valid=false; low=0; high=0; index=-1; }
  };

//--- a fully specified setup (frozen at confirmation)
struct SSetup
  {
   string            id;
   int               direction;
   int               break_bar;
   datetime          break_time;
   string            break_label;
   double            broken_level;
   int               broken_pivot;
   int               origin_idx;
   double            origin_price;
   int               extreme_idx;
   double            extreme_price;
   int               confirm_bar;
   datetime          confirm_time;
   int               bias_h4;
   int               bias_h1;
   double            atr;
   double            spread;
   double            ote_low, ote_high;
   double            fvg_low, fvg_high; int fvg_mid_idx;
   double            ob_low, ob_high;   int ob_idx;
   double            zone_low, zone_high;
   string            entry_case;
   double            entry;
   double            sl;
   double            risk_dist;
   double            tp_liquidity;
   bool              tp_liquidity_is_fallback;
   double            rsi_extreme;
   string            sweeps_compatible;
   string            sweeps_caution;
   ENUM_SAI_SETUP_STATUS status;
   string            reason;
   int               place_bar;
   datetime          place_time;
   int               end_bar;
   datetime          end_time;
   string            end_reason;
  };

void SetupInit(SSetup &s)
  {
   s.id=""; s.direction=0; s.break_bar=-1; s.break_time=0; s.break_label=""; s.broken_level=0;
   s.broken_pivot=-1; s.origin_idx=-1; s.origin_price=0; s.extreme_idx=-1; s.extreme_price=0;
   s.confirm_bar=-1; s.confirm_time=0; s.bias_h4=0; s.bias_h1=0; s.atr=0; s.spread=0;
   //--- fields not computed (e.g. early rejection) stay EMPTY_VALUE (= NaN in the Python reference)
   s.ote_low=EMPTY_VALUE; s.ote_high=EMPTY_VALUE; s.fvg_low=EMPTY_VALUE; s.fvg_high=EMPTY_VALUE; s.fvg_mid_idx=-1;
   s.ob_low=EMPTY_VALUE; s.ob_high=EMPTY_VALUE; s.ob_idx=-1; s.zone_low=EMPTY_VALUE; s.zone_high=EMPTY_VALUE;
   s.entry_case=""; s.entry=EMPTY_VALUE; s.sl=EMPTY_VALUE; s.risk_dist=EMPTY_VALUE;
   s.tp_liquidity=EMPTY_VALUE; s.tp_liquidity_is_fallback=false; s.rsi_extreme=EMPTY_VALUE;
   s.sweeps_compatible=""; s.sweeps_caution=""; s.status=SETUP_STATUS_VALID; s.reason="";
   s.place_bar=-1; s.place_time=0; s.end_bar=-1; s.end_time=0; s.end_reason="";
  }

//--- engine decision (log line)
struct SDecision
  {
   datetime          time;
   int               bar;
   int               direction;
   string            code;
   string            detail;
  };

#endif
