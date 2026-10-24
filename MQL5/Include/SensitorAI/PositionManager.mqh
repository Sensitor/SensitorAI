//+------------------------------------------------------------------+
//| PositionManager.mqh - open positions: initial risk (1R), break-   |
//| even at +1R, single 50 % partial at +3R, runner methods A-D.      |
//| State is rebuilt from MT5 (position + history) after a restart;   |
//| the StateStore only complements it.                               |
//+------------------------------------------------------------------+
#ifndef SENSITOR_POSITION_MQH
#define SENSITOR_POSITION_MQH

#include "Config.mqh"
#include "RiskManager.mqh"
#include "ExecutionManager.mqh"
#include "StateStore.mqh"

struct SPosState
  {
   ulong             ticket;
   long              identifier;
   string            setup_id;
   int               dir;
   double            entry_fill;
   double            entry_theoretical;
   double            sl0;
   double            vol0;
   double            R;                 // |entry_fill - sl0|
   double            risk_money;        // nominal money at risk at the fill
   double            tp_liquidity;      // frozen liquidity target (runner B), 0 if unknown
   bool              tp_set;
   bool              be_done;
   bool              partial_done;
   datetime          fill_time,be_time,partial_time;
   double            be_price,partial_price,partial_volume;
   double            spread_at_fill;
   ENUM_SAI_STATE    state;
   bool              seen;              // used during sync
  };

class CPositionManager
  {
private:
   SConfig           m_cfg;
   CMarketData      *m_md;
   CExecutionManager *m_ex;
   CRiskManager     *m_risk;
   CTradeLogger     *m_log;
   CStateStore      *m_store;
   long              m_magic;

public:
   SPosState         pos[];
   bool              critical;          // a position could not be protected
   string            critical_reason;

   void              Init(const SConfig &cfg,CMarketData *md,CExecutionManager *ex,CRiskManager *risk,
                          CTradeLogger *log,CStateStore *store,const long magic)
     {
      m_cfg=cfg; m_md=md; m_ex=ex; m_risk=risk; m_log=log; m_store=store; m_magic=magic;
      ArrayResize(pos,0); critical=false; critical_reason="";
     }

   int               Find(const ulong ticket) const
     {
      for(int i=0;i<ArraySize(pos);i++) if(pos[i].ticket==ticket) return i;
      return -1;
     }

   //--- rebuild the list from the terminal; closed positions are journalled and removed
   void              Sync(void)
     {
      for(int i=0;i<ArraySize(pos);i++) pos[i].seen=false;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong tk=PositionGetTicket(i);
         if(tk==0 || PositionGetInteger(POSITION_MAGIC)!=m_magic || PositionGetString(POSITION_SYMBOL)!=m_md.symbol) continue;
         int k=Find(tk);
         if(k<0) k=Reconstruct(tk);
         if(k>=0) pos[k].seen=true;
        }
      for(int i=ArraySize(pos)-1;i>=0;i--)
        {
         if(pos[i].seen) continue;
         Journal(i);
         Remove(i);
        }
     }

   //--- rebuild the state of one position from MT5 (and the store when available)
   int               Reconstruct(const ulong ticket)
     {
      if(!PositionSelectByTicket(ticket)) return -1;
      SPosState s; ZeroMemory(s);
      s.ticket=ticket;
      s.identifier=PositionGetInteger(POSITION_IDENTIFIER);
      s.dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY) ? 1 : -1;
      s.entry_fill=PositionGetDouble(POSITION_PRICE_OPEN);
      s.fill_time=(datetime)PositionGetInteger(POSITION_TIME);
      double cur_vol=PositionGetDouble(POSITION_VOLUME), cur_sl=PositionGetDouble(POSITION_SL);
      s.setup_id=CExecutionManager::SetupFromComment(PositionGetString(POSITION_COMMENT));
      string key="pos_"+IntegerToString(s.identifier)+"_";
      //--- history: initial volume (entry deals) and the SL of the opening order
      double vol_in=0, sl_hist=0; ulong open_order=0;
      if(HistorySelectByPosition(s.identifier))
        {
         for(int i=0;i<HistoryDealsTotal();i++)
           {
            ulong d=HistoryDealGetTicket(i);
            if(d==0) continue;
            ENUM_DEAL_ENTRY e=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(d,DEAL_ENTRY);
            if(e==DEAL_ENTRY_IN || e==DEAL_ENTRY_INOUT)
              {
               vol_in+=HistoryDealGetDouble(d,DEAL_VOLUME);
               if(open_order==0) open_order=(ulong)HistoryDealGetInteger(d,DEAL_ORDER);
              }
           }
         if(open_order>0 && HistoryOrderSelect(open_order))
           {
            sl_hist=HistoryOrderGetDouble(open_order,ORDER_SL);
            s.entry_theoretical=HistoryOrderGetDouble(open_order,ORDER_PRICE_OPEN);
            if(s.setup_id=="") s.setup_id=CExecutionManager::SetupFromComment(HistoryOrderGetString(open_order,ORDER_COMMENT));
           }
        }
      if(s.setup_id=="") s.setup_id=m_store.Get(key+"setup","UNKNOWN");
      s.sl0=m_store.GetD(key+"sl0",0.0);
      if(s.sl0==0.0) s.sl0=sl_hist;
      if(s.sl0==0.0 && cur_sl>0 && s.dir*(cur_sl-s.entry_fill)<0) s.sl0=cur_sl;   // last resort: current adverse stop
      s.vol0=m_store.GetD(key+"vol0",0.0);
      if(s.vol0==0.0) s.vol0=(vol_in>0) ? vol_in : cur_vol;
      s.tp_liquidity=m_store.GetD(key+"tpliq",0.0);
      s.spread_at_fill=m_store.GetD(key+"spread",0.0);
      if(s.entry_theoretical==0.0) s.entry_theoretical=m_store.GetD(key+"etheo",s.entry_fill);
      s.R=MathAbs(s.entry_fill-s.sl0);
      s.risk_money=0;
      double loss;
      if(s.sl0>0 && m_risk.LossPerLot(s.dir,s.entry_fill,s.sl0,loss)) s.risk_money=loss*s.vol0;
      s.be_done=(m_store.Get(key+"be","0")=="1") || (cur_sl>0 && s.dir*(cur_sl-s.entry_fill)>=-SAI_EPS);
      s.partial_done=(m_store.Get(key+"partial","0")=="1") || (cur_vol<s.vol0-m_md.spec.vol_step/2);
      s.be_time=(datetime)(long)m_store.GetD(key+"betime",0);
      s.partial_time=(datetime)(long)m_store.GetD(key+"ptime",0);
      if(s.partial_done && s.partial_time==0) s.partial_time=TimeTradeServer();
      s.tp_set=(m_store.Get(key+"tpset","0")=="1");
      s.state=s.partial_done ? ST_RUNNER_ACTIVE : (s.be_done ? ST_BREAK_EVEN_SET : ST_POSITION_OPEN);
      if(s.sl0==0.0)
        {
         critical=true;
         critical_reason="position "+IntegerToString((long)ticket)+" has no known initial SL";
         m_log.Error("Reconstruct",critical_reason);
        }
      Persist(s);
      int n=ArraySize(pos); ArrayResize(pos,n+1); pos[n]=s;
      m_log.Event(s.setup_id,ticket,"RESTORE",StateName(s.state),s.entry_fill,
                  StringFormat("sl0=%s vol0=%.2f R=%.5f be=%d partial=%d",DoubleToString(s.sl0,m_md.spec.digits),s.vol0,s.R,(int)s.be_done,(int)s.partial_done));
      return n;
     }

   //--- register a fresh fill (called from OnTradeTransaction) with setup info
   void              OnFill(const ulong ticket,const string setup_id,const double entry_theo,const double sl0,
                            const double tp_liq,const double spread)
     {
      if(!PositionSelectByTicket(ticket)) return;
      string key="pos_"+IntegerToString(PositionGetInteger(POSITION_IDENTIFIER))+"_";
      if(!m_store.Has(key+"sl0"))
        {
         m_store.Set(key+"setup",setup_id,false);
         m_store.Set(key+"sl0",DoubleToString(sl0,10),false);
         m_store.Set(key+"vol0",DoubleToString(PositionGetDouble(POSITION_VOLUME),8),false);
         m_store.Set(key+"tpliq",DoubleToString(tp_liq,10),false);
         m_store.Set(key+"spread",DoubleToString(spread,10),false);
         m_store.Set(key+"etheo",DoubleToString(entry_theo,10),true);
        }
      if(Find(ticket)<0) Reconstruct(ticket);
     }

   //--- per-tick protective management (BE, partial, TP placement). Server-side SL/TP keep
   //--- protecting the position if the terminal disconnects; BE/partial need the EA running.
   void              OnTick(void)
     {
      for(int i=0;i<ArraySize(pos);i++)
        {
         if(!PositionSelectByTicket(pos[i].ticket)) continue;
         double cur_sl=PositionGetDouble(POSITION_SL), cur_tp=PositionGetDouble(POSITION_TP);
         double vol=PositionGetDouble(POSITION_VOLUME);
         double px=(pos[i].dir>0) ? m_md.Bid() : m_md.Ask();
         //--- a position must never stay without a stop
         if(cur_sl==0.0 && pos[i].sl0>0)
           {
            if(!m_ex.ModifyPosition(pos[i].ticket,pos[i].setup_id,pos[i].sl0,cur_tp,"restore missing SL"))
              { critical=true; critical_reason="cannot restore SL on #"+IntegerToString((long)pos[i].ticket); }
            continue;
           }
         if(pos[i].R<=0) continue;
         //--- server-side TP adjusted to the real fill (methods B and C)
         if(!pos[i].tp_set)
           {
            double tp=DesiredTP(i);
            if(tp<=0 || MathAbs(tp-cur_tp)<m_md.spec.tick_size/2 ||
               m_ex.ModifyPosition(pos[i].ticket,pos[i].setup_id,cur_sl,tp,"runner target"))
              {
               pos[i].tp_set=true;
               m_store.Set(Key(i)+"tpset","1");
              }
           }
         double r=RMultiple(pos[i].dir,pos[i].entry_fill,pos[i].sl0,px);
         //--- break-even at +1R (never widens the stop)
         if(!pos[i].be_done && r>=m_cfg.be_trigger_r)
            DoBreakEven(i,px);
         //--- single partial at +3R (computed with the INITIAL risk)
         if(!pos[i].partial_done && r>=m_cfg.partial_trigger_r)
           {
            if(!pos[i].be_done) DoBreakEven(i,px);
            DoPartial(i,vol,px);
           }
        }
     }

   //--- runner management on a new closed entry-TF bar (methods A and D)
   void              OnEntryBar(const SEvent &events[],const CBarSeries &bars,const double spread)
     {
      for(int i=0;i<ArraySize(pos);i++)
        {
         if(!pos[i].partial_done || !PositionSelectByTicket(pos[i].ticket)) continue;
         for(int e=0;e<ArraySize(events);e++)
           {
            datetime known=bars.CloseTime(events[e].bar);
            if(known<=pos[i].partial_time) continue;
            if(m_cfg.runner_method==RUNNER_STRUCTURE)
              {
               ENUM_SAI_EVENT opp=(pos[i].dir>0) ? EV_BREAK_DOWN : EV_BREAK_UP;
               if(events[e].kind!=opp) continue;
               double px;
               double vol=PositionGetDouble(POSITION_VOLUME);
               if(m_ex.ClosePosition(pos[i].ticket,pos[i].setup_id,vol,"runner A: structure break",px))
                  m_log.Event(pos[i].setup_id,pos[i].ticket,StateName(pos[i].state),"CLOSED",px,"runner STRUCTURE exit");
               break;
              }
            if(m_cfg.runner_method==RUNNER_TRAILING)
              {
               ENUM_SAI_EVENT sw=(pos[i].dir>0) ? EV_SWING_LOW : EV_SWING_HIGH;
               if(events[e].kind!=sw) continue;
               double a=bars.atr[events[e].bar];
               double buf=(a==EMPTY_VALUE) ? 0.0 : m_cfg.trailing_buffer_atr*a;
               double lvl=(pos[i].dir>0) ? FloorToTick(events[e].price-buf,m_md.spec.tick_size)
                                         : CeilToTick(events[e].price+buf+(m_cfg.sl_add_spread_for_sells ? spread : 0.0),m_md.spec.tick_size);
               double cur_sl=PositionGetDouble(POSITION_SL);
               if(TighterSL(pos[i].dir,cur_sl,lvl))
                 {
                  if(m_ex.ModifyPosition(pos[i].ticket,pos[i].setup_id,lvl,PositionGetDouble(POSITION_TP),"runner D: trailing"))
                     m_log.Event(pos[i].setup_id,pos[i].ticket,StateName(pos[i].state),StateName(pos[i].state),lvl,"trailing stop moved");
                 }
              }
           }
        }
     }

   double            TotalRiskMoney(void) const
     {
      double s=0;
      for(int i=0;i<ArraySize(pos);i++) s+=pos[i].risk_money;
      return s;
     }

private:
   string            Key(const int i) const { return "pos_"+IntegerToString(pos[i].identifier)+"_"; }

   void              Persist(const SPosState &s)
     {
      string key="pos_"+IntegerToString(s.identifier)+"_";
      m_store.Set(key+"setup",s.setup_id,false);
      m_store.Set(key+"sl0",DoubleToString(s.sl0,10),false);
      m_store.Set(key+"vol0",DoubleToString(s.vol0,8),true);
     }

   double            DesiredTP(const int i) const
     {
      double R=pos[i].R; int d=pos[i].dir;
      if(m_cfg.runner_method==RUNNER_FIXED_R) return pos[i].entry_fill+d*m_cfg.runner_target_r*R;
      if(m_cfg.runner_method==RUNNER_LIQUIDITY)
        {
         double part=pos[i].entry_fill+d*m_cfg.partial_trigger_r*R;
         if(pos[i].tp_liquidity>0 && d*(pos[i].tp_liquidity-part)>0) return pos[i].tp_liquidity;
         return pos[i].entry_fill+d*m_cfg.liquidity_fallback_r*R;
        }
      return 0.0;   // A and D: no server TP
     }

   void              DoBreakEven(const int i,const double px)
     {
      if(!PositionSelectByTicket(pos[i].ticket)) return;
      double cur_sl=PositionGetDouble(POSITION_SL);
      double target=FloorToTick(pos[i].entry_fill,m_md.spec.tick_size);
      if(pos[i].dir<0) target=CeilToTick(pos[i].entry_fill,m_md.spec.tick_size);
      target+=pos[i].dir*m_cfg.be_offset_points*m_md.spec.point;
      if(!TighterSL(pos[i].dir,cur_sl,target)) { MarkBE(i,cur_sl,"already at/after entry"); return; }
      if(m_ex.ModifyPosition(pos[i].ticket,pos[i].setup_id,target,PositionGetDouble(POSITION_TP),"break-even +1R"))
         MarkBE(i,target,StringFormat("trigger price %s",DoubleToString(px,m_md.spec.digits)));
     }

   void              MarkBE(const int i,const double sl,const string detail)
     {
      ENUM_SAI_STATE from=pos[i].state;
      pos[i].be_done=true; pos[i].be_time=TimeTradeServer(); pos[i].be_price=sl;
      if(pos[i].state==ST_POSITION_OPEN) pos[i].state=ST_BREAK_EVEN_SET;
      m_store.Set(Key(i)+"be","1",false);
      m_store.Set(Key(i)+"betime",IntegerToString((long)pos[i].be_time),true);
      m_log.Event(pos[i].setup_id,pos[i].ticket,StateName(from),StateName(pos[i].state),sl,detail);
     }

   void              DoPartial(const int i,const double cur_vol,const double px)
     {
      string action;
      double v=PartialCloseVolume(pos[i].vol0,cur_vol,m_cfg.partial_fraction,m_md.spec.vol_min,m_md.spec.vol_step,m_cfg.partial_fallback,action);
      double fill=px;
      bool ok=true;
      if(v>0) ok=m_ex.ClosePosition(pos[i].ticket,pos[i].setup_id,v,"partial +3R "+action,fill);
      if(!ok) return;                                   // retried on the next tick
      ENUM_SAI_STATE from=pos[i].state;
      pos[i].partial_done=true; pos[i].partial_time=TimeTradeServer(); pos[i].partial_price=fill; pos[i].partial_volume=v;
      pos[i].state=ST_PARTIAL_CLOSED;
      m_store.Set(Key(i)+"partial","1",false);
      m_store.Set(Key(i)+"ptime",IntegerToString((long)pos[i].partial_time),true);
      m_log.Event(pos[i].setup_id,pos[i].ticket,StateName(from),"PARTIAL_CLOSED",fill,StringFormat("%s volume=%.2f",action,v));
      pos[i].state=ST_RUNNER_ACTIVE;
      m_log.Event(pos[i].setup_id,pos[i].ticket,"PARTIAL_CLOSED","RUNNER_ACTIVE",fill,"runner "+RunnerName(m_cfg.runner_method));
     }

   //--- one CSV line per closed position, rebuilt from the deal history
   void              Journal(const int i)
     {
      double profit=0,comm=0,swap=0,exit_px=0,exit_vol=0; datetime exit_t=0; string reason="";
      if(HistorySelectByPosition(pos[i].identifier))
        {
         for(int k=0;k<HistoryDealsTotal();k++)
           {
            ulong d=HistoryDealGetTicket(k);
            if(d==0) continue;
            profit+=HistoryDealGetDouble(d,DEAL_PROFIT);
            comm+=HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);
            swap+=HistoryDealGetDouble(d,DEAL_SWAP);
            ENUM_DEAL_ENTRY e=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(d,DEAL_ENTRY);
            if(e==DEAL_ENTRY_OUT || e==DEAL_ENTRY_OUT_BY)
              {
               exit_px=HistoryDealGetDouble(d,DEAL_PRICE); exit_vol+=HistoryDealGetDouble(d,DEAL_VOLUME);
               exit_t=(datetime)HistoryDealGetInteger(d,DEAL_TIME);
               ENUM_DEAL_REASON rs=(ENUM_DEAL_REASON)HistoryDealGetInteger(d,DEAL_REASON);
               reason=(rs==DEAL_REASON_SL ? "SL" : rs==DEAL_REASON_TP ? "TP" : rs==DEAL_REASON_SO ? "STOP_OUT" : "MARKET");
              }
           }
        }
      double net=profit+comm+swap;
      double r_net=(pos[i].risk_money>0) ? net/pos[i].risk_money : 0.0;
      int dg=m_md.spec.digits;
      string line=StringFormat("%s,%I64u,%s,%s,%s,%s,%s,%s,%s,%s,%.2f,%.2f,%s,%s,%s,%s,%s,%s,%s,%.2f,%s,%s,%s,%.2f,%.2f,%.2f,%.2f,%.4f,%d,,,,,,,,,,,,",
                               pos[i].setup_id,pos[i].ticket,m_md.symbol,DirName(pos[i].dir),RunnerName(m_cfg.runner_method),
                               DoubleToString(pos[i].entry_theoretical,dg),DoubleToString(pos[i].entry_fill,dg),
                               DoubleToString(pos[i].dir*(pos[i].entry_theoretical-pos[i].entry_fill),dg),
                               DoubleToString(pos[i].sl0,dg),"",pos[i].vol0,pos[i].risk_money,DoubleToString(pos[i].R,dg),
                               DoubleToString(pos[i].spread_at_fill,dg),TimeToString(pos[i].fill_time,TIME_DATE|TIME_SECONDS),
                               pos[i].be_time>0 ? TimeToString(pos[i].be_time,TIME_DATE|TIME_SECONDS) : "",DoubleToString(pos[i].be_price,dg),
                               pos[i].partial_time>0 && pos[i].partial_done ? TimeToString(pos[i].partial_time,TIME_DATE|TIME_SECONDS) : "",
                               DoubleToString(pos[i].partial_price,dg),pos[i].partial_volume,
                               exit_t>0 ? TimeToString(exit_t,TIME_DATE|TIME_SECONDS) : "",DoubleToString(exit_px,dg),reason,
                               profit,comm,swap,net,r_net,(int)((exit_t-pos[i].fill_time)/60));
      m_log.Trade(line);
      m_log.Event(pos[i].setup_id,pos[i].ticket,StateName(pos[i].state),"CLOSED",exit_px,
                  StringFormat("%s net=%.2f R=%.3f",reason,net,r_net));
      string key=Key(i);
      string suffixes[]={"setup","sl0","vol0","tpliq","spread","etheo","be","betime","partial","ptime","tpset"};
      for(int s=0;s<ArraySize(suffixes);s++) m_store.Remove(key+suffixes[s]);
     }

   void              Remove(const int i)
     {
      int n=ArraySize(pos);
      for(int k=i+1;k<n;k++) pos[k-1]=pos[k];
      ArrayResize(pos,n-1);
     }
  };

#endif
