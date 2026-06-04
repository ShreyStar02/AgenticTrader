"""Manual management operations for the unattended deployment.

Triggered by the 'manage' GitHub Actions workflow (workflow_dispatch) so you can
add/withdraw paper funds or change settings without a live backend.

Usage:
    python -m app.jobs.funds_op add --amount 1000 --password trade123
    python -m app.jobs.funds_op withdraw --amount 200 --password trade123
    python -m app.jobs.funds_op set-risk --value moderate
    python -m app.jobs.funds_op set-autonomous --value true
"""
from __future__ import annotations

import argparse
import sys

from app.bootstrap import bootstrap
from app.core.logging_config import get_logger
from app.db.session import session_scope
from app.services import alerts, notify, settings_store, wallet

log = get_logger("job.funds_op")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage funds/settings.")
    sub = parser.add_subparsers(dest="op", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("--amount", type=float, required=True)
    p_add.add_argument("--password", required=True)
    p_add.add_argument("--note", default="via workflow")

    p_wd = sub.add_parser("withdraw")
    p_wd.add_argument("--amount", type=float, required=True)
    p_wd.add_argument("--password", required=True)
    p_wd.add_argument("--note", default="via workflow")

    p_risk = sub.add_parser("set-risk")
    p_risk.add_argument("--value", required=True,
                        choices=["conservative", "moderate", "aggressive"])

    p_auto = sub.add_parser("set-autonomous")
    p_auto.add_argument("--value", required=True, choices=["true", "false"])

    p_research = sub.add_parser("research")
    p_research.add_argument("--symbol", required=True)

    p_wl_add = sub.add_parser("watchlist-add")
    p_wl_add.add_argument("--symbol", required=True)

    p_wl_rm = sub.add_parser("watchlist-remove")
    p_wl_rm.add_argument("--symbol", required=True)

    p_buy = sub.add_parser("buy")
    p_buy.add_argument("--symbol", required=True)
    p_buy.add_argument("--amount", type=float, required=True, help="Quantity (whole shares)")
    p_buy.add_argument("--password", required=True)

    p_sell = sub.add_parser("sell")
    p_sell.add_argument("--symbol", required=True)
    p_sell.add_argument("--amount", type=float, required=True, help="Quantity (whole shares)")
    p_sell.add_argument("--password", required=True)

    args = parser.parse_args(argv)

    bootstrap()
    db = session_scope()
    try:
        if args.op == "add":
            w = wallet.add_funds(db, args.amount, args.password, args.note)
            alerts.push_alert(db, f"Funds added: {args.amount:.2f}",
                              message=f"New balance {w.cash:.2f}", level="success",
                              category="funds")
            notify.send(f"💰 Funds added: ₹{args.amount:.2f}. Balance ₹{w.cash:.2f}")
            print(f"OK add. Balance={w.cash:.2f}")

        elif args.op == "withdraw":
            w = wallet.withdraw_funds(db, args.amount, args.password, args.note)
            alerts.push_alert(db, f"Funds withdrawn: {args.amount:.2f}",
                              message=f"New balance {w.cash:.2f}", level="info",
                              category="funds")
            notify.send(f"🏧 Funds withdrawn: ₹{args.amount:.2f}. Balance ₹{w.cash:.2f}")
            print(f"OK withdraw. Balance={w.cash:.2f}")

        elif args.op == "set-risk":
            settings_store.set_risk_profile(db, args.value)
            alerts.push_alert(db, f"Risk profile set to {args.value}", category="system")
            print(f"OK risk={args.value}")

        elif args.op == "set-autonomous":
            enabled = args.value == "true"
            settings_store.set_autonomous(db, enabled)
            alerts.push_alert(db, f"Autonomous trading {'enabled' if enabled else 'paused'}",
                              category="system")
            print(f"OK autonomous={enabled}")

        elif args.op == "research":
            from app.services import research

            res = research.research_symbol(db, args.symbol)
            if res is None:
                print(f"ERROR: no data for {args.symbol}", file=sys.stderr)
                return 3
            alerts.push_alert(db, f"Research ready: {res['symbol']}",
                              message=f"Score {res['score']:.2f} ({res['action']}). Open the Signals tab to view its chart & details.",
                              level="success", category="system")
            print(f"OK research {res['symbol']} score={res['score']:.2f}")

        elif args.op == "watchlist-add":
            from app.services import watchlist

            syms = watchlist.add_to_watchlist(db, args.symbol)
            alerts.push_alert(db, f"Added {args.symbol.upper()} to watchlist",
                              category="system")
            print(f"OK watchlist-add. {len(syms)} symbols")

        elif args.op == "watchlist-remove":
            from app.services import watchlist

            syms = watchlist.remove_from_watchlist(db, args.symbol)
            print(f"OK watchlist-remove. {len(syms)} symbols")

        elif args.op == "buy":
            from app.services import trading

            res = trading.manual_buy(db, args.symbol, int(args.amount), args.password)
            alerts.push_alert(db, f"Manual buy: {res['symbol']} x{res['qty']}",
                              message=f"@ {res['price']:.2f}", level="success",
                              category="trade")
            notify.send(f"🟢 Manual BUY {res['symbol']} x{res['qty']} @ ₹{res['price']:.2f}")
            print(f"OK buy {res['symbol']} x{res['qty']} @ {res['price']:.2f}")

        elif args.op == "sell":
            from app.services import trading

            res = trading.manual_sell(db, args.symbol, int(args.amount), args.password)
            alerts.push_alert(db, f"Manual sell: {res['symbol']} x{res['qty']}",
                              message=f"@ {res['price']:.2f}", level="info",
                              category="trade")
            notify.send(f"🔴 Manual SELL {res['symbol']} x{res['qty']} @ ₹{res['price']:.2f}")
            print(f"OK sell {res['symbol']} x{res['qty']} @ {res['price']:.2f}")

        return 0
    except PermissionError as e:
        print(f"DENIED: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
