"""Pydantic request/response schemas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class FundRequest(BaseModel):
    amount: float = Field(gt=0)
    password: str
    note: str | None = None


class ResearchRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)


class WatchlistRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)


class WatchlistOut(BaseModel):
    symbols: list[str]


class ManualTradeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    qty: int = Field(gt=0)
    password: str


class WalletOut(BaseModel):
    cash: float
    currency: str


class FundEventOut(BaseModel):
    id: int
    kind: str
    amount: float
    balance_after: float
    note: str | None
    created_at: dt.datetime

    class Config:
        from_attributes = True


class HoldingOut(BaseModel):
    symbol: str
    qty: int
    avg_price: float
    last_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pct: float
    stop_loss: float | None = None
    take_profit: float | None = None


class PortfolioOut(BaseModel):
    cash: float
    invested: float
    market_value: float
    equity: float
    unrealized_pnl: float
    realized_pnl: float
    holdings: list[HoldingOut]


class AlertOut(BaseModel):
    id: int
    level: str
    category: str
    title: str
    message: str | None
    read: bool
    created_at: dt.datetime

    class Config:
        from_attributes = True


class SignalOut(BaseModel):
    id: int
    symbol: str
    score: float
    technical_score: float
    sentiment_score: float
    trend: str | None
    action: str | None
    rationale: str | None
    last_price: float | None = None
    details: dict | None = None
    created_at: dt.datetime

    class Config:
        from_attributes = True


class AgentRunOut(BaseModel):
    id: int
    started_at: dt.datetime
    finished_at: dt.datetime | None
    regime: str | None
    candidates_scanned: int
    actions_taken: int
    summary: str | None
    briefing: str | None
    status: str

    class Config:
        from_attributes = True


class TradeOut(BaseModel):
    id: int
    symbol: str
    side: str
    qty: int
    price: float
    fees: float
    realized_pnl: float
    created_at: dt.datetime

    class Config:
        from_attributes = True


class SettingsOut(BaseModel):
    risk_profile: str
    autonomous_enabled: bool
    scan_interval_minutes: int
    market_open: bool


class RiskProfileUpdate(BaseModel):
    risk_profile: str = Field(pattern="^(conservative|moderate|aggressive)$")


class AutonomousUpdate(BaseModel):
    enabled: bool


class NewsOut(BaseModel):
    title: str
    link: str | None
    source: str | None
    symbol: str | None
    sentiment: float
    published_at: dt.datetime | None

    class Config:
        from_attributes = True
