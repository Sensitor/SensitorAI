//+------------------------------------------------------------------+
//| RiskManager.mqh - sizing (OrderCalcProfit), margin, exposure and |
//| daily limits. Never increases risk after losses.                  |
//| Pure volume arithmetic mirrors Research/sensitor/risk.py.         |
//+------------------------------------------------------------------+
#ifndef SENSITOR_RISK_MQH
#define SENSITOR_RISK_MQH

#include "Config.mqh"
#include "MarketData.mqh"

//--- pure helpers (unit-tested in Scripts/SensitorAI/SensitorTests.mq5)
double FloorStep(const double v,const double step) { return NormalizeDouble(MathFloor(v/step+SAI_EPS)*step,8); }

double ComputeVolume(const double risk_money,const double loss_per_lot,const double commission_per_lot,
                     const double vmin,const double vstep,const double vmax,const double vlimit,string &reason)
  {
   if(risk_money<=0) { reason="REJECT_RISK_MONEY"; return 0.0; }
   double per_lot=MathAbs(loss_per_lot)+MathMax(commission_per_lot,0.0);
   if(per_lot<=0 || !MathIsValidNumber(per_lot)) { reason="REJECT_LOSS_PER_LOT"; return 0.0; }
   double vol=FloorStep(risk_money/per_lot,vstep);
   double cap=(vlimit<=0) ? vmax : MathMin(vmax,vlimit);
   if(vol>cap) vol=FloorStep(cap,vstep);
   if(vol<vmin-SAI_EPS) { reason="REJECT_MIN_LOT_EXCEEDS_RISK"; return 0.0; }
   reason="OK";
   return vol;
  }

double PartialCloseVolume(const double initial_volume,const double current_volume,const double fraction,
                          const double vmin,const double vstep,const ENUM_SAI_PARTIAL_FB fallback,string &action)
  {
   double target=MathMin(FloorStep(initial_volume*fraction,vstep),current_volume);
   double remainder=NormalizeDouble(current_volume-target,8);
   if(target>=vmin-SAI_EPS && remainder>=vmin-SAI_EPS) { action="PARTIAL"; return target; }
   if(fallback==PARTIAL_FB_CLOSE_ALL) { action="FALLBACK_CLOSE_ALL"; return current_volume; }
   action="FALLBACK_KEEP_ALL";
   return 0.0;
  }

double RMultiple(const int direction,const double entry,const double sl_initial,const double price)
  {
   double risk=MathAbs(entry-sl_initial);
   if(risk<=0) return 0.0;
   return direction*(price-entry)/risk;
  }

bool TighterSL(const int direction,const double current_sl,const double candidate)
  {
   if(current_sl==0.0) return true;                          // no stop at all: any stop is tighter
   return direction>0 ? candidate>current_sl+SAI_EPS : candidate<current_sl-SAI_EPS;
  }

//+------------------------------------------------------------------+
class CRiskManager
  {
private:
   SConfig           m_cfg;
   CMarketData      *m_md;
   long              m_magic;
   datetime          m_day;
   double            m_day_start_balance;

public:
   string            last_reason;

   void              Init(const SConfig &cfg,CMarketData *md,const long magic)
     {
      m_cfg=cfg; m_md=md; m_magic=magic; m_day=0; m_day_start_balance=0;
      RollDay();
     }

   double            RiskBaseMoney(void) const
     {
      double bal=AccountInfoDouble(ACCOUNT_BALANCE), eq=AccountInfoDouble(ACCOUNT_EQUITY);
      switch(m_cfg.risk_base)
        {
         case RISK_BASE_BALANCE: return bal;
         case RISK_BASE_EQUITY:  return eq;
         case RISK_BASE_FIXED:   return m_cfg.fixed_capital;
         default:                return MathMin(bal,eq);
        }
     }

   double            RiskMoney(void) const { return RiskBaseMoney()*m_cfg.risk_pct/100.0; }

   //--- loss for 1 lot between entry and SL, in account currency, from the broker's own maths
   bool              LossPerLot(const int direction,const double entry,const double sl,double &loss)
     {
      double profit=0.0;
      ENUM_ORDER_TYPE t=(direction>0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      ResetLastError();
      if(!OrderCalcProfit(t,m_md.symbol,1.0,entry,sl,profit))
        {
         last_reason=StringFormat("OrderCalcProfit failed err=%d",GetLastError());
         return false;
        }
      loss=-profit;
      if(loss<=0) { last_reason="OrderCalcProfit returned a non-negative loss"; return false; }
      return true;
     }

   //--- volume for a setup; 0 => refuse (reason in last_reason)
   double            VolumeFor(const int direction,const double entry,const double sl)
     {
      double loss;
      if(!LossPerLot(direction,entry,sl,loss)) return 0.0;
      string why;
      double vol=ComputeVolume(RiskMoney(),loss,m_cfg.commission_per_lot,m_md.spec.vol_min,m_md.spec.vol_step,
                               m_md.spec.vol_max,m_md.spec.vol_limit,why);
      last_reason=why;
      if(vol<=0) return 0.0;
      //--- margin check
      double margin=0;
      ENUM_ORDER_TYPE t=(direction>0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(!OrderCalcMargin(t,m_md.symbol,vol,entry,margin)) { last_reason="OrderCalcMargin failed"; return 0.0; }
      if(margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.9) { last_reason="REJECT_INSUFFICIENT_MARGIN"; return 0.0; }
      return vol;
     }

   //--- current open risk (% of base) of our positions (loss to current SL, only if adverse) and pending orders
   double            OpenRiskPct(void)
     {
      double base=RiskBaseMoney();
      if(base<=0) return 1e9;
      double risk=0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong tk=PositionGetTicket(i);
         if(tk==0 || PositionGetInteger(POSITION_MAGIC)!=m_magic || PositionGetString(POSITION_SYMBOL)!=m_md.symbol) continue;
         int d=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY) ? 1 : -1;
         double open=PositionGetDouble(POSITION_PRICE_OPEN), sl=PositionGetDouble(POSITION_SL), vol=PositionGetDouble(POSITION_VOLUME);
         if(sl==0.0) { risk+=base; continue; }                     // unprotected position = unlimited risk
         if(d*(sl-open)>=0) continue;                              // stop at/after entry: no risk left
         double loss;
         if(LossPerLot(d,open,sl,loss)) risk+=loss*vol;
        }
      for(int i=OrdersTotal()-1;i>=0;i--)
        {
         ulong tk=OrderGetTicket(i);
         if(tk==0 || OrderGetInteger(ORDER_MAGIC)!=m_magic || OrderGetString(ORDER_SYMBOL)!=m_md.symbol) continue;
         ENUM_ORDER_TYPE t=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
         int d=(t==ORDER_TYPE_BUY_LIMIT || t==ORDER_TYPE_BUY_STOP || t==ORDER_TYPE_BUY_STOP_LIMIT) ? 1 : -1;
         double loss;
         if(LossPerLot(d,OrderGetDouble(ORDER_PRICE_OPEN),OrderGetDouble(ORDER_SL),loss))
            risk+=loss*OrderGetDouble(ORDER_VOLUME_CURRENT);
        }
      return risk/base*100.0;
     }

   int               CountPositions(void) const
     {
      int n=0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong tk=PositionGetTicket(i);
         if(tk!=0 && PositionGetInteger(POSITION_MAGIC)==m_magic && PositionGetString(POSITION_SYMBOL)==m_md.symbol) n++;
        }
      return n;
     }

   int               CountPending(const int direction=0) const
     {
      int n=0;
      for(int i=OrdersTotal()-1;i>=0;i--)
        {
         ulong tk=OrderGetTicket(i);
         if(tk==0 || OrderGetInteger(ORDER_MAGIC)!=m_magic || OrderGetString(ORDER_SYMBOL)!=m_md.symbol) continue;
         ENUM_ORDER_TYPE t=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
         int d=(t==ORDER_TYPE_BUY_LIMIT || t==ORDER_TYPE_BUY_STOP || t==ORDER_TYPE_BUY_STOP_LIMIT) ? 1 : -1;
         if(direction==0 || d==direction) n++;
        }
      return n;
     }

   //--- server-day bookkeeping for the daily loss limit
   void              RollDay(void)
     {
      datetime today=CMarketData::BarStart(TimeTradeServer(),PERIOD_D1);
      if(today!=m_day)
        {
         m_day=today;
         m_day_start_balance=AccountInfoDouble(ACCOUNT_BALANCE);
        }
     }

   double            DayStartBalance(void) const { return m_day_start_balance; }

   //--- realised P&L of our deals today + floating P&L of our open positions
   double            DayPnL(void)
     {
      RollDay();
      double pnl=0;
      if(HistorySelect(m_day,TimeTradeServer()+60))
        {
         for(int i=HistoryDealsTotal()-1;i>=0;i--)
           {
            ulong d=HistoryDealGetTicket(i);
            if(d==0 || HistoryDealGetInteger(d,DEAL_MAGIC)!=m_magic || HistoryDealGetString(d,DEAL_SYMBOL)!=m_md.symbol) continue;
            pnl+=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);
           }
        }
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong tk=PositionGetTicket(i);
         if(tk==0 || PositionGetInteger(POSITION_MAGIC)!=m_magic || PositionGetString(POSITION_SYMBOL)!=m_md.symbol) continue;
         pnl+=PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP);
        }
      return pnl;
     }

   bool              DailyLimitHit(void)
     {
      double pnl=DayPnL();
      return pnl<=-m_cfg.daily_loss_limit_pct/100.0*m_day_start_balance;
     }

   //--- all account-level checks before placing a NEW order; reason in last_reason
   bool              CanOpenNew(void)
     {
      if(DailyLimitHit()) { last_reason="REJECT_DAILY_LOSS_LIMIT"; return false; }
      int pos=CountPositions(), pend=CountPending();
      if(!m_md.spec.hedging && (pos>0 || pend>0)) { last_reason="REJECT_NETTING_ONE_AT_A_TIME"; return false; }
      if(pos+pend>=m_cfg.max_positions) { last_reason="REJECT_MAX_POSITIONS"; return false; }
      if(OpenRiskPct()+m_cfg.risk_pct>m_cfg.max_total_risk_pct+1e-9) { last_reason="REJECT_TOTAL_RISK"; return false; }
      if(m_cfg.max_spread_points>0 && m_md.SpreadPoints()>m_cfg.max_spread_points) { last_reason="REJECT_SPREAD"; return false; }
      last_reason="OK";
      return true;
     }
  };

#endif
