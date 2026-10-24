//+------------------------------------------------------------------+
//| ExecutionManager.mqh - limit orders, cancellations, SL/TP         |
//| modifications and closes, with server-side verification.          |
//| An order is NEVER considered placed/executed because OrderSend    |
//| returned: retcodes are checked and the order/position is re-read. |
//+------------------------------------------------------------------+
#ifndef SENSITOR_EXECUTION_MQH
#define SENSITOR_EXECUTION_MQH

#include "MarketData.mqh"
#include "TradeLogger.mqh"

enum ENUM_SAI_SEND_RESULT { SEND_OK=0, SEND_RETRY=1, SEND_FAILED=2, SEND_UNKNOWN=3 };

class CExecutionManager
  {
private:
   CMarketData      *m_md;
   CTradeLogger     *m_log;
   long              m_magic;
   int               m_deviation;
   bool              m_dry_run;

public:
   int               consecutive_errors;
   uint              last_retcode;
   string            last_error;

   void              Init(CMarketData *md,CTradeLogger *log,const long magic,const int deviation_points,const bool dry_run)
     {
      m_md=md; m_log=log; m_magic=magic; m_deviation=deviation_points; m_dry_run=dry_run;
      consecutive_errors=0; last_retcode=0; last_error="";
     }

   static string     CommentFor(const string setup_id) { return SAI_COMMENT_PREFIX+setup_id; }
   static string     SetupFromComment(const string c)
     {
      if(StringFind(c,SAI_COMMENT_PREFIX)!=0) return "";
      string rest=StringSubstr(c,StringLen(SAI_COMMENT_PREFIX));
      int sp=StringFind(rest," ");                     // brokers may append text such as "[sl 123]"
      return sp>0 ? StringSubstr(rest,0,sp) : rest;
     }

   double            Norm(const double p) const { return NormalizeDouble(MathRound(p/m_md.spec.tick_size)*m_md.spec.tick_size,m_md.spec.digits); }

   static bool       IsSuccess(const uint rc) { return rc==TRADE_RETCODE_DONE || rc==TRADE_RETCODE_PLACED || rc==TRADE_RETCODE_DONE_PARTIAL; }
   static bool       IsTransient(const uint rc)
     {
      return rc==TRADE_RETCODE_REQUOTE || rc==TRADE_RETCODE_PRICE_CHANGED || rc==TRADE_RETCODE_PRICE_OFF ||
             rc==TRADE_RETCODE_TIMEOUT || rc==TRADE_RETCODE_CONNECTION || rc==TRADE_RETCODE_TOO_MANY_REQUESTS ||
             rc==TRADE_RETCODE_LOCKED || rc==TRADE_RETCODE_ORDER_CHANGED || rc==TRADE_RETCODE_SERVER_DISABLES_AT ||
             rc==TRADE_RETCODE_CLIENT_DISABLES_AT;
     }
   static bool       IsUncertain(const uint rc) { return rc==TRADE_RETCODE_TIMEOUT || rc==TRADE_RETCODE_CONNECTION; }

   //--- filling modes to try, most preferred first
   int               FillingCandidates(const bool pending,ENUM_ORDER_TYPE_FILLING &out[]) const
     {
      ArrayResize(out,0);
      long f=m_md.spec.filling_flags;
      if(pending) Add(out,ORDER_FILLING_RETURN);
      if((f&SYMBOL_FILLING_FOK)!=0) Add(out,ORDER_FILLING_FOK);
      if((f&SYMBOL_FILLING_IOC)!=0) Add(out,ORDER_FILLING_IOC);
      if(!pending) Add(out,ORDER_FILLING_RETURN);
      return ArraySize(out);
     }

   //--- find our live pending order for a setup (idempotency)
   ulong             FindOrder(const string setup_id) const
     {
      for(int i=OrdersTotal()-1;i>=0;i--)
        {
         ulong tk=OrderGetTicket(i);
         if(tk==0 || OrderGetInteger(ORDER_MAGIC)!=m_magic || OrderGetString(ORDER_SYMBOL)!=m_md.symbol) continue;
         if(SetupFromComment(OrderGetString(ORDER_COMMENT))==setup_id) return tk;
        }
      return 0;
     }

   //--- was an order for this setup already sent at some point (history since `from`)?
   bool              EverSent(const string setup_id,const datetime from) const
     {
      if(FindOrder(setup_id)>0) return true;
      if(!HistorySelect(from-86400,TimeTradeServer()+86400)) return false;
      for(int i=HistoryOrdersTotal()-1;i>=0;i--)
        {
         ulong tk=HistoryOrderGetTicket(i);
         if(tk==0 || HistoryOrderGetInteger(tk,ORDER_MAGIC)!=m_magic) continue;
         if(SetupFromComment(HistoryOrderGetString(tk,ORDER_COMMENT))==setup_id) return true;
        }
      return false;
     }

   //--- place a limit order; returns SEND_OK with ticket, or a classified failure
   ENUM_SAI_SEND_RESULT PlaceLimit(const string setup_id,const int direction,const double volume,const double price,
                                   const double sl,const double tp,ulong &ticket)
     {
      ticket=0;
      double p=Norm(price), s=Norm(sl), t=(tp>0 ? Norm(tp) : 0.0);
      double bid=m_md.Bid(), ask=m_md.Ask();
      double min_dist=m_md.spec.stops_level*m_md.spec.point;
      //--- a limit order must rest on the passive side of the market: never chase [U]
      if(direction>0 && p>ask-min_dist) { last_error="PRICE_THROUGH_ENTRY"; return SEND_FAILED; }
      if(direction<0 && p<bid+min_dist) { last_error="PRICE_THROUGH_ENTRY"; return SEND_FAILED; }
      if(MathAbs(p-s)<min_dist || (t>0 && MathAbs(t-p)<min_dist)) { last_error="STOPS_TOO_CLOSE"; return SEND_FAILED; }
      if(FindOrder(setup_id)>0) { last_error="DUPLICATE"; return SEND_FAILED; }

      MqlTradeRequest rq; MqlTradeResult rs; MqlTradeCheckResult ck;
      ZeroMemory(rq); ZeroMemory(rs);
      rq.action=TRADE_ACTION_PENDING;
      rq.symbol=m_md.symbol;
      rq.volume=volume;
      rq.type=(direction>0) ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
      rq.price=p; rq.sl=s; rq.tp=t;
      rq.magic=m_magic;
      rq.comment=CommentFor(setup_id);
      rq.deviation=m_deviation;
      if((m_md.spec.expiration_flags&SYMBOL_EXPIRATION_GTC)!=0) rq.type_time=ORDER_TIME_GTC;
      else if((m_md.spec.expiration_flags&SYMBOL_EXPIRATION_DAY)!=0) rq.type_time=ORDER_TIME_DAY;   // re-placed daily by reconciliation
      else rq.type_time=ORDER_TIME_GTC;
      if(m_dry_run)
        {
         rs.retcode=TRADE_RETCODE_PLACED;
         m_log.Order("PLACE_LIMIT_DRYRUN",setup_id,rq,rs,"dry-run: not sent");
         return SEND_OK;
        }
      ENUM_ORDER_TYPE_FILLING fills[];
      FillingCandidates(true,fills);
      bool checked=false;
      for(int i=0;i<ArraySize(fills);i++)
        {
         rq.type_filling=fills[i];
         ZeroMemory(ck);
         if(OrderCheck(rq,ck)) { checked=true; break; }
         if(ck.retcode!=TRADE_RETCODE_INVALID_FILL) break;
        }
      if(!checked)
        {
         rs.retcode=ck.retcode; rs.comment=ck.comment;
         m_log.Order("PLACE_LIMIT_CHECK_FAIL",setup_id,rq,rs,"OrderCheck rejected");
         last_retcode=ck.retcode; last_error=ck.comment;
         Fail();
         return IsTransient(ck.retcode) ? SEND_RETRY : SEND_FAILED;
        }
      ResetLastError();
      bool sent=OrderSend(rq,rs);
      last_retcode=rs.retcode;
      m_log.Order("PLACE_LIMIT",setup_id,rq,rs,sent ? "" : StringFormat("OrderSend false err=%d",GetLastError()));
      if(IsSuccess(rs.retcode) && rs.order>0)
        {
         //--- verify on the server side (the order may already have been filled)
         if(OrderSelect(rs.order) || HistoryOrderSelect(rs.order))
           {
            ticket=rs.order; consecutive_errors=0;
            return SEND_OK;
           }
         ticket=rs.order;
         return SEND_UNKNOWN;
        }
      if(IsUncertain(rs.retcode))
        {
         ulong found=FindOrder(setup_id);
         if(found>0) { ticket=found; consecutive_errors=0; return SEND_OK; }
         Fail();
         return SEND_UNKNOWN;
        }
      last_error=rs.comment;
      Fail();
      return IsTransient(rs.retcode) ? SEND_RETRY : SEND_FAILED;
     }

   bool              Cancel(const ulong ticket,const string setup_id,const string reason)
     {
      if(m_dry_run) return true;
      if(!OrderSelect(ticket)) return true;           // already gone (filled, expired or deleted)
      MqlTradeRequest rq; MqlTradeResult rs;
      ZeroMemory(rq); ZeroMemory(rs);
      rq.action=TRADE_ACTION_REMOVE;
      rq.order=ticket;
      bool sent=OrderSend(rq,rs);
      m_log.Order("CANCEL",setup_id,rq,rs,reason);
      if(IsSuccess(rs.retcode) || !OrderSelect(ticket)) { consecutive_errors=0; return true; }
      last_retcode=rs.retcode; last_error=rs.comment;
      Fail();
      return false;
     }

   //--- modify SL/TP of a position, honouring stops & freeze levels; verified on the server
   bool              ModifyPosition(const ulong ticket,const string setup_id,const double sl,const double tp,const string why)
     {
      if(!PositionSelectByTicket(ticket)) { last_error="position not found"; return false; }
      double s=(sl>0 ? Norm(sl) : 0.0), t=(tp>0 ? Norm(tp) : 0.0);
      double cur_sl=PositionGetDouble(POSITION_SL), cur_tp=PositionGetDouble(POSITION_TP);
      if(MathAbs(s-cur_sl)<m_md.spec.tick_size/2 && MathAbs(t-cur_tp)<m_md.spec.tick_size/2) return true;
      bool buy=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
      double px=buy ? m_md.Bid() : m_md.Ask();
      double stops=m_md.spec.stops_level*m_md.spec.point, freeze=m_md.spec.freeze_level*m_md.spec.point;
      if(s>0 && ((buy && px-s<stops) || (!buy && s-px<stops))) { last_error="SL_TOO_CLOSE_STOPS_LEVEL"; return false; }
      if(freeze>0 && ((cur_sl>0 && MathAbs(px-cur_sl)<=freeze) || (cur_tp>0 && MathAbs(px-cur_tp)<=freeze)))
        { last_error="FREEZE_LEVEL"; return false; }
      if(m_dry_run) return true;
      MqlTradeRequest rq; MqlTradeResult rs;
      ZeroMemory(rq); ZeroMemory(rs);
      rq.action=TRADE_ACTION_SLTP;
      rq.symbol=m_md.symbol;
      rq.position=ticket;
      rq.sl=s; rq.tp=t;
      rq.magic=m_magic;
      bool sent=OrderSend(rq,rs);
      m_log.Order("MODIFY_SLTP",setup_id,rq,rs,why);
      if(!IsSuccess(rs.retcode)) { last_retcode=rs.retcode; last_error=rs.comment; Fail(); return false; }
      //--- confirm with the server
      if(!PositionSelectByTicket(ticket)) return false;
      bool ok=MathAbs(PositionGetDouble(POSITION_SL)-s)<m_md.spec.tick_size/2 &&
              MathAbs(PositionGetDouble(POSITION_TP)-t)<m_md.spec.tick_size/2;
      if(ok) consecutive_errors=0; else last_error="modification not reflected by the server";
      return ok;
     }

   //--- market close of `volume` of a position (partial or full); verified by volume change
   bool              ClosePosition(const ulong ticket,const string setup_id,const double volume,const string why,double &fill_price)
     {
      fill_price=0;
      if(!PositionSelectByTicket(ticket)) { last_error="position not found"; return false; }
      double before=PositionGetDouble(POSITION_VOLUME);
      bool buy=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
      if(m_dry_run) { fill_price=buy ? m_md.Bid() : m_md.Ask(); return true; }
      MqlTradeRequest rq; MqlTradeResult rs;
      ZeroMemory(rq); ZeroMemory(rs);
      rq.action=TRADE_ACTION_DEAL;
      rq.symbol=m_md.symbol;
      rq.position=ticket;
      rq.volume=MathMin(volume,before);
      rq.type=buy ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      rq.price=buy ? m_md.Bid() : m_md.Ask();
      rq.deviation=m_deviation;
      rq.magic=m_magic;
      rq.comment=CommentFor(setup_id);
      ENUM_ORDER_TYPE_FILLING fills[];
      FillingCandidates(false,fills);
      bool sent=false;
      for(int i=0;i<ArraySize(fills);i++)
        {
         rq.type_filling=fills[i];
         ZeroMemory(rs);
         sent=OrderSend(rq,rs);
         if(rs.retcode!=TRADE_RETCODE_INVALID_FILL) break;
        }
      m_log.Order("CLOSE",setup_id,rq,rs,why);
      if(!IsSuccess(rs.retcode)) { last_retcode=rs.retcode; last_error=rs.comment; Fail(); return false; }
      fill_price=rs.price;
      double after=PositionSelectByTicket(ticket) ? PositionGetDouble(POSITION_VOLUME) : 0.0;
      bool ok=(after<before-m_md.spec.vol_step/2);
      if(ok) consecutive_errors=0; else last_error="volume unchanged after close";
      return ok;
     }

private:
   static void       Add(ENUM_ORDER_TYPE_FILLING &arr[],const ENUM_ORDER_TYPE_FILLING f)
     {
      for(int i=0;i<ArraySize(arr);i++) if(arr[i]==f) return;
      int n=ArraySize(arr); ArrayResize(arr,n+1); arr[n]=f;
     }
   void              Fail(void) { consecutive_errors++; }
  };

#endif
