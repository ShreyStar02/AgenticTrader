"""Application bootstrap: DB init, seeding, and instrument population."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.universe import SECTOR_HINT, universe_for_profile
from app.db.session import Base, engine, session_scope
from app.models import Instrument
from app.services import wallet
from app.services.market_data import to_yf

log = get_logger("init")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    log.info("Database tables ensured")


def seed(db: Session) -> None:
    wallet.ensure_wallet(db)
    wallet.ensure_funds_password(db)
    _seed_instruments(db)


def _seed_instruments(db: Session) -> None:
    existing = db.scalar(select(Instrument).limit(1))
    if existing:
        return
    symbols = universe_for_profile("aggressive")  # widest set
    for sym in symbols:
        db.add(
            Instrument(
                symbol=sym,
                yf_symbol=to_yf(sym),
                sector=SECTOR_HINT.get(sym),
                index_membership="NIFTY50" if sym in universe_for_profile("moderate") else "EXTRA",
            )
        )
    db.commit()
    log.info("Seeded %d instruments", len(symbols))


def bootstrap() -> None:
    init_db()
    db = session_scope()
    try:
        seed(db)
    finally:
        db.close()
