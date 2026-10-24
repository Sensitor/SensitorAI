//+------------------------------------------------------------------+
//| TradeLogger.mqh - structured CSV journals (Common\Files\SensitorAI)|
//| decisions.csv  every engine decision with its reason code          |
//| setups.csv     every confirmed/rejected setup with frozen levels   |
//| orders.csv     every trade request and the server response         |
//| trades.csv     one line per closed trade (R, money, costs, ...)    |
//| events.csv     state transitions, BE, partial, runner actions      |
//| errors.csv     errors and anomalies                                |
//| Read by Research/scripts/analyze_mt5_logs.py                       |
//+------------------------------------------------------------------+
#ifndef SENSITOR_LOGGER_MQH
#define SENSITOR_LOGGER_MQH

#include "Types.mqh"

class CTradeLogger
  {
private:
   string            m_dir;
   string            m_tag;
   bool              m_enabled;
   bool              m_print;

   string            Path(const string name) const { return m_dir+"\\"+m_tag+"_"+name+".csv"; }

   void              Write(const string name,const string header,const string line)
     {
      if(!m_enabled) return;
      string p=Path(name);
      bool exists=FileIsExist(p,FILE_COMMON);
      int h=FileOpen(p,FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ);
      if(h==INVALID_HANDLE) { PrintFormat("Logger: cannot open %s err=%d",p,GetLastError()); return; }
      if(!exists || FileSize(h)==0) FileWriteString(h,header+"\n");
      FileSeek(h,0,SEEK_END);
      FileWriteString(h,line+"\n");
      FileClose(h);
     }

   static string     Esc(string s) { StringReplace(s,",",";"); StringReplace(s,"\n"," "); return s; }
   static string     Ts(const datetime t) { return t>0 ? TimeToString(t,TIME_DATE|TIME_SECONDS) : ""; }
   static string     D(const double v,const int digits=5) { return (v==EMPTY_VALUE || !MathIsValidNumber(v)) ? "" : DoubleToString(v,digits); }

public:
   void              Init(const string tag,const bool enabled,const bool echo)
     {
      m_dir="SensitorAI"; m_tag=tag; m_enabled=enabled; m_print=echo;
      if(m_enabled) FolderCreate(m_dir,FILE_COMMON);
     }

   void              Decision(const string symbol,const string tf,const SDecision &d)
     {
      Write("decisions","time,symbol,tf,bar,direction,code,detail",
            StringFormat("%s,%s,%s,%d,%s,%s,%s",Ts(d.time),symbol,tf,d.bar,DirName(d.direction),d.code,Esc(d.detail)));
     }

   void              Setup(const string symbol,const string tf,const SSetup &s)
     {
      string status=(s.status==SETUP_STATUS_VALID ? "VALID" : s.status==SETUP_STATUS_REJECTED ? "REJECTED" :
                     s.status==SETUP_STATUS_MISSED ? "MISSED" : "INVALIDATED");
      Write("setups",
            "setup_id,symbol,tf,direction,status,reason,break_time,break_label,broken_level,origin,extreme,confirm_time,"
            "bias_h4,bias_h1,atr,spread,ote_low,ote_high,fvg_low,fvg_high,ob_low,ob_high,zone_low,zone_high,entry_case,"
            "entry,sl,risk_dist,tp_liquidity,tp_liq_fallback,rsi_extreme,sweeps_compatible,sweeps_caution,place_time,end_time,end_reason",
            StringFormat("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%d,%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%d,%s,%s,%s,%s,%s,%s",
                         s.id,symbol,tf,DirName(s.direction),status,s.reason,Ts(s.break_time),s.break_label,D(s.broken_level),
                         D(s.origin_price),D(s.extreme_price),Ts(s.confirm_time),s.bias_h4,s.bias_h1,D(s.atr),D(s.spread),
                         D(s.ote_low),D(s.ote_high),D(s.fvg_low),D(s.fvg_high),D(s.ob_low),D(s.ob_high),D(s.zone_low),D(s.zone_high),
                         s.entry_case,D(s.entry),D(s.sl),D(s.risk_dist),D(s.tp_liquidity),(int)s.tp_liquidity_is_fallback,
                         D(s.rsi_extreme,2),Esc(s.sweeps_compatible),Esc(s.sweeps_caution),Ts(s.place_time),Ts(s.end_time),s.end_reason));
     }

   void              Order(const string action,const string setup_id,const MqlTradeRequest &rq,const MqlTradeResult &rs,const string note)
     {
      Write("orders",
            "time,action,setup_id,symbol,type,volume,price,sl,tp,order,position,retcode,result_deal,result_order,result_volume,result_price,comment,note",
            StringFormat("%s,%s,%s,%s,%s,%s,%s,%s,%s,%I64u,%I64u,%u,%I64u,%I64u,%s,%s,%s,%s",
                         Ts(TimeTradeServer()),action,setup_id,rq.symbol,EnumToString(rq.type),D(rq.volume,2),D(rq.price),D(rq.sl),
                         D(rq.tp),rq.order,rq.position,rs.retcode,rs.deal,rs.order,D(rs.volume,2),D(rs.price),Esc(rs.comment),Esc(note)));
      if(m_print) PrintFormat("[order] %s %s ret=%u %s %s",action,setup_id,rs.retcode,rs.comment,note);
     }

   void              Event(const string setup_id,const ulong position,const string from_state,const string to_state,
                           const double price,const string detail)
     {
      Write("events","time,setup_id,position,from_state,to_state,price,detail",
            StringFormat("%s,%s,%I64u,%s,%s,%s,%s",Ts(TimeTradeServer()),setup_id,position,from_state,to_state,D(price),Esc(detail)));
      if(m_print) PrintFormat("[event] %s #%I64u %s -> %s @%s %s",setup_id,position,from_state,to_state,D(price),detail);
     }

   void              Trade(const string line)
     {
      Write("trades",
            "setup_id,position,symbol,direction,runner,entry_theoretical,entry_fill,slippage_entry,sl_initial,tp,volume_initial,"
            "risk_nominal_money,risk_dist,spread_at_fill,fill_time,be_time,be_price,partial_time,partial_price,partial_volume,"
            "exit_time,exit_price,exit_reason,profit,commission,swap,net,r_net,hold_minutes,bias_h4,bias_h1,rsi_extreme,"
            "ote_low,ote_high,ob_low,ob_high,fvg_low,fvg_high,entry_case,sweeps_compatible,sweeps_caution",line);
     }

   void              Error(const string where,const string what)
     {
      Write("errors","time,where,what",StringFormat("%s,%s,%s",Ts(TimeTradeServer()),where,Esc(what)));
      PrintFormat("[ERROR] %s: %s",where,what);
     }

   void              Info(const string what) { if(m_print) Print(what); }
  };

#endif
