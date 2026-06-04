"""Watchlist service: user-pinned symbols, stored as JSON in the settings table.

Watchlist symbols are always evaluated each agent cycle (so they produce signals
and become eligible for autonomous buys) and can be researched/added on demand.
No schema change — reuses the existing key/value `settings` table so the cloud
`state` DB stays compatible.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.services import settings_store

WATCHLIST_KEY = "watchlist"


def _norm(symbol: str) -> str:
    return symbol.strip().upper()


def get_watchlist(db: Session) -> list[str]:
    raw = settings_store.get_setting(db, WATCHLIST_KEY, "[]")
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(s).upper() for s in data]
    except (ValueError, TypeError):
        pass
    return []


def _save(db: Session, symbols: list[str]) -> None:
    # De-dupe preserving order.
    seen: list[str] = []
    for s in symbols:
        u = _norm(s)
        if u and u not in seen:
            seen.append(u)
    settings_store.set_setting(db, WATCHLIST_KEY, json.dumps(seen))


def add_to_watchlist(db: Session, symbol: str) -> list[str]:
    symbols = get_watchlist(db)
    symbols.append(_norm(symbol))
    _save(db, symbols)
    return get_watchlist(db)


def remove_from_watchlist(db: Session, symbol: str) -> list[str]:
    target = _norm(symbol)
    symbols = [s for s in get_watchlist(db) if s != target]
    _save(db, symbols)
    return get_watchlist(db)
