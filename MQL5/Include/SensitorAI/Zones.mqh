//+------------------------------------------------------------------+
//| Zones.mqh - OTE, FVG, Order Block, intersection, entry & SL      |
//| Pure functions, mirror Research/sensitor/zones.py                 |
//+------------------------------------------------------------------+
#ifndef SENSITOR_ZONES_MQH
#define SENSITOR_ZONES_MQH

#include "Types.mqh"

//--- price at retracement r (0 = impulse extreme reached, 1 = origin)
double RetracementLevel(const int direction,const double lo,const double hi,const double r)
  {
   double rng=hi-lo;
   return direction>0 ? hi-r*rng : lo+r*rng;
  }

SZone OteZone(const int direction,const double lo,const double hi,const double rmin,const double rmax)
  {
   double a=RetracementLevel(direction,lo,hi,rmin);
   double b=RetracementLevel(direction,lo,hi,rmax);
   SZone z; z.Set(MathMin(a,b),MathMax(a,b),-1);
   return z;
  }

//--- FVGs with candles (m-1,m,m+1) inside [start,end], chronological. Returns count.
int FindFvgs(const int direction,const double &h[],const double &l[],const int start,const int end,
             const double min_size,SZone &out[])
  {
   ArrayResize(out,0);
   for(int m=start+1;m<end;m++)
     {
      double a,b;
      if(direction>0) { a=h[m-1]; b=l[m+1]; }
      else            { a=h[m+1]; b=l[m-1]; }
      if(b>a && (b-a)>=min_size && (b-a)>SAI_EPS)
        {
         int n=ArraySize(out);
         ArrayResize(out,n+1);
         out[n].Set(a,b,m);
        }
     }
   return ArraySize(out);
  }

//--- last opposite-colour candle searching back from m-1
SZone FindOrderBlock(const int direction,const double &o[],const double &h[],const double &l[],const double &c[],
                     const int fvg_mid,const int origin,const int max_dist,const int pre_origin,
                     const ENUM_SAI_OB_ZONE mode)
  {
   SZone z; z.Reset();
   int lo_bound=MathMax(MathMax(origin-pre_origin,fvg_mid-1-max_dist),0);
   for(int j=fvg_mid-1;j>=lo_bound;j--)
     {
      bool opposite=(direction>0) ? (c[j]<o[j]) : (c[j]>o[j]);
      if(opposite)
        {
         if(mode==OB_ZONE_BODY) z.Set(MathMin(o[j],c[j]),MathMax(o[j],c[j]),j);
         else                   z.Set(l[j],h[j],j);
         return z;
        }
     }
   return z;
  }

SZone Intersect(const SZone &a,const SZone &b)
  {
   SZone z; z.Reset();
   double lo=MathMax(a.low,b.low), hi=MathMin(a.high,b.high);
   if(lo>hi+SAI_EPS) return z;
   z.Set(lo,MathMax(lo,hi),a.index);
   return z;
  }

bool IsInside(const SZone &inner,const SZone &outer)
  {
   return inner.low>=outer.low-SAI_EPS && inner.high<=outer.high+SAI_EPS;
  }

ENUM_SAI_ZONE_STATE ZoneState(const int direction,const SZone &z,const double &h[],const double &l[],
                              const double &c[],const int first,const int last)
  {
   if(last<first) return ZONE_NEW;
   if(direction>0)
     {
      double m=DBL_MAX;
      for(int i=first;i<=last;i++)
        {
         if(c[i]<z.low-SAI_EPS) return ZONE_INVALIDATED;
         m=MathMin(m,l[i]);
        }
      if(m<=z.low+SAI_EPS)  return ZONE_FULLY_MITIGATED;
      if(m<=z.high+SAI_EPS) return ZONE_PARTIALLY_MITIGATED;
      return ZONE_VALID;
     }
   double mx=-DBL_MAX;
   for(int i=first;i<=last;i++)
     {
      if(c[i]>z.high+SAI_EPS) return ZONE_INVALIDATED;
      mx=MathMax(mx,h[i]);
     }
   if(mx>=z.high-SAI_EPS) return ZONE_FULLY_MITIGATED;
   if(mx>=z.low-SAI_EPS)  return ZONE_PARTIALLY_MITIGATED;
   return ZONE_VALID;
  }

//--- tick rounding (python: round(round(p/tick)*tick,10))
double RoundToTick(const double p,const double tick)  { return NormalizeDouble(MathRound(p/tick)*tick,10); }
double FloorToTick(const double p,const double tick)  { return NormalizeDouble(MathFloor(p/tick+1e-9)*tick,10); }
double CeilToTick(const double p,const double tick)   { return NormalizeDouble(MathCeil(p/tick-1e-9)*tick,10); }

//--- entry inside zone; returns false if no tick-aligned price fits
bool EntryPrice(const int direction,const SZone &zone,const double depth,const double tick,double &price)
  {
   double raw=(direction>0) ? zone.high-depth*(zone.high-zone.low) : zone.low+depth*(zone.high-zone.low);
   double lo_t=CeilToTick(zone.low,tick), hi_t=FloorToTick(zone.high,tick);
   if(lo_t>hi_t+SAI_EPS) return false;
   price=MathMin(MathMax(RoundToTick(raw,tick),lo_t),hi_t);
   return true;
  }

double StopLossPrice(const int direction,const SZone &ob,const double impulse_lo,const double impulse_hi,
                     const ENUM_SAI_SL_ANCHOR anchor,const double buffer,const double tick,const double spread_add)
  {
   double base;
   if(direction>0)
     {
      if(anchor==SL_OB_DISTAL)            base=ob.low;
      else if(anchor==SL_IMPULSE_ORIGIN)  base=impulse_lo;
      else                                base=MathMin(ob.low,impulse_lo);
      return FloorToTick(base-buffer,tick);
     }
   if(anchor==SL_OB_DISTAL)            base=ob.high;
   else if(anchor==SL_IMPULSE_ORIGIN)  base=impulse_hi;
   else                                base=MathMax(ob.high,impulse_hi);
   return CeilToTick(base+buffer+spread_add,tick);
  }

#endif
