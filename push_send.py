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


DEFAULT_NOTIF_CATEGORIES = {
    "signal": True, "copy": True, "billing": True,
    "system": True, "education": True, "trade_closed": True,
}


def get_notification_prefs(db, user_id: int) -> dict:
    row = db.execute("SELECT categories FROM user_notification_prefs WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return dict(DEFAULT_NOTIF_CATEGORIES)
    try:
        return {**DEFAULT_NOTIF_CATEGORIES, **json.loads(row["categories"] or "{}")}
    except Exception:
        return dict(DEFAULT_NOTIF_CATEGORIES)


def should_push(db, user_id: int, category: str) -> bool:
    """Per-category push gate. Push used to be all-or-nothing (one browser
    permission covering every event); this lets a user mute, say, education
    pushes while keeping trade-close/copy alerts on. The in-app bell
    notification is unaffected either way — only the push half is gated."""
    prefs = get_notification_prefs(db, user_id)
    return bool(prefs.get(category, True))


def push_to_user(db, user_id: int, title: str, body: str, url: str = "/") -> None:
    """Push to every device/browser this user has installed the PWA on. Dead
    subscriptions (expired/uninstalled) get cleaned up automatically.
    Shared here (not just in forexpro_main.py) so mpesa.py, bridge.py, and
    payments.py can push too — those events (deposit confirmed, MT5 fill,
    withdrawal sent, etc.) were previously silent: an in-app notification
    row was written but no push ever fired for them."""
    if not push_configured():
        return
    subs = db.execute("SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id=?",
                       (user_id,)).fetchall()
    for s in subs:
        ok = send_push(
            {"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}},
            title, body, url)
        if not ok:
            db.execute("DELETE FROM push_subscriptions WHERE id=?", (s["id"],))


def notify_user(db, user_id: int, type_: str, title: str, message: str, url: str = "/", push: bool = True) -> None:
    """Single entry point for a user-facing event: writes the in-app
    notification row AND fires a real push notification in one call (subject
    to the user's per-category push preference — the in-app row always
    happens regardless). Prefer this over a bare `INSERT INTO notifications`
    so new events can't silently skip push the way several did before."""
    db.execute("INSERT INTO notifications (user_id,type,title,message) VALUES (?,?,?,?)",
               (user_id, type_, title, message))
    if push and should_push(db, user_id, type_):
        push_to_user(db, user_id, title, message, url)
