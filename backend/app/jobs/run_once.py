"""Run a single autonomous trading cycle (for GitHub Actions cron).

Usage:
    python -m app.jobs.run_once [--force]

Behaviour:
  * Ensures the DB exists and is seeded (idempotent).
  * Optionally seeds INITIAL_FUNDS once, so a fresh cloud DB is populated.
  * Skips trading outside NSE market hours unless --force is given
    (the dashboard snapshots are still refreshed by export_snapshots).
  * Pushes a Telegram summary when trades happen (if configured).
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.bootstrap import bootstrap
from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import session_scope
from app.models import FundEvent
from app.services import market_data, notify, wallet

log = get_logger("job.run_once")


def _seed_initial_funds(db) -> None:
    """Deposit INITIAL_FUNDS exactly once on a brand-new wallet."""
    if settings.initial_funds <= 0:
        return
    already = db.scalar(select(FundEvent).limit(1))
    if already is not None:
        return
    w = wallet.ensure_wallet(db)
    w.cash = round(w.cash + settings.initial_funds, 2)
    db.add(FundEvent(kind="deposit", amount=settings.initial_funds,
                     balance_after=w.cash, note="initial seed"))
    db.commit()
    log.info("Seeded initial funds: %.2f", settings.initial_funds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one autonomous trading cycle.")
    parser.add_argument("--force", action="store_true",
                        help="Run even if the market is closed / autonomous is paused.")
    args = parser.parse_args(argv)

    bootstrap()

    db = session_scope()
    try:
        _seed_initial_funds(db)

        if not args.force and not market_data.is_market_open():
            log.info("Market closed; skipping trade cycle (snapshots still refresh).")
            return 0

        from app.agents.supervisor import run_cycle

        result = run_cycle(db, force=args.force)
        if result.get("skipped"):
            log.info("Cycle skipped: %s", result.get("reason"))
            return 0

        log.info("Cycle done: %s", result.get("summary"))
        actions = result.get("actions", 0)
        if actions and notify.enabled():
            notify.send(
                "🤖 <b>AgenticTrader</b>\n"
                f"{actions} trade action(s) this cycle.\n"
                f"Regime: <b>{result.get('regime')}</b>\n"
                f"{result.get('summary', '')}"
            )
        return 0
    except Exception as e:  # noqa: BLE001
        log.exception("run_once failed: %s", e)
        if notify.enabled():
            notify.send(f"⚠️ AgenticTrader cycle failed: {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
