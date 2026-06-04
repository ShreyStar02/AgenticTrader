"""Optional push notifications via Telegram (free).

Enabled only when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set (e.g. as
GitHub Actions secrets). Uses the stdlib so no extra dependency is required.
Every call is best-effort: failures are logged and swallowed so they can never
break a trading cycle.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger("notify")


def enabled() -> bool:
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)


def send(text: str) -> bool:
    """Send a Telegram message. Returns True on success, False otherwise."""
    if not enabled():
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": settings.telegram_chat_id,
            "text": text[:4000],
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            body = json.loads(resp.read().decode())
            if not body.get("ok"):
                log.warning("Telegram API returned not-ok: %s", body)
                return False
            return True
    except Exception as e:  # noqa: BLE001
        log.warning("Telegram notification failed: %s", e)
        return False
