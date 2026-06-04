"""SQLAlchemy ORM models for AgenticTrader."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Setting(Base):
    """Key/value app settings (risk profile, funds password hash, flags)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Instrument(Base):
    """A tradable NSE instrument."""

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    yf_symbol: Mapped[str | None] = mapped_column(String(40))  # e.g. RELIANCE.NS
    sector: Mapped[str | None] = mapped_column(String(64))
    index_membership: Mapped[str | None] = mapped_column(String(64))  # NIFTY50 / NIFTY100 ...
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class PriceBar(Base):
    """Daily OHLCV bar for an instrument."""

    __tablename__ = "price_bars"
    __table_args__ = (UniqueConstraint("instrument_id", "date", name="uq_price_bar"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    date: Mapped[dt.date] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)


class NewsItem(Base):
    """A news/RSS headline, optionally mapped to a symbol with sentiment."""

    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(80))
    symbol: Mapped[str | None] = mapped_column(String(32), index=True)
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)  # -1..1
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    hash: Mapped[str] = mapped_column(String(40), unique=True, index=True)


class Wallet(Base):
    """Single paper wallet (fake money)."""

    __tablename__ = "wallet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class FundEvent(Base):
    """Ledger of add/withdraw fund operations."""

    __tablename__ = "fund_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # deposit / withdrawal
    amount: Mapped[float] = mapped_column(Float)
    balance_after: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Order(Base):
    """A simulated order (always filled immediately in paper mode)."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(4))  # BUY / SELL
    qty: Mapped[int] = mapped_column(Integer)
    requested_price: Mapped[float] = mapped_column(Float)
    fill_price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(12), default="FILLED")
    reason: Mapped[str | None] = mapped_column(Text)  # rationale
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Trade(Base):
    """A realized round-trip or executed fill record for P&L tracking."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(4))
    qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Position(Base):
    """Current open holding per symbol (paper)."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    qty: Mapped[int] = mapped_column(Integer, default=0)
    avg_price: Mapped[float] = mapped_column(Float, default=0.0)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    take_profit: Mapped[float | None] = mapped_column(Float)
    last_price: Mapped[float | None] = mapped_column(Float)
    opened_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AgentRun(Base):
    """One execution of the autonomous supervisor loop."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    regime: Mapped[str | None] = mapped_column(String(32))
    candidates_scanned: Mapped[int] = mapped_column(Integer, default=0)
    actions_taken: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    briefing: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="running")

    signals: Mapped[list["Signal"]] = relationship(back_populates="run")


class Signal(Base):
    """A per-symbol scored signal produced during an agent run."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)  # -1..1 composite
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    trend: Mapped[str | None] = mapped_column(String(16))
    action: Mapped[str | None] = mapped_column(String(8))  # BUY/SELL/HOLD
    rationale: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    run: Mapped["AgentRun | None"] = relationship(back_populates="signals")


class Alert(Base):
    """User-facing alert/notification."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(12), default="info")  # info/success/warning/danger
    category: Mapped[str] = mapped_column(String(24), default="system")  # trade/funds/system/risk
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str | None] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, index=True)


class AuditLog(Base):
    """Append-only audit trail of significant decisions/actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(32), default="system")
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, index=True)
