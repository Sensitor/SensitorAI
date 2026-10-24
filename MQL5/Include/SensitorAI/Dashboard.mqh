//+------------------------------------------------------------------+
//| Dashboard.mqh - read-only chart panel and zone drawings.          |
//| Purely informative: the risk engine and order management never    |
//| depend on it, and every call is safe to skip.                     |
//+------------------------------------------------------------------+
#ifndef SENSITOR_DASHBOARD_MQH
#define SENSITOR_DASHBOARD_MQH

#include "Types.mqh"

class CDashboard
  {
private:
   bool              m_enabled;
   bool              m_draw;
   string            m_prefix;

public:
   void              Init(const bool enabled,const bool draw,const long magic)
     {
      m_enabled=enabled && !MQLInfoInteger(MQL_OPTIMIZATION);
      m_draw=draw && !MQLInfoInteger(MQL_OPTIMIZATION);
      m_prefix="SAI_"+IntegerToString(magic)+"_";
     }

   void              Show(const string text)
     {
      if(!m_enabled) return;
      Comment(text);
     }

   void              DrawSetup(const SSetup &s,const datetime from,const datetime to)
     {
      if(!m_draw) return;
      string p=m_prefix+s.id+"_";
      Rect(p+"OTE",from,to,s.ote_low,s.ote_high,clrDodgerBlue);
      Rect(p+"OB",from,to,s.ob_low,s.ob_high,s.direction>0 ? clrSeaGreen : clrIndianRed);
      Rect(p+"FVG",from,to,s.fvg_low,s.fvg_high,clrGoldenrod);
      HLine(p+"E",from,to,s.entry,clrWhite,STYLE_SOLID);
      HLine(p+"SL",from,to,s.sl,clrRed,STYLE_DASH);
     }

   void              Clear(void)
     {
      if(m_draw) ObjectsDeleteAll(0,m_prefix);
      if(m_enabled) Comment("");
     }

private:
   void              Rect(const string name,const datetime t1,const datetime t2,const double p1,const double p2,const color c)
     {
      if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_RECTANGLE,0,t1,p1,t2,p2);
      ObjectSetInteger(0,name,OBJPROP_COLOR,c);
      ObjectSetInteger(0,name,OBJPROP_FILL,true);
      ObjectSetInteger(0,name,OBJPROP_BACK,true);
      ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
      ObjectMove(0,name,0,t1,p1); ObjectMove(0,name,1,t2,p2);
     }
   void              HLine(const string name,const datetime t1,const datetime t2,const double p,const color c,const ENUM_LINE_STYLE st)
     {
      if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_TREND,0,t1,p,t2,p);
      ObjectSetInteger(0,name,OBJPROP_COLOR,c);
      ObjectSetInteger(0,name,OBJPROP_STYLE,st);
      ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);
      ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
      ObjectMove(0,name,0,t1,p); ObjectMove(0,name,1,t2,p);
     }
  };

#endif
