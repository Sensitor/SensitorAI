//+------------------------------------------------------------------+
//| ImportCustomSymbol.mq5 - build a custom XAU/USD symbol from the   |
//| CSV produced by Research/scripts/export_mt5_custom.py, so that    |
//| the EA can be run in the Strategy Tester on the research data.    |
//| Symbol properties mimic a typical XAUUSD CFD: 2 digits, 100 oz,   |
//| tick 0.01 = 1 USD per lot. ADAPT them to your broker if needed.   |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input string InpCsv          = "SensitorAI\\XAUUSD_DK_M1.csv"; // CSV in Common\Files
input string InpSymbol       = "XAUUSD_DK";                   // custom symbol name
input double InpSwapLong     = -40.0;                         // swap long (USD per lot per night)
input double InpSwapShort    = -15.0;                         // swap short (USD per lot per night)
input bool   InpCloseTerminal= false;                         // close terminal when done

bool SetD(const ENUM_SYMBOL_INFO_DOUBLE p,const double v)  { return CustomSymbolSetDouble(InpSymbol,p,v); }
bool SetI(const ENUM_SYMBOL_INFO_INTEGER p,const long v)   { return CustomSymbolSetInteger(InpSymbol,p,v); }
bool SetS(const ENUM_SYMBOL_INFO_STRING p,const string v)  { return CustomSymbolSetString(InpSymbol,p,v); }

void Done(const int code,const string msg)
  {
   Print("ImportCustomSymbol: ",msg);
   int h=FileOpen("SensitorAI\\import_result.txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h!=INVALID_HANDLE) { FileWriteString(h,msg+"\n"); FileClose(h); }
   if(InpCloseTerminal) TerminalClose(code);
  }

void OnStart()
  {
   bool is_custom=false;
   if(!SymbolExist(InpSymbol,is_custom))
     {
      if(!CustomSymbolCreate(InpSymbol,"Sensitor"))
        { Done(1,StringFormat("CustomSymbolCreate failed err=%d",GetLastError())); return; }
     }
   //--- specification
   SetS(SYMBOL_CURRENCY_BASE,"XAU"); SetS(SYMBOL_CURRENCY_PROFIT,"USD"); SetS(SYMBOL_CURRENCY_MARGIN,"USD");
   SetS(SYMBOL_DESCRIPTION,"XAU/USD Dukascopy M1 (Sensitor research data)");
   SetI(SYMBOL_DIGITS,2);
   SetD(SYMBOL_POINT,0.01);
   SetD(SYMBOL_TRADE_TICK_SIZE,0.01);
   SetD(SYMBOL_TRADE_TICK_VALUE,1.0);
   SetD(SYMBOL_TRADE_TICK_VALUE_PROFIT,1.0);
   SetD(SYMBOL_TRADE_TICK_VALUE_LOSS,1.0);
   SetD(SYMBOL_TRADE_CONTRACT_SIZE,100.0);
   SetI(SYMBOL_TRADE_CALC_MODE,SYMBOL_CALC_MODE_CFDLEVERAGE);
   SetD(SYMBOL_MARGIN_INITIAL,0.0);
   SetD(SYMBOL_VOLUME_MIN,0.01); SetD(SYMBOL_VOLUME_STEP,0.01); SetD(SYMBOL_VOLUME_MAX,100.0);
   SetI(SYMBOL_TRADE_STOPS_LEVEL,0); SetI(SYMBOL_TRADE_FREEZE_LEVEL,0);
   SetI(SYMBOL_TRADE_MODE,SYMBOL_TRADE_MODE_FULL);
   SetI(SYMBOL_TRADE_EXEMODE,SYMBOL_TRADE_EXECUTION_MARKET);
   SetI(SYMBOL_FILLING_MODE,SYMBOL_FILLING_FOK|SYMBOL_FILLING_IOC);
   SetI(SYMBOL_EXPIRATION_MODE,SYMBOL_EXPIRATION_GTC|SYMBOL_EXPIRATION_DAY|SYMBOL_EXPIRATION_SPECIFIED);
   SetI(SYMBOL_ORDER_MODE,SYMBOL_ORDER_MARKET|SYMBOL_ORDER_LIMIT|SYMBOL_ORDER_STOP|SYMBOL_ORDER_SL|SYMBOL_ORDER_TP);
   SetI(SYMBOL_SPREAD_FLOAT,1);
   SetI(SYMBOL_SWAP_MODE,SYMBOL_SWAP_MODE_CURRENCY_SYMBOL);
   SetD(SYMBOL_SWAP_LONG,InpSwapLong); SetD(SYMBOL_SWAP_SHORT,InpSwapShort);
   SetI(SYMBOL_SWAP_ROLLOVER3DAYS,WEDNESDAY);
   //--- rates
   int h=FileOpen(InpCsv,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ);
   if(h==INVALID_HANDLE) { Done(1,"cannot open "+InpCsv); return; }
   FileReadString(h);  // header
   MqlRates buf[];
   ArrayResize(buf,0,200000);
   int total=0;
   bool first=true;
   while(!FileIsEnding(h))
     {
      string line=FileReadString(h);
      string f[];
      if(StringSplit(line,';',f)<7) continue;
      MqlRates r;
      r.time=(datetime)StringToInteger(f[0]);
      r.open=StringToDouble(f[1]); r.high=StringToDouble(f[2]); r.low=StringToDouble(f[3]); r.close=StringToDouble(f[4]);
      r.tick_volume=StringToInteger(f[5]); r.spread=(int)StringToInteger(f[6]); r.real_volume=0;
      int n=ArraySize(buf); ArrayResize(buf,n+1,200000); buf[n]=r;
      if(ArraySize(buf)>=100000)
        {
         int w=first ? CustomRatesReplace(InpSymbol,buf[0].time,D'2100.01.01',buf) : CustomRatesUpdate(InpSymbol,buf);
         if(w<0) { FileClose(h); Done(1,StringFormat("CustomRates write failed err=%d",GetLastError())); return; }
         total+=ArraySize(buf); first=false; ArrayResize(buf,0,200000);
        }
     }
   FileClose(h);
   if(ArraySize(buf)>0)
     {
      int w=first ? CustomRatesReplace(InpSymbol,buf[0].time,D'2100.01.01',buf) : CustomRatesUpdate(InpSymbol,buf);
      if(w<0) { Done(1,StringFormat("CustomRates write failed err=%d",GetLastError())); return; }
      total+=ArraySize(buf);
     }
   SymbolSelect(InpSymbol,true);
   Done(0,StringFormat("imported %d M1 bars into %s",total,InpSymbol));
  }
//+------------------------------------------------------------------+
