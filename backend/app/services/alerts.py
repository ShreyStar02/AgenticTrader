"""Alerts and audit logging helpers."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models import Alert, AuditLog

log = get_logger("alerts")


def push_alert(
    db: Session,
    title: str,
    message: str | None = None,
    level: str = "info",
    category: str = "system",
) -> Alert:
    alert = Alert(title=title, message=message, level=level, category=category)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    log.info("ALERT[%s/%s] %s", category, level, title)
    return alert


def audit(db: Session, action: str, detail: str | None = None, actor: str = "system") -> None:
    db.add(AuditLog(actor=actor, action=action, detail=detail))
    db.commit()


def list_alerts(db: Session, limit: int = 50, unread_only: bool = False) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if unread_only:
        stmt = select(Alert).where(Alert.read.is_(False)).order_by(Alert.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def mark_all_read(db: Session) -> int:
    alerts = db.scalars(select(Alert).where(Alert.read.is_(False))).all()
    for a in alerts:
        a.read = True
    db.commit()
    return len(alerts)
