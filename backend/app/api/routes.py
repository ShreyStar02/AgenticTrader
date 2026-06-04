"""FastAPI route definitions."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import AgentRun, FundEvent, Signal, Trade
from app.schemas import (
    AgentRunOut,
    AlertOut,
    AutonomousUpdate,
    FundEventOut,
    FundRequest,
    ManualTradeRequest,
    PortfolioOut,
    ResearchRequest,
    RiskProfileUpdate,
    SettingsOut,
    SignalOut,
    TradeOut,
    WalletOut,
    WatchlistOut,
    WatchlistRequest,
)
from app.services import (
    alerts,
    market_data,
    news,
    portfolio,
    research,
    settings_store,
    trading,
    wallet,
    watchlist,
)

router = APIRouter()


# --------------------------- Funds ---------------------------
@router.get("/wallet", response_model=WalletOut)
def get_wallet(db: Session = Depends(get_db)):
    w = wallet.ensure_wallet(db)
    return WalletOut(cash=w.cash, currency=w.currency)


@router.post("/funds/add", response_model=WalletOut)
def add_funds(req: FundRequest, db: Session = Depends(get_db)):
    try:
        w = wallet.add_funds(db, req.amount, req.password, req.note)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    alerts.push_alert(db, f"Funds added: ₹{req.amount:.2f}",
                      message=f"New balance ₹{w.cash:.2f}", level="success", category="funds")
    return WalletOut(cash=w.cash, currency=w.currency)


@router.post("/funds/withdraw", response_model=WalletOut)
def withdraw_funds(req: FundRequest, db: Session = Depends(get_db)):
    try:
        w = wallet.withdraw_funds(db, req.amount, req.password, req.note)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    alerts.push_alert(db, f"Funds withdrawn: ₹{req.amount:.2f}",
                      message=f"New balance ₹{w.cash:.2f}", level="info", category="funds")
    return WalletOut(cash=w.cash, currency=w.currency)


@router.get("/funds/history", response_model=list[FundEventOut])
def funds_history(db: Session = Depends(get_db)):
    return list(db.scalars(select(FundEvent).order_by(FundEvent.created_at.desc()).limit(100)))


# --------------------------- Portfolio ---------------------------
@router.get("/portfolio", response_model=PortfolioOut)
def get_portfolio(db: Session = Depends(get_db)):
    prices = {p.symbol: (p.last_price or p.avg_price) for p in portfolio.list_positions(db)}
    return portfolio.portfolio_summary(db, prices)


@router.get("/trades", response_model=list[TradeOut])
def get_trades(db: Session = Depends(get_db)):
    return list(db.scalars(select(Trade).order_by(Trade.created_at.desc()).limit(200)))


# --------------------------- Alerts ---------------------------
@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(unread_only: bool = False, db: Session = Depends(get_db)):
    return alerts.list_alerts(db, limit=100, unread_only=unread_only)


@router.post("/alerts/read-all")
def read_all_alerts(db: Session = Depends(get_db)):
    return {"marked_read": alerts.mark_all_read(db)}


# --------------------------- Signals / Runs ---------------------------
def _dedup_latest(rows):
    """Keep only the most recent signal per symbol (rows must be newest-first)."""
    seen, out = set(), []
    for r in rows:
        if r.symbol in seen:
            continue
        seen.add(r.symbol)
        out.append(r)
    return out


@router.get("/signals", response_model=list[SignalOut])
def get_signals(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Signal).order_by(Signal.created_at.desc()).limit(max(limit * 5, 250))
    )
    return _dedup_latest(list(rows))[:limit]


@router.get("/runs", response_model=list[AgentRunOut])
def get_runs(limit: int = 20, db: Session = Depends(get_db)):
    return list(db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)))


@router.post("/agent/run-now")
def run_now(db: Session = Depends(get_db)):
    from app.agents.supervisor import run_cycle

    return run_cycle(db, force=True)


# --------------------------- Research / Watchlist ---------------------------
@router.post("/research")
def research_symbol_ep(req: ResearchRequest, db: Session = Depends(get_db)):
    result = research.research_symbol(db, req.symbol)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No market data found for '{req.symbol.upper()}'. Check the NSE symbol.",
        )
    return result


@router.get("/watchlist", response_model=WatchlistOut)
def get_watchlist_ep(db: Session = Depends(get_db)):
    return WatchlistOut(symbols=watchlist.get_watchlist(db))


@router.post("/watchlist/add", response_model=WatchlistOut)
def watchlist_add_ep(req: WatchlistRequest, db: Session = Depends(get_db)):
    symbols = watchlist.add_to_watchlist(db, req.symbol)
    alerts.push_alert(db, f"Added {req.symbol.upper()} to watchlist",
                      level="info", category="system")
    return WatchlistOut(symbols=symbols)


@router.post("/watchlist/remove", response_model=WatchlistOut)
def watchlist_remove_ep(req: WatchlistRequest, db: Session = Depends(get_db)):
    symbols = watchlist.remove_from_watchlist(db, req.symbol)
    return WatchlistOut(symbols=symbols)


# --------------------------- Manual trading ---------------------------
@router.post("/trade/buy")
def manual_buy_ep(req: ManualTradeRequest, db: Session = Depends(get_db)):
    try:
        return trading.manual_buy(db, req.symbol, req.qty, req.password)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/trade/sell")
def manual_sell_ep(req: ManualTradeRequest, db: Session = Depends(get_db)):
    try:
        return trading.manual_sell(db, req.symbol, req.qty, req.password)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --------------------------- News ---------------------------
@router.get("/news")
def get_news():
    items = news.fetch_market_news()[:30]
    return items


# --------------------------- Settings ---------------------------
@router.get("/settings", response_model=SettingsOut)
def get_settings_ep(db: Session = Depends(get_db)):
    return SettingsOut(
        risk_profile=settings_store.get_risk_profile(db),
        autonomous_enabled=settings_store.is_autonomous(db),
        scan_interval_minutes=settings.scan_interval_minutes,
        market_open=market_data.is_market_open(),
    )


@router.put("/settings/risk")
def set_risk(req: RiskProfileUpdate, db: Session = Depends(get_db)):
    settings_store.set_risk_profile(db, req.risk_profile)
    alerts.push_alert(db, f"Risk profile set to {req.risk_profile}", level="info",
                      category="system")
    return {"risk_profile": req.risk_profile}


@router.put("/settings/autonomous")
def set_autonomous(req: AutonomousUpdate, db: Session = Depends(get_db)):
    settings_store.set_autonomous(db, req.enabled)
    alerts.push_alert(db, f"Autonomous trading {'enabled' if req.enabled else 'paused'}",
                      level="info", category="system")
    return {"autonomous_enabled": req.enabled}


@router.get("/health")
def health():
    return {"status": "ok", "time": dt.datetime.now(dt.timezone.utc).isoformat()}
