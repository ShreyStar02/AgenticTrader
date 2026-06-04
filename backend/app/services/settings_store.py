"""App settings stored in the DB (risk profile, autonomous flag)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings as cfg
from app.models import Setting

RISK_KEY = "risk_profile"
AUTO_KEY = "autonomous_enabled"


def get_setting(db: Session, key: str, default: str) -> str:
    s = db.get(Setting, key)
    return s.value if s else default


def set_setting(db: Session, key: str, value: str) -> None:
    s = db.get(Setting, key)
    if s is None:
        db.add(Setting(key=key, value=value))
    else:
        s.value = value
    db.commit()


def get_risk_profile(db: Session) -> str:
    return get_setting(db, RISK_KEY, cfg.default_risk_profile)


def set_risk_profile(db: Session, profile: str) -> None:
    set_setting(db, RISK_KEY, profile)


def is_autonomous(db: Session) -> bool:
    return get_setting(db, AUTO_KEY, "true" if cfg.autonomous_enabled else "false") == "true"


def set_autonomous(db: Session, enabled: bool) -> None:
    set_setting(db, AUTO_KEY, "true" if enabled else "false")
