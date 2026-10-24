//+------------------------------------------------------------------+
//| StructureEngine.mqh - swings, BOS/CHoCH, trend, liquidity, sweeps|
//| Analysis only: this module never places orders.                   |
//| Processes CLOSED bars one by one; output at bar k depends only on |
//| bars 0..k. Mirror of Research/sensitor/structure.py.              |
//+------------------------------------------------------------------+
#ifndef SENSITOR_STRUCTURE_MQH
#define SENSITOR_STRUCTURE_MQH

#include "Types.mqh"
#include "Indicators.mqh"

//+------------------------------------------------------------------+
//| Ascending series of CLOSED bars of one timeframe                  |
//+------------------------------------------------------------------+
class CBarSeries
  {
public:
   int               tf_seconds;
   datetime          time[];     // bar OPEN time
   double            o[],h[],l[],c[];
   double            spread[];   // historical spread of the bar (price units), 0 if unknown
   double            atr[];
   int               atr_period;

                     CBarSeries(void) : tf_seconds(0), atr_period(14) {}
   void              Init(const int tf_sec) { tf_seconds=tf_sec; Clear(); }
   void              Clear(void) { ArrayResize(time,0); ArrayResize(o,0); ArrayResize(h,0); ArrayResize(l,0); ArrayResize(c,0); ArrayResize(atr,0); ArrayResize(spread,0); }
   int               Size(void) const { return ArraySize(time); }
   datetime          CloseTime(const int i) const { return time[i]+tf_seconds; }
   datetime          LastTime(void) const { int n=ArraySize(time); return n>0 ? time[n-1] : 0; }

   //--- append one closed bar (must be newer than the last one)
   bool              Append(const datetime t,const double op,const double hi,const double lo,const double cl,const double sp=0.0)
     {
      int n=ArraySize(time);
      if(n>0 && t<=time[n-1]) return false;
      ArrayResize(time,n+1,4096); ArrayResize(o,n+1,4096); ArrayResize(h,n+1,4096); ArrayResize(l,n+1,4096);
      ArrayResize(c,n+1,4096); ArrayResize(atr,n+1,4096); ArrayResize(spread,n+1,4096);
      time[n]=t; o[n]=op; h[n]=hi; l[n]=lo; c[n]=cl; spread[n]=sp;
      atr[n]=AtrAt(h,l,c,n,atr_period);
      return true;
     }

   //--- index of the last bar whose close time <= t (-1 if none)
   int               LastClosedIndex(const datetime t) const
     {
      int lo=0,hi=ArraySize(time)-1,ans=-1;
      while(lo<=hi)
        {
         int mid=(lo+hi)/2;
         if(time[mid]+tf_seconds<=t) { ans=mid; lo=mid+1; }
         else hi=mid-1;
        }
      return ans;
     }
  };

//--- swing tests (strict on the left, non-strict on the right)
bool IsSwingHigh(const double &h[],const int n,const int i,const int left,const int right)
  {
   if(i-left<0 || i+right>=n) return false;
   for(int j=i-left;j<i;j++)          if(!(h[i]>h[j]))  return false;
   for(int j=i+1;j<=i+right;j++)      if(!(h[i]>=h[j])) return false;
   return true;
  }

bool IsSwingLow(const double &l[],const int n,const int i,const int left,const int right)
  {
   if(i-left<0 || i+right>=n) return false;
   for(int j=i-left;j<i;j++)          if(!(l[i]<l[j]))  return false;
   for(int j=i+1;j<=i+right;j++)      if(!(l[i]<=l[j])) return false;
   return true;
  }

int CombineBias(const int h4,const int h1,const ENUM_SAI_BIAS_MODE mode)
  {
   if(mode==BIAS_REQUIRE_BOTH)
      return (h4==h1 && h4!=SAI_NEUTRAL) ? h4 : SAI_NEUTRAL;
   if(h4==SAI_NEUTRAL) return SAI_NEUTRAL;
   if(h1==-h4) return SAI_NEUTRAL;
   return h4;
  }

//+------------------------------------------------------------------+
//| Incremental structure tracker for one timeframe                   |
//+------------------------------------------------------------------+
class CStructureTracker
  {
public:
   CBarSeries       *bars;
   int               left,right;
   double            bos_buffer_atr;
   ENUM_SAI_BIAS_FLIP flip_mode;
   int               max_levels;
   SLevel            ref_high,ref_low,last_swing_high,last_swing_low;
   int               trend;
   SLevel            liq_highs[];
   SLevel            liq_lows[];
   SEvent            events[];
   int               last_k;
   //--- events produced by the last Update() call
   SEvent            new_events[];

                     CStructureTracker(void) : bars(NULL), left(2), right(2), bos_buffer_atr(0), flip_mode(FLIP_ON_CHOCH), max_levels(30), trend(0), last_k(-1) {}

   void              Init(CBarSeries *b,const int lft,const int rgt,const double buf_atr,
                          const ENUM_SAI_BIAS_FLIP flip,const int maxlv)
     {
      bars=b; left=lft; right=rgt; bos_buffer_atr=buf_atr; flip_mode=flip; max_levels=maxlv;
      Reset();
     }

   void              Reset(void)
     {
      ref_high.Reset(); ref_low.Reset(); last_swing_high.Reset(); last_swing_low.Reset();
      trend=SAI_NEUTRAL; ArrayResize(liq_highs,0); ArrayResize(liq_lows,0);
      ArrayResize(events,0); ArrayResize(new_events,0); last_k=-1;
     }

   double            Buffer(const int k) const
     {
      if(bos_buffer_atr<=0) return 0.0;
      double a=bars.atr[k];
      return (a==EMPTY_VALUE) ? 0.0 : bos_buffer_atr*a;
     }

   //--- process bar k (must be last_k+1). Returns number of new events.
   int               Update(const int k)
     {
      ArrayResize(new_events,0);
      if(k!=last_k+1) { PrintFormat("StructureTracker: non sequential update %d after %d",k,last_k); return -1; }
      last_k=k;
      double c=bars.c[k], h=bars.h[k], l=bars.l[k];
      double buf=Buffer(k);
      //--- 1. liquidity levels: broken (close beyond) or swept (wick beyond, close back)
      SLevel keep[];
      for(int i=0;i<ArraySize(liq_highs);i++)
        {
         if(c>liq_highs[i].price+buf) continue;
         if(h>liq_highs[i].price) { Emit(EV_SWEEP_HIGH,k,liq_highs[i].price,liq_highs[i].index,""); continue; }
         Push(keep,liq_highs[i]);
        }
      CopyLevels(keep,liq_highs);
      ArrayResize(keep,0);
      for(int i=0;i<ArraySize(liq_lows);i++)
        {
         if(c<liq_lows[i].price-buf) continue;
         if(l<liq_lows[i].price) { Emit(EV_SWEEP_LOW,k,liq_lows[i].price,liq_lows[i].index,""); continue; }
         Push(keep,liq_lows[i]);
        }
      CopyLevels(keep,liq_lows);
      //--- 2. breaks of the references (close beyond; a wick is never a break)
      if(ref_high.valid && c>ref_high.price+buf)
        {
         string label=(trend==SAI_BEAR) ? "CHOCH" : "BOS";
         Emit(EV_BREAK_UP,k,ref_high.price,ref_high.index,label);
         ref_high.Reset();
         ApplyBreak(SAI_BULL,label);
        }
      if(ref_low.valid && c<ref_low.price-buf)
        {
         string label=(trend==SAI_BULL) ? "CHOCH" : "BOS";
         Emit(EV_BREAK_DOWN,k,ref_low.price,ref_low.index,label);
         ref_low.Reset();
         ApplyBreak(SAI_BEAR,label);
        }
      //--- 3. swings confirmed at this bar (pivot k-right)
      int i=k-right;
      int n=k+1;  // only bars 0..k may be read
      if(i>=0)
        {
         if(IsSwingHigh(bars.h,n,i,left,right))
           {
            SLevel lv; lv.valid=true; lv.index=i; lv.price=bars.h[i]; lv.confirm_index=k;
            ref_high=lv; last_swing_high=lv;
            Push(liq_highs,lv);
            if(ArraySize(liq_highs)>max_levels) RemoveFirst(liq_highs);
            Emit(EV_SWING_HIGH,k,lv.price,i,"");
           }
         if(IsSwingLow(bars.l,n,i,left,right))
           {
            SLevel lv; lv.valid=true; lv.index=i; lv.price=bars.l[i]; lv.confirm_index=k;
            ref_low=lv; last_swing_low=lv;
            Push(liq_lows,lv);
            if(ArraySize(liq_lows)>max_levels) RemoveFirst(liq_lows);
            Emit(EV_SWING_LOW,k,lv.price,i,"");
           }
        }
      return ArraySize(new_events);
     }

   //--- nearest active liquidity level strictly above / below a price
   bool              NearestLiquidityAbove(const double price,SLevel &out) const
     {
      bool found=false;
      for(int i=0;i<ArraySize(liq_highs);i++)
         if(liq_highs[i].price>price && (!found || liq_highs[i].price<out.price)) { out=liq_highs[i]; found=true; }
      return found;
     }
   bool              NearestLiquidityBelow(const double price,SLevel &out) const
     {
      bool found=false;
      for(int i=0;i<ArraySize(liq_lows);i++)
         if(liq_lows[i].price<price && (!found || liq_lows[i].price>out.price)) { out=liq_lows[i]; found=true; }
      return found;
     }

private:
   void              ApplyBreak(const int direction,const string label)
     {
      if(flip_mode==NEUTRAL_ON_CHOCH && label=="CHOCH") trend=SAI_NEUTRAL;
      else trend=direction;
     }
   void              Emit(const ENUM_SAI_EVENT kind,const int bar,const double price,const int pivot,const string label)
     {
      SEvent e; e.kind=kind; e.bar=bar; e.price=price; e.pivot=pivot; e.label=label;
      int n=ArraySize(events); ArrayResize(events,n+1,1024); events[n]=e;
      int m=ArraySize(new_events); ArrayResize(new_events,m+1); new_events[m]=e;
     }
   static void       Push(SLevel &arr[],const SLevel &lv) { int n=ArraySize(arr); ArrayResize(arr,n+1); arr[n]=lv; }
   static void       CopyLevels(const SLevel &src[],SLevel &dst[])
     {
      ArrayResize(dst,ArraySize(src));
      for(int i=0;i<ArraySize(src);i++) dst[i]=src[i];
     }
   static void       RemoveFirst(SLevel &arr[])
     {
      int n=ArraySize(arr);
      for(int i=1;i<n;i++) arr[i-1]=arr[i];
      ArrayResize(arr,n-1);
     }
  };

#endif
