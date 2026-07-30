"""
Lightweight Telegram sender used directly by forexpro_main.py to push
per-follower alerts (e.g. "a provider you follow just posted a signal")
the moment they happen — this is deliberately separate from telegram_bot.py's
own polling loop, which handles slash commands (/signals, /prices, etc.) and
the older global broadcast-to-everyone alerts.

Needs the same TELEGRAM_BOT_TOKEN as telegram_bot.py — one bot, two senders.
"""
import os
import json
import urllib.request
import urllib.error
import secrets
import string

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "YourForexProBot")  # set to your @BotFather username


def telegram_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN)


def send_telegram_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    """Fire-and-forget send — never raises, just returns False on failure so a
    Telegram outage/misconfiguration can't break signal generation or copy trading."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id, "text": text, "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"[telegram] send failed for chat {chat_id}: {e}")
        return False


def generate_link_code() -> str:
    """Short, human-typeable code the user sends the bot as /start <code>."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def bot_deep_link(code: str) -> str:
    return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={code}"
