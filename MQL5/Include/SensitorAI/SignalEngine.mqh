//+------------------------------------------------------------------+
//| SignalEngine.mqh - confluence rules, RSI filter, frozen setups,  |
//| invalidation. Mirror of Research/sensitor/setups.py (SetupEngine) |
//| Incremental: ProcessEntryBar(k) after the caller appended every   |
//| bar (entry, H1, H4, RSI TF) closed at or before close(k).         |
//+------------------------------------------------------------------+
#ifndef SENSITOR_SIGNAL_MQH
#define SENSITOR_SIGNAL_MQH

#include "Config.mqh"
#include "StructureEngine.mqh"
#include "Zones.mqh"

struct SCandidate
  {
   bool              valid;
   int               direction;
   int               break_bar;
   string            break_label;
   double            broken_level;
   int               broken_pivot;
   int               origin_idx;
   double            origin_price;
  };

class CSignalEngine
  {
public:
   SConfig           cfg;
   double            tick;
   CBarSeries        entry,h1,h4,rsi_bars;
   bool              rsi_on_entry;
   CStructureTracker trk_e,trk_h1,trk_h4;
   CRsiCalc          rsi;
   SSetup            setups[];
   SDecision         decisions[];
   int               changed[];      // setup indices created/placed/ended during the last call
   int               last_bias,last_h4,last_h1;

private:
   int               m_h1_next,m_h4_next;
   SCandidate        m_cand[2];      // [0]=bull [1]=bear
   int               m_active[2];    // index in setups[] or -1
   double            m_spread;       // spread at decision time (price units)

   int               Slot(const int d) const { return d>0 ? 0 : 1; }

public:
                     CSignalEngine(void) : tick(0.01), rsi_on_entry(true), last_bias(0), last_h4(0), last_h1(0), m_h1_next(0), m_h4_next(0), m_spread(0) {}

   void              Init(const SConfig &c,const double tick_size)
     {
      cfg=c; tick=tick_size;
      entry.Init(PeriodSeconds(c.entry_tf));
      h1.Init(PeriodSeconds(PERIOD_H1));
      h4.Init(PeriodSeconds(PERIOD_H4));
      rsi_on_entry=(c.rsi_tf==PERIOD_CURRENT || c.rsi_tf==c.entry_tf);
      rsi_bars.Init(PeriodSeconds(rsi_on_entry ? c.entry_tf : c.rsi_tf));
      trk_e.Init(GetPointer(entry),c.swing_left_entry,c.swing_right_entry,c.bos_buffer_atr,c.bias_flip_mode,c.liquidity_max_levels);
      trk_h1.Init(GetPointer(h1),c.swing_left_htf,c.swing_right_htf,c.bos_buffer_atr,c.bias_flip_mode,c.liquidity_max_levels);
      trk_h4.Init(GetPointer(h4),c.swing_left_htf,c.swing_right_htf,c.bos_buffer_atr,c.bias_flip_mode,c.liquidity_max_levels);
      rsi.Init(c.rsi_period);
      ArrayResize(setups,0); ArrayResize(decisions,0); ArrayResize(changed,0);
      m_h1_next=0; m_h4_next=0;
      for(int i=0;i<2;i++) { m_cand[i].valid=false; m_active[i]=-1; }
      last_bias=0; last_h4=0; last_h1=0;
     }

   int               ActiveIndex(const int d) const { return m_active[Slot(d)]; }
   int               ProcessedEntryBars(void) const { return trk_e.last_k+1; }

   //--- main step: entry bar k is closed; spread = current spread (price units)
   void              ProcessEntryBar(const int k,const double spread)
     {
      ArrayResize(changed,0);
      m_spread=spread;
      datetime t=entry.CloseTime(k);
      AdvanceHtf(t);
      if(!rsi_on_entry) rsi.Update(rsi_bars.c,rsi_bars.Size());
      else              rsi.Update(entry.c,entry.Size());
      trk_e.Update(k);
      SEvent ev[];
      ArrayResize(ev,ArraySize(trk_e.new_events));
      for(int i=0;i<ArraySize(ev);i++) ev[i]=trk_e.new_events[i];
      int h4v=trk_h4.trend, h1v=trk_h1.trend;
      int bias=CombineBias(h4v,h1v,cfg.bias_mode);
      last_bias=bias; last_h4=h4v; last_h1=h1v;

      //--- 1) invalidation / gating of active setups
      for(int s=0;s<2;s++)
        {
         int d=(s==0) ? SAI_BULL : SAI_BEAR;
         int ai=m_active[s];
         if(ai<0 || k<=setups[ai].confirm_bar) continue;
         string reason=Invalidation(ai,k,bias);
         if(reason!="") { End(ai,k,t,reason); m_active[s]=-1; continue; }
         if(setups[ai].place_bar<0)
           {
            double val;
            if(!RsiCheck(t,d,val))
              {
               Place(ai,k,t);
               if(setups[ai].status!=SETUP_STATUS_VALID) m_active[s]=-1;
              }
           }
        }
      //--- 2) candidates waiting for the impulse swing (SWING_CONFIRM)
      for(int s=0;s<2;s++)
        {
         if(!m_cand[s].valid || k<=m_cand[s].break_bar) continue;
         int d=m_cand[s].direction;
         ENUM_SAI_EVENT opp=(d==SAI_BULL) ? EV_BREAK_DOWN : EV_BREAK_UP;
         bool opposite=false;
         for(int i=0;i<ArraySize(ev);i++) if(ev[i].kind==opp) opposite=true;
         if(opposite) { Log(t,k,d,"CANDIDATE_DROPPED_OPPOSITE_BREAK",""); m_cand[s].valid=false; continue; }
         if(bias!=d)  { Log(t,k,d,"CANDIDATE_DROPPED_BIAS","bias="+IntegerToString(bias)); m_cand[s].valid=false; continue; }
         ENUM_SAI_EVENT swk=(d==SAI_BULL) ? EV_SWING_HIGH : EV_SWING_LOW;
         int pivot=-1;
         for(int i=0;i<ArraySize(ev);i++)
            if(ev[i].kind==swk && ev[i].pivot>m_cand[s].origin_idx) { pivot=ev[i].pivot; break; }
         if(pivot>=0)
           {
            SCandidate cd=m_cand[s];
            m_cand[s].valid=false;
            int idx=Build(cd,pivot,k,t,bias,h4v,h1v);
            if(idx>=0) Activate(idx,k,t);
           }
        }
      //--- 3) new breaks => new candidates
      for(int i=0;i<ArraySize(ev);i++)
        {
         if(ev[i].kind!=EV_BREAK_UP && ev[i].kind!=EV_BREAK_DOWN) continue;
         int d=(ev[i].kind==EV_BREAK_UP) ? SAI_BULL : SAI_BEAR;
         if(bias!=d)
           {
            Log(t,k,d,"BREAK_IGNORED_BIAS",StringFormat("bias=%d h4=%d h1=%d",bias,h4v,h1v));
            continue;
           }
         SCandidate cd=MakeCandidate(d,ev[i],k);
         if(cfg.impulse_anchor==ANCHOR_BOS_BAR)
           {
            int idx=Build(cd,k,k,t,bias,h4v,h1v);
            if(idx>=0) Activate(idx,k,t);
           }
         else
           {
            int s=Slot(d);
            if(m_cand[s].valid) Log(t,k,d,"CANDIDATE_REPLACED","");
            m_cand[s]=cd;
            Log(t,k,d,"CANDIDATE_CREATED",StringFormat("level=%s %s",DoubleToString(ev[i].price,5),ev[i].label));
           }
        }
     }

   //--- force-end an active setup from outside (safety rules, order failure, ...)
   void              ForceEnd(const int idx,const string reason)
     {
      if(idx<0 || idx>=ArraySize(setups)) return;
      for(int s=0;s<2;s++) if(m_active[s]==idx) m_active[s]=-1;
      if(setups[idx].end_bar<0)
        {
         int k=trk_e.last_k;
         End(idx,k,(k>=0 ? entry.CloseTime(k) : 0),reason);
        }
     }

private:
   //--- append HTF bars (already loaded by the caller) whose close <= t to their trackers
   void              AdvanceHtf(const datetime t)
     {
      while(m_h1_next<h1.Size() && h1.CloseTime(m_h1_next)<=t) { trk_h1.Update(m_h1_next); m_h1_next++; }
      while(m_h4_next<h4.Size() && h4.CloseTime(m_h4_next)<=t) { trk_h4.Update(m_h4_next); m_h4_next++; }
     }

   void              Log(const datetime t,const int k,const int d,const string code,const string detail)
     {
      int n=ArraySize(decisions);
      ArrayResize(decisions,n+1,1024);
      decisions[n].time=t; decisions[n].bar=k; decisions[n].direction=d; decisions[n].code=code; decisions[n].detail=detail;
     }

   void              MarkChanged(const int idx)
     {
      for(int i=0;i<ArraySize(changed);i++) if(changed[i]==idx) return;
      int n=ArraySize(changed); ArrayResize(changed,n+1); changed[n]=idx;
     }

   //--- RSI exclusion. Returns true when BLOCKED. val receives the window extreme.
   bool              RsiCheck(const datetime t,const int d,double &val)
     {
      val=EMPTY_VALUE;
      if(cfg.rsi_mode==RSI_OFF) return false;
      int k=rsi_on_entry ? entry.LastClosedIndex(t) : rsi_bars.LastClosedIndex(t);
      return RsiWindowBlocks(rsi.values,k,cfg.rsi_window,d,cfg.rsi_overbought,cfg.rsi_oversold,val);
     }

   SCandidate        MakeCandidate(const int d,const SEvent &ev,const int k)
     {
      SCandidate cd;
      int i0=ev.pivot, o=i0;
      if(d==SAI_BULL)
        {
         double m=DBL_MAX;
         for(int j=i0;j<=k;j++) if(entry.l[j]<=m) { m=entry.l[j]; o=j; }   // last index of the minimum
        }
      else
        {
         double m=-DBL_MAX;
         for(int j=i0;j<=k;j++) if(entry.h[j]>=m) { m=entry.h[j]; o=j; }
        }
      cd.valid=true; cd.direction=d; cd.break_bar=k; cd.break_label=ev.label; cd.broken_level=ev.price;
      cd.broken_pivot=ev.pivot; cd.origin_idx=o; cd.origin_price=(d==SAI_BULL) ? entry.l[o] : entry.h[o];
      return cd;
     }

   void              Activate(const int idx,const int k,const datetime t)
     {
      MarkChanged(idx);
      if(setups[idx].status!=SETUP_STATUS_VALID) return;   // rejected/missed never supersede
      int s=Slot(setups[idx].direction);
      int old=m_active[s];
      if(old>=0) End(old,k,t,"INV_SUPERSEDED");
      m_active[s]=idx;
     }

   void              End(const int idx,const int k,const datetime t,const string reason)
     {
      setups[idx].end_bar=k; setups[idx].end_time=t; setups[idx].end_reason=reason;
      if(setups[idx].status==SETUP_STATUS_VALID) setups[idx].status=SETUP_STATUS_INVALIDATED;
      Log(t,k,setups[idx].direction,reason,setups[idx].id);
      MarkChanged(idx);
     }

   string            Invalidation(const int idx,const int k,const int bias)
     {
      int d=setups[idx].direction;
      double buf=0.0;
      if(cfg.bos_buffer_atr>0 && entry.atr[k]!=EMPTY_VALUE) buf=cfg.bos_buffer_atr*entry.atr[k];
      double ext=setups[idx].extreme_price;
      if(d==SAI_BULL)
        {
         if(cfg.continuation_invalidation==CONT_WICK) { if(entry.h[k]>ext) return "INV_CONTINUATION"; }
         else if(entry.c[k]>ext+buf) return "INV_CONTINUATION";
         if(entry.c[k]<setups[idx].sl || entry.c[k]<setups[idx].origin_price) return "INV_DEEP_FAILURE";
        }
      else
        {
         if(cfg.continuation_invalidation==CONT_WICK) { if(entry.l[k]<ext) return "INV_CONTINUATION"; }
         else if(entry.c[k]<ext-buf) return "INV_CONTINUATION";
         if(entry.c[k]>setups[idx].sl || entry.c[k]>setups[idx].origin_price) return "INV_DEEP_FAILURE";
        }
      if(cfg.cancel_on_bias_change && bias!=d) return "INV_BIAS_CHANGED";
      if(cfg.rsi_mode==RSI_CONTINUOUS && setups[idx].place_bar>=0)
        {
         double v;
         if(RsiCheck(entry.CloseTime(k),d,v)) return "INV_RSI";
        }
      return "";
     }

   void              Place(const int idx,const int k,const datetime t)
     {
      if(cfg.reject_if_touched_before_placement)
        {
         int a=setups[idx].extreme_idx+1, b=k;
         if(b>=a)
           {
            bool touched=false;
            for(int j=a;j<=b;j++)
              {
               if(setups[idx].direction==SAI_BULL && entry.l[j]<=setups[idx].entry) touched=true;
               if(setups[idx].direction==SAI_BEAR && entry.h[j]>=setups[idx].entry) touched=true;
              }
            if(touched)
              {
               setups[idx].status=SETUP_STATUS_MISSED; setups[idx].reason="MISSED_TOUCHED_BEFORE_PLACEMENT";
               Log(t,k,setups[idx].direction,setups[idx].reason,setups[idx].id);
               MarkChanged(idx);
               return;
              }
           }
        }
      setups[idx].place_bar=k; setups[idx].place_time=t;
      Log(t,k,setups[idx].direction,"READY_TO_PLACE",setups[idx].id);
      MarkChanged(idx);
     }

   int               Reject(const int idx,const int k,const datetime t,const string code,const string detail)
     {
      setups[idx].status=SETUP_STATUS_REJECTED; setups[idx].reason=code;
      Log(t,k,setups[idx].direction,code,setups[idx].id+(detail!="" ? " "+detail : ""));
      return idx;
     }

   //--- freeze all levels of a setup confirmed at close of bar k; returns its index (or -1)
   int               Build(const SCandidate &cd,const int end_idx,const int k,const datetime t,
                           const int bias,const int h4v,const int h1v)
     {
      int d=cd.direction, o_idx=cd.origin_idx;
      if(end_idx<o_idx) return -1;
      int ext_idx=o_idx; double lo,hi,ext_price;
      if(d==SAI_BULL)
        {
         for(int j=o_idx;j<=end_idx;j++) if(entry.h[j]>entry.h[ext_idx]) ext_idx=j;   // first max
         lo=cd.origin_price; hi=entry.h[ext_idx]; ext_price=hi;
        }
      else
        {
         for(int j=o_idx;j<=end_idx;j++) if(entry.l[j]<entry.l[ext_idx]) ext_idx=j;   // first min
         lo=entry.l[ext_idx]; hi=cd.origin_price; ext_price=lo;
        }
      double atr=entry.atr[k];
      int idx=ArraySize(setups);
      ArrayResize(setups,idx+1,256);
      SetupInit(setups[idx]);
      setups[idx].id=(d==SAI_BULL ? "B" : "S")+IntegerToString((long)entry.time[cd.break_bar]);
      setups[idx].direction=d; setups[idx].break_bar=cd.break_bar; setups[idx].break_time=entry.CloseTime(cd.break_bar);
      setups[idx].break_label=cd.break_label; setups[idx].broken_level=cd.broken_level; setups[idx].broken_pivot=cd.broken_pivot;
      setups[idx].origin_idx=o_idx; setups[idx].origin_price=cd.origin_price;
      setups[idx].extreme_idx=ext_idx; setups[idx].extreme_price=ext_price;
      setups[idx].confirm_bar=k; setups[idx].confirm_time=t; setups[idx].bias_h4=h4v; setups[idx].bias_h1=h1v;
      setups[idx].atr=atr; setups[idx].spread=m_spread;

      double rng=hi-lo;
      if(rng<=0 || atr==EMPTY_VALUE) return Reject(idx,k,t,"REJECT_DEGENERATE_IMPULSE","");
      if(cfg.min_impulse_atr>0 && rng<cfg.min_impulse_atr*atr) return Reject(idx,k,t,"REJECT_IMPULSE_TOO_SMALL","");
      SZone ote=OteZone(d,lo,hi,cfg.ote_min,cfg.ote_max);
      setups[idx].ote_low=ote.low; setups[idx].ote_high=ote.high;

      SZone fvgs[];
      if(FindFvgs(d,entry.h,entry.l,o_idx,ext_idx,cfg.fvg_min_atr*atr,fvgs)==0)
         return Reject(idx,k,t,"REJECT_NO_FVG","");
      string failure="REJECT_NO_OB";
      int chosen=-1; SZone ob,zone; ob.Reset(); zone.Reset();
      for(int f=0;f<ArraySize(fvgs);f++)
        {
         SZone cob=FindOrderBlock(d,entry.o,entry.h,entry.l,entry.c,fvgs[f].index,o_idx,cfg.ob_max_dist_bars,cfg.ob_pre_origin_bars,cfg.ob_zone_mode);
         if(!cob.valid) continue;
         SZone z=Intersect(cob,ote);
         if(!z.valid) { failure=Worse(failure,"REJECT_NO_OB_OTE_OVERLAP"); continue; }
         int first=fvgs[f].index+2;
         ENUM_SAI_ZONE_STATE obs=ZoneState(d,cob,entry.h,entry.l,entry.c,first,k);
         if(obs==ZONE_FULLY_MITIGATED || obs==ZONE_INVALIDATED) { failure=Worse(failure,"REJECT_OB_"+ZoneStateName(obs)); continue; }
         ENUM_SAI_ZONE_STATE fs=ZoneState(d,fvgs[f],entry.h,entry.l,entry.c,first,k);
         if(fs==ZONE_INVALIDATED) { failure=Worse(failure,"REJECT_FVG_INVALIDATED"); continue; }
         chosen=f; ob=cob; zone=z;
         break;
        }
      if(chosen<0) return Reject(idx,k,t,failure,"");
      setups[idx].fvg_low=fvgs[chosen].low; setups[idx].fvg_high=fvgs[chosen].high; setups[idx].fvg_mid_idx=fvgs[chosen].index;
      setups[idx].ob_low=ob.low; setups[idx].ob_high=ob.high; setups[idx].ob_idx=ob.index;
      setups[idx].zone_low=zone.low; setups[idx].zone_high=zone.high;
      setups[idx].entry_case=IsInside(ob,ote) ? "A" : "B";

      double e;
      if(!EntryPrice(d,zone,cfg.entry_depth,tick,e)) return Reject(idx,k,t,"REJECT_ZONE_TOO_NARROW","");
      setups[idx].entry=e;
      double buffer=MathMax(cfg.sl_buffer_points*tick,cfg.sl_buffer_atr*atr);
      double spread_add=(d==SAI_BEAR && cfg.sl_add_spread_for_sells) ? m_spread : 0.0;
      setups[idx].sl=StopLossPrice(d,ob,lo,hi,cfg.sl_anchor,buffer,tick,spread_add);
      setups[idx].risk_dist=NormalizeDouble(MathAbs(setups[idx].entry-setups[idx].sl),10);
      if(setups[idx].risk_dist<=0 || (d==SAI_BULL && setups[idx].sl>=e) || (d==SAI_BEAR && setups[idx].sl<=e))
         return Reject(idx,k,t,"REJECT_SL_INVALID","");
      if(setups[idx].risk_dist<cfg.min_sl_spread_mult*m_spread)
         return Reject(idx,k,t,"REJECT_SL_TOO_TIGHT",StringFormat("D=%.3f spread=%.3f",setups[idx].risk_dist,m_spread));
      if(cfg.max_sl_atr>0 && setups[idx].risk_dist>cfg.max_sl_atr*atr)
         return Reject(idx,k,t,"REJECT_SL_TOO_WIDE","");

      //--- sweeps
      string comp="",caution="";
      Sweeps(d,cd.break_bar,comp,caution);
      setups[idx].sweeps_compatible=comp; setups[idx].sweeps_caution=caution;
      if(caution!="" && cfg.caution_sweep_action==SWEEP_BLOCK) return Reject(idx,k,t,"REJECT_CAUTION_SWEEP",caution);
      if(cfg.require_compatible_sweep && comp=="") return Reject(idx,k,t,"REJECT_NO_COMPATIBLE_SWEEP","");

      //--- liquidity target for runner B (frozen now)
      double trg=e+d*cfg.partial_trigger_r*setups[idx].risk_dist;
      SLevel lv; bool found;
      if(cfg.liquidity_tf==PERIOD_H1)      found=(d==SAI_BULL) ? trk_h1.NearestLiquidityAbove(trg,lv) : trk_h1.NearestLiquidityBelow(trg,lv);
      else if(cfg.liquidity_tf==PERIOD_H4) found=(d==SAI_BULL) ? trk_h4.NearestLiquidityAbove(trg,lv) : trk_h4.NearestLiquidityBelow(trg,lv);
      else                                 found=(d==SAI_BULL) ? trk_e.NearestLiquidityAbove(trg,lv)  : trk_e.NearestLiquidityBelow(trg,lv);
      if(found) setups[idx].tp_liquidity=lv.price;
      else { setups[idx].tp_liquidity=e+d*cfg.liquidity_fallback_r*setups[idx].risk_dist; setups[idx].tp_liquidity_is_fallback=true; }

      //--- RSI exclusion
      double val;
      bool blocked=RsiCheck(t,d,val);
      setups[idx].rsi_extreme=val;
      if(cfg.rsi_mode==RSI_AT_SETUP && blocked) return Reject(idx,k,t,"REJECT_RSI",StringFormat("rsi=%.2f",val));
      Log(t,k,d,"SETUP_CONFIRMED",StringFormat("%s case=%s E=%s SL=%s D=%.3f",setups[idx].id,setups[idx].entry_case,
          DoubleToString(e,5),DoubleToString(setups[idx].sl,5),setups[idx].risk_dist));
      if((cfg.rsi_mode==RSI_GATE_PLACEMENT || cfg.rsi_mode==RSI_CONTINUOUS) && blocked)
        {
         Log(t,k,d,"WAIT_RSI_GATE",StringFormat("rsi=%.2f",val));
         return idx;
        }
      Place(idx,k,t);
      return idx;
     }

   void              Sweeps(const int d,const int break_bar,string &comp,string &caution)
     {
      int lb=cfg.sweep_lookback_bars;
      ENUM_SAI_EVENT want_comp=(d==SAI_BULL) ? EV_SWEEP_LOW : EV_SWEEP_HIGH;
      ENUM_SAI_EVENT want_caut=(d==SAI_BULL) ? EV_SWEEP_HIGH : EV_SWEEP_LOW;
      for(int i=ArraySize(trk_e.events)-1;i>=0;i--)
        {
         if(trk_e.events[i].bar<break_bar-lb) break;
         if(trk_e.events[i].kind==want_comp && trk_e.events[i].bar<=break_bar)
            comp=Join(comp,"E:"+PriceStr(trk_e.events[i].price));
        }
      ScanHtf(trk_h1,"H1",lb,want_comp,want_caut,comp,caution);
      ScanHtf(trk_h4,"H4",lb,want_comp,want_caut,comp,caution);
     }

   void              ScanHtf(CStructureTracker &trk,const string name,const int lb,const ENUM_SAI_EVENT wc,
                             const ENUM_SAI_EVENT wa,string &comp,string &caution)
     {
      for(int i=ArraySize(trk.events)-1;i>=0;i--)
        {
         if(trk.events[i].bar<trk.last_k-lb+1) break;
         if(trk.events[i].kind==wc)      comp=Join(comp,name+":"+PriceStr(trk.events[i].price));
         else if(trk.events[i].kind==wa) caution=Join(caution,name+":"+PriceStr(trk.events[i].price));
        }
     }

   static string     Join(const string a,const string b) { return a=="" ? b : a+";"+b; }
   static string     PriceStr(const double p) { return DoubleToString(p,5); }

   static int        RejectRank(const string r)
     {
      if(r=="REJECT_NO_OB") return 0;
      if(r=="REJECT_NO_OB_OTE_OVERLAP") return 1;
      if(r=="REJECT_OB_INVALIDATED") return 2;
      if(r=="REJECT_OB_FULLY_MITIGATED") return 3;
      if(r=="REJECT_FVG_INVALIDATED") return 4;
      return -1;
     }
   static string     Worse(const string a,const string b) { return RejectRank(a)>=RejectRank(b) ? a : b; }
  };

#endif
