//+------------------------------------------------------------------+
//| Indicators.mqh - exact ports of MT5 ATR.mq5 (SMA of TR) and      |
//| RSI.mq5 (Wilder smoothing seeded by a simple mean).               |
//| Mirrors Research/sensitor/indicators.py. Arrays are ascending     |
//| (index 0 = oldest). Values before warm-up are EMPTY_VALUE.        |
//+------------------------------------------------------------------+
#ifndef SENSITOR_INDICATORS_MQH
#define SENSITOR_INDICATORS_MQH

#include "Types.mqh"

//--- ATR as MT5: mean of TR[i-period+1..i] for i>=period
void CalcATR(const double &h[],const double &l[],const double &c[],const int n,const int period,double &out[])
  {
   ArrayResize(out,n);
   for(int i=0;i<n;i++) out[i]=EMPTY_VALUE;
   if(n<=period) return;
   double tr[];
   ArrayResize(tr,n);
   tr[0]=h[0]-l[0];
   for(int i=1;i<n;i++)
      tr[i]=MathMax(h[i],c[i-1])-MathMin(l[i],c[i-1]);
   double sum=0.0;
   for(int i=1;i<=period;i++) sum+=tr[i];
   out[period]=sum/period;
   for(int i=period+1;i<n;i++)
     {
      sum+=tr[i]-tr[i-period];
      out[i]=sum/period;
     }
  }

//--- incremental helper: ATR value at index k (needs tr window); used for appended bars
double AtrAt(const double &h[],const double &l[],const double &c[],const int k,const int period)
  {
   if(k<period) return EMPTY_VALUE;
   double sum=0.0;
   for(int i=k-period+1;i<=k;i++)
      sum+=MathMax(h[i],c[i-1])-MathMin(l[i],c[i-1]);
   return sum/period;
  }

double RsiValue(const double pos,const double neg)
  {
   if(neg!=0.0) return 100.0-100.0/(1.0+pos/neg);
   return (pos!=0.0) ? 100.0 : 50.0;
  }

//--- RSI with persistent smoothing state so it can be extended bar by bar
class CRsiCalc
  {
private:
   int               m_period;
   double            m_pos, m_neg;
   int               m_last;        // last computed index
public:
   double            values[];
                     CRsiCalc(void) : m_period(14), m_pos(0), m_neg(0), m_last(-1) {}
   void              Init(const int period) { m_period=period; m_pos=0; m_neg=0; m_last=-1; ArrayResize(values,0); }
   //--- compute/extend up to index n-1
   void              Update(const double &c[],const int n)
     {
      int old=ArraySize(values);
      ArrayResize(values,n);
      for(int i=old;i<n;i++) values[i]=EMPTY_VALUE;
      if(n<=m_period) return;
      int start=m_last+1;
      if(m_last<m_period)
        {
         double sp=0.0,sn=0.0;
         for(int i=1;i<=m_period;i++)
           {
            double d=c[i]-c[i-1];
            if(d>0) sp+=d; else if(d<0) sn-=d;
           }
         m_pos=sp/m_period; m_neg=sn/m_period;
         values[m_period]=RsiValue(m_pos,m_neg);
         start=m_period+1;
        }
      for(int i=start;i<n;i++)
        {
         double d=c[i]-c[i-1];
         m_pos=(m_pos*(m_period-1)+(d>0.0?d:0.0))/m_period;
         m_neg=(m_neg*(m_period-1)+(d<0.0?-d:0.0))/m_period;
         values[i]=RsiValue(m_pos,m_neg);
        }
      m_last=n-1;
     }
  };

//--- RSI exclusion rule [U]: buy blocked if max(RSI[k-w+1..k]) >= ob; sell if min <= os.
//--- insufficient data => blocked (conservative). extreme receives the max/min.
bool RsiWindowBlocks(const double &rsi[],const int k,const int window,const int direction,
                     const double ob,const double os,double &extreme)
  {
   extreme=EMPTY_VALUE;
   if(k<window-1 || k>=ArraySize(rsi)) return true;
   double mx=-DBL_MAX,mn=DBL_MAX;
   for(int i=k-window+1;i<=k;i++)
     {
      if(rsi[i]==EMPTY_VALUE) return true;
      mx=MathMax(mx,rsi[i]); mn=MathMin(mn,rsi[i]);
     }
   if(direction>0) { extreme=mx; return mx>=ob; }
   extreme=mn;
   return mn<=os;
  }

#endif
