//+------------------------------------------------------------------+
//| MarketData.mqh - symbol specification, closed bars, prices,      |
//| data quality / synchronisation checks.                            |
//| Rule: only CLOSED bars are ever handed to the engines.            |
//+------------------------------------------------------------------+
#ifndef SENSITOR_MARKETDATA_MQH
#define SENSITOR_MARKETDATA_MQH

#include "Types.mqh"
#include "StructureEngine.mqh"

struct SSymbolSpec
  {
   string            name;
   int               digits;
   double            point;
   double            tick_size;
   double            tick_value;
   double            contract_size;
   double            vol_min,vol_max,vol_step,vol_limit;
   int               stops_level;      // points
   int               freeze_level;     // points
   long              filling_flags;
   long              expiration_flags;
   ENUM_SYMBOL_TRADE_EXECUTION exec_mode;
   ENUM_SYMBOL_TRADE_MODE trade_mode;
   string            profit_currency;
   string            account_currency;
   bool              hedging;
  };

class CMarketData
  {
public:
   string            symbol;
   SSymbolSpec       spec;
   string            last_error;

   bool              Init(const string sym)
     {
      symbol=sym;
      if(!SymbolSelect(symbol,true)) { last_error="SymbolSelect failed for "+symbol; return false; }
      return RefreshSpec();
     }

   //--- read every property from the broker; never assume XAU/USD conventions
   bool              RefreshSpec(void)
     {
      spec.name=symbol;
      spec.digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
      spec.point=SymbolInfoDouble(symbol,SYMBOL_POINT);
      spec.tick_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
      spec.tick_value=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_VALUE);
      spec.contract_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_CONTRACT_SIZE);
      spec.vol_min=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
      spec.vol_max=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
      spec.vol_step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
      spec.vol_limit=SymbolInfoDouble(symbol,SYMBOL_VOLUME_LIMIT);
      spec.stops_level=(int)SymbolInfoInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL);
      spec.freeze_level=(int)SymbolInfoInteger(symbol,SYMBOL_TRADE_FREEZE_LEVEL);
      spec.filling_flags=SymbolInfoInteger(symbol,SYMBOL_FILLING_MODE);
      spec.expiration_flags=SymbolInfoInteger(symbol,SYMBOL_EXPIRATION_MODE);
      spec.exec_mode=(ENUM_SYMBOL_TRADE_EXECUTION)SymbolInfoInteger(symbol,SYMBOL_TRADE_EXEMODE);
      spec.trade_mode=(ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(symbol,SYMBOL_TRADE_MODE);
      spec.profit_currency=SymbolInfoString(symbol,SYMBOL_CURRENCY_PROFIT);
      spec.account_currency=AccountInfoString(ACCOUNT_CURRENCY);
      spec.hedging=((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE)==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
      if(spec.tick_size<=0 || spec.point<=0) { last_error="invalid tick size / point"; return false; }
      if(spec.vol_min<=0 || spec.vol_step<=0 || spec.vol_max<spec.vol_min) { last_error="invalid volume constraints"; return false; }
      if(spec.contract_size<=0) { last_error="invalid contract size"; return false; }
      return true;
     }

   string            SpecSummary(void) const
     {
      return StringFormat("%s digits=%d point=%g tick=%g tickValue=%g contract=%g vol[min=%g step=%g max=%g limit=%g] stops=%d freeze=%d fill=%d exp=%d exec=%d hedging=%s profitCcy=%s accountCcy=%s",
                          spec.name,spec.digits,spec.point,spec.tick_size,spec.tick_value,spec.contract_size,
                          spec.vol_min,spec.vol_step,spec.vol_max,spec.vol_limit,spec.stops_level,spec.freeze_level,
                          (int)spec.filling_flags,(int)spec.expiration_flags,(int)spec.exec_mode,
                          spec.hedging?"yes":"no",spec.profit_currency,spec.account_currency);
     }

   double            Bid(void) const { return SymbolInfoDouble(symbol,SYMBOL_BID); }
   double            Ask(void) const { return SymbolInfoDouble(symbol,SYMBOL_ASK); }
   double            Spread(void) const { return Ask()-Bid(); }
   int               SpreadPoints(void) const { return (int)MathRound(Spread()/spec.point); }
   bool              TradingAllowed(void) const { return spec.trade_mode==SYMBOL_TRADE_MODE_FULL; }

   //--- open time of the bar containing t on timeframe tf (server time, epoch aligned)
   static datetime   BarStart(const datetime t,const ENUM_TIMEFRAMES tf)
     {
      int s=PeriodSeconds(tf);
      return (datetime)((long)t/s*s);
     }

   //--- true when the series of tf already contains the bar opened at or before T and
   //--- is synchronised (avoids the race where H1 is not yet rebuilt at a new M15 bar)
   bool              SeriesReady(const ENUM_TIMEFRAMES tf,const datetime T)
     {
      if(!SeriesInfoInteger(symbol,tf,SERIES_SYNCHRONIZED)) { last_error="series not synchronised "+EnumToString(tf); return false; }
      datetime cur=iTime(symbol,tf,0);
      if(cur==0) { last_error="iTime failed "+EnumToString(tf); return false; }
      if(cur<BarStart(T,tf)) { last_error="series not updated yet "+EnumToString(tf); return false; }
      return true;
     }

   //--- append to `s` every CLOSED bar of tf (close time <= upto) newer than its last bar.
   //--- returns number appended, or -1 on error. max_initial bounds the warm-up load.
   int               AppendClosed(CBarSeries &s,const ENUM_TIMEFRAMES tf,const datetime upto,const int max_initial)
     {
      MqlRates r[];
      ArraySetAsSeries(r,false);
      int want=(s.Size()==0) ? max_initial : 64;
      int got=0;
      for(int attempt=0;attempt<8;attempt++)
        {
         got=CopyRates(symbol,tf,0,want,r);
         if(got<=0) { last_error=StringFormat("CopyRates %s failed err=%d",EnumToString(tf),GetLastError()); return -1; }
         // enough history to connect with what we already have?
         if(s.Size()==0 || r[0].time<=s.LastTime() || got<want) break;
         want*=4;
         if(want>200000) break;
        }
      int added=0;
      int psec=PeriodSeconds(tf);
      for(int i=0;i<got;i++)
        {
         if(r[i].time+psec>upto) break;           // forming bar (or future): never used
         if(s.Size()>0 && r[i].time<=s.LastTime()) continue;
         if(r[i].high<r[i].low || r[i].open<=0 || r[i].close<=0) { last_error="corrupted bar "+TimeToString(r[i].time); return -1; }
         if(s.Append(r[i].time,r[i].open,r[i].high,r[i].low,r[i].close)) added++;
        }
      return added;
     }

   //--- detect abnormal gaps between consecutive bars (excluding weekends); returns count
   static int        CountGaps(const CBarSeries &s,const int from,const int max_gap_bars)
     {
      int gaps=0;
      for(int i=MathMax(from,1);i<s.Size();i++)
        {
         long dt=(long)(s.time[i]-s.time[i-1]);
         if(dt>(long)max_gap_bars*s.tf_seconds)
           {
            MqlDateTime a; TimeToStruct(s.time[i-1],a);
            if(!(a.day_of_week==5 || a.day_of_week==6 || dt>=36*3600)) gaps++;   // weekend / holiday tolerated
           }
        }
      return gaps;
     }
  };

#endif
