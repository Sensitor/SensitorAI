//+------------------------------------------------------------------+
//| NewsFilter.mqh - optional economic-calendar blackout (MT5 API).   |
//| Blocks NEW order placement within [event-before, event+after]     |
//| for high-impact events of the selected currencies.                |
//| NOT a protection against slippage. The MT5 calendar is not        |
//| available in the Strategy Tester: the filter is then inactive     |
//| (logged) and its effect is therefore NOT backtested.              |
//+------------------------------------------------------------------+
#ifndef SENSITOR_NEWS_MQH
#define SENSITOR_NEWS_MQH

class CNewsFilter
  {
private:
   bool              m_enabled;
   int               m_before,m_after;      // minutes
   string            m_currencies;          // e.g. "USD"
   datetime          m_events[];
   string            m_names[];
   datetime          m_loaded_at;

public:
   bool              active;
   string            status;

   void              Init(const bool enabled,const int before_min,const int after_min,const string currencies)
     {
      m_enabled=enabled; m_before=before_min; m_after=after_min; m_currencies=currencies;
      m_loaded_at=0; active=false; status="disabled";
      if(!m_enabled) return;
      if(MQLInfoInteger(MQL_TESTER)) { status="inactive in Strategy Tester (no calendar)"; return; }
      active=true; status="enabled";
      Refresh();
     }

   //--- pure window test (unit-tested): is t inside [ev-before, ev+after] for any event?
   static bool       InWindow(const datetime t,const datetime &events[],const int before_min,const int after_min,int &which)
     {
      which=-1;
      for(int i=0;i<ArraySize(events);i++)
         if(t>=events[i]-before_min*60 && t<=events[i]+after_min*60) { which=i; return true; }
      return false;
     }

   void              Refresh(void)
     {
      if(!active) return;
      datetime now=TimeTradeServer();
      if(m_loaded_at>0 && now-m_loaded_at<3600) return;
      ArrayResize(m_events,0); ArrayResize(m_names,0);
      string ccys[];
      int n=StringSplit(m_currencies,',',ccys);
      for(int c=0;c<n;c++)
        {
         MqlCalendarValue vals[];
         if(CalendarValueHistory(vals,now-6*3600,now+48*3600,NULL,ccys[c])<=0) continue;
         for(int i=0;i<ArraySize(vals);i++)
           {
            MqlCalendarEvent ev;
            if(!CalendarEventById(vals[i].event_id,ev)) continue;
            if(ev.importance!=CALENDAR_IMPORTANCE_HIGH) continue;
            int k=ArraySize(m_events);
            ArrayResize(m_events,k+1); ArrayResize(m_names,k+1);
            m_events[k]=vals[i].time; m_names[k]=ccys[c]+" "+ev.name;
           }
        }
      m_loaded_at=now;
      status=StringFormat("enabled (%d high-impact events loaded)",ArraySize(m_events));
     }

   bool              Blocked(const datetime t,string &why)
     {
      why="";
      if(!active) return false;
      Refresh();
      int w;
      if(InWindow(t,m_events,m_before,m_after,w)) { why=m_names[w]+" @ "+TimeToString(m_events[w]); return true; }
      return false;
     }
  };

#endif
