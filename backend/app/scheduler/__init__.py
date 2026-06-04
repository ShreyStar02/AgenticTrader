"""Background scheduler running the autonomous supervisor loop."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.agents.supervisor import run_cycle
from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import session_scope

log = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _job() -> None:
    db = session_scope()
    try:
        result = run_cycle(db)
        if not result.get("skipped"):
            log.info("Cycle done: %s", result.get("summary"))
    except Exception as e:  # noqa: BLE001
        log.exception("Autonomous cycle failed: %s", e)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        _job,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="autonomous_cycle",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info("Scheduler started (every %d min)", settings.scan_interval_minutes)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")
