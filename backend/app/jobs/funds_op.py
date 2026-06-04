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
