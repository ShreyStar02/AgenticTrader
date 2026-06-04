"""Paper wallet service: fake funds with password-authorized add/withdraw."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import FundEvent, Setting, Wallet

FUNDS_PWD_KEY = "funds_password_hash"


def ensure_wallet(db: Session) -> Wallet:
    wallet = db.scalar(select(Wallet).limit(1))
    if wallet is None:
        wallet = Wallet(cash=0.0, currency="INR")
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def ensure_funds_password(db: Session) -> None:
    """Seed the funds password hash from settings on first boot."""
    existing = db.get(Setting, FUNDS_PWD_KEY)
    if existing is None:
        db.add(Setting(key=FUNDS_PWD_KEY, value=hash_password(settings.funds_password)))
        db.commit()


def check_password(db: Session, plain: str) -> bool:
    s = db.get(Setting, FUNDS_PWD_KEY)
    if s is None:
        return False
    return verify_password(plain, s.value)


def get_balance(db: Session) -> float:
    return ensure_wallet(db).cash


def add_funds(db: Session, amount: float, password: str, note: str | None = None) -> Wallet:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if not check_password(db, password):
        raise PermissionError("Invalid system password")
    wallet = ensure_wallet(db)
    wallet.cash = round(wallet.cash + amount, 2)
    db.add(FundEvent(kind="deposit", amount=amount, balance_after=wallet.cash, note=note))
    db.commit()
    db.refresh(wallet)
    return wallet


def withdraw_funds(db: Session, amount: float, password: str, note: str | None = None) -> Wallet:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if not check_password(db, password):
        raise PermissionError("Invalid system password")
    wallet = ensure_wallet(db)
    if amount > wallet.cash:
        raise ValueError("Insufficient cash balance")
    wallet.cash = round(wallet.cash - amount, 2)
    db.add(FundEvent(kind="withdrawal", amount=amount, balance_after=wallet.cash, note=note))
    db.commit()
    db.refresh(wallet)
    return wallet


def debit(db: Session, amount: float) -> None:
    """Internal debit for a buy (no password; system-authorized)."""
    wallet = ensure_wallet(db)
    wallet.cash = round(wallet.cash - amount, 2)
    db.add(wallet)


def credit(db: Session, amount: float) -> None:
    """Internal credit for a sell (no password; system-authorized)."""
    wallet = ensure_wallet(db)
    wallet.cash = round(wallet.cash + amount, 2)
    db.add(wallet)
