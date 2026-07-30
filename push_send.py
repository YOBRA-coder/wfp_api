"""
Web Push notifications for the installed PWA — this is what lets the app
notify you even when it's not open in a tab, the same way a native app would.
Uses VAPID (no third-party push service account needed, works with any
browser's built-in push service).

Generate your own key pair once with:
    python3 -c "from py_vapid import Vapid02; v=Vapid02(); v.generate_keys(); ..."
(see backend/.env.example for the exact snippet) and set VAPID_PUBLIC_KEY /
VAPID_PRIVATE_KEY — never reuse the example pair checked into this repo for
a real deployment.
"""
import os
import json
from pywebpush import webpush, WebPushException

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:support@yobbytech.com")


def push_configured() -> bool:
    return bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)


def send_push(subscription_info: dict, title: str, body: str, url: str = "/") -> bool:
    """Fire-and-forget — never raises. A dead/expired subscription just returns
    False (caller should delete it; see forexpro_main.py push endpoints)."""
    if not push_configured():
        return False
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
        )
        return True
    except WebPushException as e:
        print(f"[push] send failed: {e}")
        return False
    except Exception as e:
        print(f"[push] unexpected error: {e}")
        return False
