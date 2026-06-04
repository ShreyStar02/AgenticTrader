"""Export the current DB state to static JSON snapshots for the dashboard.

These files are published to GitHub Pages and consumed by the React app when it
runs in static (read-only) mode. Shapes mirror the live API exactly, so the same
frontend works both locally (live API) and on Pages (static JSON).

Usage:
    python -m app.jobs.export_snapshots --out ../site/data
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from sqlalchemy import select

from app.bootstrap import bootstrap
from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import session_scope
from app.models import AgentRun, FundEvent, Signal, Trade
from app.schemas import (
    AgentRunOut,
    AlertOut,
    FundEventOut,
    SettingsOut,
    SignalOut,
    TradeOut,
    WalletOut,
)
from app.services import alerts, market_data, news, portfolio, settings_store, wallet, watchlist

log = get_logger("job.export")


def _write(out: Path, name: str, data) -> None:
    (out / name).write_text(json.dumps(data, default=str, ensure_ascii=False, indent=0),
                            encoding="utf-8")


def _dump_list(models, schema) -> list[dict]:
    return [schema.model_validate(m).model_dump(mode="json") for m in models]


def export(out_dir: str) -> None:
    bootstrap()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    db = session_scope()
    try:
        w = wallet.ensure_wallet(db)
        _write(out, "wallet.json", WalletOut(cash=w.cash, currency=w.currency).model_dump())

        prices = {p.symbol: (p.last_price or p.avg_price) for p in portfolio.list_positions(db)}
        _write(out, "portfolio.json", portfolio.portfolio_summary(db, prices))

        trades = db.scalars(select(Trade).order_by(Trade.created_at.desc()).limit(200)).all()
        _write(out, "trades.json", _dump_list(trades, TradeOut))

        alert_rows = alerts.list_alerts(db, limit=100)
        _write(out, "alerts.json", _dump_list(alert_rows, AlertOut))

        signals = db.scalars(
            select(Signal).order_by(Signal.created_at.desc()).limit(300)
        ).all()
        seen, deduped = set(), []
        for s in signals:
            if s.symbol in seen:
                continue
            seen.add(s.symbol)
            deduped.append(s)
        _write(out, "signals.json", _dump_list(deduped[:60], SignalOut))

        runs = db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(20)).all()
        _write(out, "runs.json", _dump_list(runs, AgentRunOut))

        fund_events = db.scalars(
            select(FundEvent).order_by(FundEvent.created_at.desc()).limit(100)
        ).all()
        _write(out, "funds_history.json", _dump_list(fund_events, FundEventOut))

        _write(out, "settings.json", SettingsOut(
            risk_profile=settings_store.get_risk_profile(db),
            autonomous_enabled=settings_store.is_autonomous(db),
            scan_interval_minutes=settings.scan_interval_minutes,
            market_open=market_data.is_market_open(),
        ).model_dump())

        _write(out, "watchlist.json", {"symbols": watchlist.get_watchlist(db)})

        try:
            news_items = news.fetch_market_news()[:30]
        except Exception as e:  # noqa: BLE001
            log.warning("News fetch failed during export: %s", e)
            news_items = []
        _write(out, "news.json", news_items)

        _write(out, "meta.json", {
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "market_open": market_data.is_market_open(),
            "mode": "static",
        })
        log.info("Snapshots written to %s", out.resolve())
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export DB state to JSON snapshots.")
    parser.add_argument("--out", default="../site/data", help="Output directory.")
    args = parser.parse_args(argv)
    export(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
