"""
ForexPro API — Complete Backend
Routes: /auth, /signals, /copy, /providers, /education, /journal, /prices, /ws
DB: SQLite (forexpro.db)
"""
from fastapi import FastAPI, Query, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import json, time, asyncio
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARN] python-dotenv not installed — relying on real environment variables only. "
          "Run: pip install python-dotenv --break-system-packages")

from database import get_db, init_db, hash_password, verify_password, is_subscription_active, recompute_provider_stats, plan_limits, effective_plan
from signals import (get_ohlcv, add_indicators, build_signal, get_live_quote,
                     PAIR_CONFIG, TF_MAP, detect_support_resistance,
                     detect_trendline, build_markers, pip_value_usd, compute_margin_usd, run_backtest,
                     compute_risk_based_lot, _low_liquidity_window, to_unix_utc)
from payments import router as payments_router
from mpesa import router as mpesa_router
from bridge import router as bridge_router, check_stale_bridges
from prefs import router as prefs_router
from news import router as news_router
import pandas as pd
import time
       

app = FastAPI(title="ForexPro API", version="4.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from auth import create_token, decode_token, get_current_user, get_optional_user, security
from telegram_send import send_telegram_message, generate_link_code, bot_deep_link, telegram_configured
from push_send import send_push, push_configured, VAPID_PUBLIC_KEY, push_to_user, notify_user
from email_send import send_email, send_verification_email, send_password_reset_otp_email, email_configured
import secrets

# ── Pydantic Models ───────────────────────────────────────────────────────────
class RegisterReq(BaseModel):
    email: str; username: str; password: str

class LoginReq(BaseModel):
    email: str; password: str

class ForgotPasswordReq(BaseModel):
    email: str

class ResetPasswordReq(BaseModel):
    email: str; otp: str; new_password: str

class GenerateSignalReq(BaseModel):
    pair: str = "EURUSD"; timeframe: str = "H1"

class ManualSignalReq(BaseModel):
    pair: str
    timeframe: str = "H1"
    direction: str          # BUY | SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float = 0.02  # the provider's OWN position size for this trade
    risk_pct: float = 2.0
    is_copyable: bool = True
    execution_mode: str = "immediate"  # immediate | pending
    trigger_price: Optional[float] = None  # required if execution_mode == 'pending'
    execute_live: bool = False
    analysis: str = ""      # provider's own written rationale — shown to followers instead of the AI text

class BulkSignalReq(BaseModel):
    pairs: List[str] = ["EURUSD","GBPUSD","USDJPY","XAUUSD"]
    timeframes: List[str] = ["H1","H4"]
    min_confidence: int = 0
    direction_filter: str = "ALL"

class SubscribeReq(BaseModel):
    provider_id: int; risk_pct: float = 2.0; max_lot: float = 0.05
    min_confidence: int = 65; auto_copy: bool = True; auto_execute: bool = False
    pairs_filter: List[str] = []

class UpdateProgressReq(BaseModel):
    course_id: int; lesson_idx: int; completed: bool = False; score: int = 0

class JournalEntryReq(BaseModel):
    pair: str; direction: str; entry_price: float; exit_price: float
    lot_size: float; pnl_usd: float; pnl_pips: float
    notes: str = ""; emotion: str = "calm"; setup: str = ""

class UpdateProfileReq(BaseModel):
    bio: str = ""; broker: str = ""; mt5_login: str = ""; mt5_server: str = ""

class SettingsReq(BaseModel):
    email_alerts_enabled: Optional[bool] = None
    default_lot_size: Optional[float] = None
    default_risk_pct: Optional[float] = None

class ChangePasswordReq(BaseModel):
    current_password: str
    new_password: str

class ProviderRegisterReq(BaseModel):
    display_name: str; description: str = ""; monthly_fee: float = 0

class ProviderUpdateReq(BaseModel):
    display_name: Optional[str] = None; description: Optional[str] = None
    monthly_fee: Optional[float] = None
    subscription_type: Optional[str] = None       # monthly | percentage
    commission_pct: Optional[float] = None        # % of a follower's profit, if percentage-based
    preferred_pairs: Optional[List[str]] = None
    preferred_timeframes: Optional[List[str]] = None
    max_signals_per_day: Optional[int] = None
    risk_notes: Optional[str] = None

class CopySignalReq(BaseModel):
    lot_size: float = 0.01; risk_pct: float = 2.0; execute_live: bool = False

class QuickTradeReq(BaseModel):
    pair: str
    direction: str  # BUY | SELL
    lot_size: float = 0.01
    sl_pips: float = 30
    tp_pips: float = 60
    execute_live: bool = False

class AdjustTradeReq(BaseModel):
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
    asyncio.create_task(price_broadcaster_loop())
    asyncio.create_task(auto_signal_loop())
    asyncio.create_task(settlement_loop())

app.include_router(payments_router)
app.include_router(mpesa_router)
app.include_router(bridge_router)
app.include_router(prefs_router)
app.include_router(news_router)
# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.post("/auth/register")
def register(req: RegisterReq):
    with get_db() as db:
        existing = db.execute("SELECT id FROM users WHERE email=? OR username=?",
                              (req.email, req.username)).fetchone()
        if existing: raise HTTPException(400, "Email or username already taken")
        verify_token = secrets.token_urlsafe(24)
        verify_expires = (datetime.now() + timedelta(hours=24)).isoformat()
        cursor = db.execute(
            "INSERT INTO users (email,username,password,email_verify_token,email_verify_expires) VALUES (?,?,?,?,?)",
            (req.email, req.username, hash_password(req.password), verify_token, verify_expires))
        user_id = cursor.lastrowid
        db.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user_id,))
        token = create_token(user_id, req.username)
        if email_configured():
            send_verification_email(req.email, req.username, verify_token)
        return {"token": token, "user": {"id": user_id, "username": req.username,
                "email": req.email, "role": "trader", "plan": "free",
                "registration_paid": 0, "subscription_status": "inactive",
                "subscription_active": True, "email_verified": False}}

@app.post("/auth/resend-verification")
def resend_verification(user=Depends(get_current_user)):
    if user.get("email_verified"):
        return {"already_verified": True}
    verify_token = secrets.token_urlsafe(24)
    verify_expires = (datetime.now() + timedelta(hours=24)).isoformat()
    with get_db() as db:
        db.execute("UPDATE users SET email_verify_token=?, email_verify_expires=? WHERE id=?",
                   (verify_token, verify_expires, user["id"]))
    sent = email_configured() and send_verification_email(user["email"], user["username"], verify_token)
    return {"sent": sent}

@app.get("/auth/verify-email")
def verify_email(token: str):
    with get_db() as db:
        row = db.execute("SELECT id, email_verify_expires FROM users WHERE email_verify_token=?", (token,)).fetchone()
        if not row:
            return {"verified": False, "reason": "Invalid or already-used link"}
        try:
            if datetime.fromisoformat(row["email_verify_expires"]) < datetime.now():
                return {"verified": False, "reason": "Link expired — request a new one from Settings"}
        except Exception:
            return {"verified": False, "reason": "Link expired — request a new one from Settings"}
        db.execute("UPDATE users SET email_verified=1, email_verify_token=NULL, email_verify_expires=NULL WHERE id=?",
                   (row["id"],))
        notify_user(db, row["id"], "system", "Email verified ✅", "Your email is confirmed.", "/settings")
    return {"verified": True}

@app.post("/auth/accept-disclaimer")
def accept_disclaimer(user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("UPDATE users SET risk_disclaimer_accepted_at=datetime('now') WHERE id=?", (user["id"],))
    return {"accepted": True}

@app.post("/auth/login")
def login(req: LoginReq):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (req.email,)).fetchone()
        if not user or not verify_password(req.password, user["password"]):
            raise HTTPException(401, "Invalid email or password")
        db.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],))
        token = create_token(user["id"], user["username"])
        return {"token": token, "user": {
            "id": user["id"], "username": user["username"],
            "email": user["email"], "role": user["role"],
            "plan": user["plan"], "balance": user["balance"],
            "equity": user["equity"], "broker": user["broker"],
            "mt5_login": user["mt5_login"], "mt5_server": user["mt5_server"],
            "registration_paid": user["registration_paid"] or 0,
            "subscription_status": user["subscription_status"] or "inactive",
            "subscription_expires_at": user["subscription_expires_at"],
            "subscription_active": is_subscription_active(dict(user)),
        }}

@app.post("/auth/forgot-password")
def forgot_password(req: ForgotPasswordReq):
    """Always responds the same way whether or not the email exists — so this
    endpoint can't be used to check which emails have accounts."""
    with get_db() as db:
        user = db.execute("SELECT id, username, password_reset_expires FROM users WHERE email=?",
                           (req.email,)).fetchone()
        if user:
            # Throttle: don't re-send within 60s of the last code (still asked
            # for again below), so a user mashing "resend" can't spam their inbox.
            recently_sent = False
            if user["password_reset_expires"]:
                try:
                    issued_at = datetime.fromisoformat(user["password_reset_expires"]) - timedelta(minutes=10)
                    recently_sent = (datetime.now() - issued_at) < timedelta(seconds=60)
                except Exception:
                    recently_sent = False
            if not recently_sent:
                otp = f"{secrets.randbelow(1_000_000):06d}"
                expires = (datetime.now() + timedelta(minutes=10)).isoformat()
                db.execute("""UPDATE users SET password_reset_otp=?, password_reset_expires=?,
                              password_reset_attempts=0 WHERE id=?""", (otp, expires, user["id"]))
                if email_configured():
                    send_password_reset_otp_email(req.email, user["username"], otp)
    return {"sent": True}

@app.post("/auth/reset-password")
def reset_password(req: ResetPasswordReq):
    if len(req.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (req.email,)).fetchone()
        if not user or not user["password_reset_otp"]:
            raise HTTPException(400, "Invalid or expired code — request a new one")
        if (user["password_reset_attempts"] or 0) >= 5:
            raise HTTPException(400, "Too many incorrect attempts — request a new code")
        try:
            expired = datetime.fromisoformat(user["password_reset_expires"]) < datetime.now()
        except Exception:
            expired = True
        if expired:
            raise HTTPException(400, "This code has expired — request a new one")
        if req.otp.strip() != user["password_reset_otp"]:
            db.execute("UPDATE users SET password_reset_attempts = password_reset_attempts + 1 WHERE id=?",
                       (user["id"],))
            left = 5 - ((user["password_reset_attempts"] or 0) + 1)
            db.commit()  # must persist before raising — get_db() rolls back on exception,
                         # which was silently discarding this increment every time and
                         # meant the 5-attempt lockout below never actually engaged
            raise HTTPException(400, f"Incorrect code — {max(left, 0)} attempt(s) left")
        db.execute("""UPDATE users SET password=?, password_reset_otp=NULL,
                      password_reset_expires=NULL, password_reset_attempts=0 WHERE id=?""",
                   (hash_password(req.new_password), user["id"]))
        notify_user(db, user["id"], "system", "Password changed",
                    "Your password was just reset. If this wasn't you, contact support immediately.", "/settings")
        token = create_token(user["id"], user["username"])
    return {"reset": True, "token": token}

@app.get("/auth/me")
def get_me(user=Depends(get_current_user)):
    with get_db() as db:
        equity = sync_equity(db, user["id"])
        notifs = db.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
                            (user["id"],)).fetchone()[0]
        subs = db.execute("SELECT COUNT(*) FROM subscriptions WHERE follower_id=? AND is_active=1",
                          (user["id"],)).fetchone()[0]
        fresh = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        _maybe_notify_subscription_expiry(db, dict(fresh))
        new_token = create_token(user["id"], user["username"])  # sliding session — see component.jsx
        return {**{k:v for k,v in dict(fresh).items() if k!="password"},
                "equity": equity, "token": new_token,
                "unread_notifications": notifs, "active_subscriptions": subs,
                "subscription_active": is_subscription_active(dict(fresh))}

def _maybe_notify_subscription_expiry(db, user_row):
    """Warn once when a paid plan is within 3 days of expiring, and once more when
    it actually lapses — so a downgrade to free-tier limits never comes as a
    surprise mid-session."""
    exp = user_row.get("subscription_expires_at")
    if not exp or user_row.get("plan") == "free":
        return
    try:
        expires_at = datetime.fromisoformat(exp.replace("Z", ""))
    except Exception:
        return
    days_left = (expires_at - datetime.utcnow()).total_seconds() / 86400
    uid = user_row["id"]
    if 0 <= days_left <= 3:
        dupe = db.execute("""SELECT id FROM notifications WHERE user_id=? AND type='billing'
                              AND title LIKE 'Subscription expiring%'
                              AND created_at > datetime('now','-2 days')""", (uid,)).fetchone()
        if not dupe:
            notify_user(db, uid, "billing", "Subscription expiring soon",
                 f"Your {user_row['plan']} plan expires in {max(int(days_left),0)} day(s). "
                 f"Renew in Billing to keep your current limits and features.", "/billing")
    elif days_left < 0:
        dupe = db.execute("""SELECT id FROM notifications WHERE user_id=? AND type='billing'
                              AND title = 'Subscription expired'
                              AND created_at > datetime('now','-2 days')""", (uid,)).fetchone()
        if not dupe:
            notify_user(db, uid, "billing", "Subscription expired",
                 "Your plan has expired and your account reverted to Free-tier limits. Renew anytime in Billing.", "/billing")

@app.put("/auth/profile")
def update_profile(req: UpdateProfileReq, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("UPDATE users SET bio=?,broker=?,mt5_login=?,mt5_server=? WHERE id=?",
                   (req.bio, req.broker, req.mt5_login, req.mt5_server, user["id"]))
        fresh = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"success": True, "user": {k: v for k, v in dict(fresh).items() if k != "password"}}

@app.put("/auth/settings")
def update_settings(req: SettingsReq, user=Depends(get_current_user)):
    with get_db() as db:
        if req.email_alerts_enabled is not None:
            db.execute("UPDATE users SET email_alerts_enabled=? WHERE id=?",
                       (int(req.email_alerts_enabled), user["id"]))
        if req.default_lot_size is not None:
            db.execute("UPDATE users SET default_lot_size=? WHERE id=?", (req.default_lot_size, user["id"]))
        if req.default_risk_pct is not None:
            db.execute("UPDATE users SET default_risk_pct=? WHERE id=?", (req.default_risk_pct, user["id"]))
        fresh = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"success": True, "user": {k: v for k, v in dict(fresh).items() if k != "password"}}

@app.post("/auth/change-password")
def change_password(req: ChangePasswordReq, user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute("SELECT password FROM users WHERE id=?", (user["id"],)).fetchone()
        if not verify_password(req.current_password, row["password"]):
            raise HTTPException(400, "Current password is incorrect")
        if len(req.new_password) < 8:
            raise HTTPException(400, "New password must be at least 8 characters")
        db.execute("UPDATE users SET password=? WHERE id=?", (hash_password(req.new_password), user["id"]))
    return {"success": True}

# ── Signal Routes ─────────────────────────────────────────────────────────────
@app.post("/signals/generate")
def generate_signal(req: GenerateSignalReq, user=Depends(get_current_user)):
    if req.pair not in PAIR_CONFIG: raise HTTPException(400, "Unknown pair")
    if req.timeframe not in TF_MAP: raise HTTPException(400, "Unknown timeframe")

    limits = plan_limits(effective_plan(user))
    if limits["signals_per_day"] is not None:
        with get_db() as db:
            used = db.execute(
                "SELECT COUNT(*) c FROM signals WHERE provider_id=? AND date(created_at)=date('now')",
                (user["id"],)).fetchone()["c"]
        if used >= limits["signals_per_day"]:
            raise HTTPException(403, f"Free plan is limited to {limits['signals_per_day']} signals/day — "
                                      f"you've used all {used}. Upgrade to Pro for unlimited signals.")

    df = get_ohlcv(req.pair, req.timeframe, 250)
    df = add_indicators(df)
    sig = build_signal(req.pair, req.timeframe, df, provider_id=user["id"])

    if sig["direction"] == "NO_TRADE":
        # Nothing tradeable — don't burn the user's daily signal quota on a
        # non-actionable result, and don't try to persist it (stop_loss/take_profit
        # are NOT NULL on the signals table, correctly, since a real signal always
        # has them — a NO_TRADE isn't a signal to track, it's just an answer).
        sig.pop("ohlcv", None)
        return sig

    ohlcv = sig.pop("ohlcv", None)
    chart_data = {
        "ohlcv": ohlcv,
        "markers": sig.get("markers", []),
        "support_resistance": sig.get("support_resistance", []),
        "trendline": sig.get("trendline"),
    }

    with get_db() as db:
        # Providers with active subscribers must confirm a signal before it
        # reaches followers — generating one used to auto-copy it into real
        # follower positions instantly, with no review step. A solo trader
        # (no provider profile, or a provider with zero subscribers) has no
        # one to distribute to anyway, so this only changes behavior for
        # accounts that actually have followers riding on the call.
        is_provider = db.execute("SELECT 1 FROM providers WHERE user_id=? AND is_active=1", (user["id"],)).fetchone()
        sub_count = 0
        if is_provider:
            sub_count = db.execute("SELECT COUNT(*) c FROM subscriptions WHERE provider_id=? AND is_active=1",
                                    (user["id"],)).fetchone()["c"]
        approval_status = "pending_review" if (is_provider and sub_count > 0) else "approved"

        cur = db.execute("""
            INSERT INTO signals (provider_id,pair,timeframe,direction,strength,confidence,
            entry_price,stop_loss,take_profit,sl_pips,tp_pips,risk_reward,rsi,macd,
            ema20,ema50,bb_upper,bb_lower,stoch_k,atr,candle_pattern,chart_pattern,
            entry_time,ai_analysis,expires_at,chart_data,approval_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (user["id"], sig["pair"], sig["timeframe"], sig["direction"], sig["strength"],
              sig["confidence"], sig["entry_price"], sig["stop_loss"], sig["take_profit"],
              sig["sl_pips"], sig["tp_pips"], sig["risk_reward"], sig["rsi"], sig["macd"],
              sig["ema20"], sig["ema50"], sig["bb_upper"], sig["bb_lower"], sig["stoch_k"],
              sig["atr"], sig["candle_pattern"], sig["chart_pattern"], sig["entry_time"],
              sig["ai_analysis"], sig["expires_at"], json.dumps(chart_data), approval_status))
        sig_id = cur.lastrowid

        # Distribute to subscribers — auto_copy=1 opens immediately (reserving margin),
        # auto_copy=0 creates a pending_approval row the follower must approve/decline
        # on the Copy Trading page (previously: nothing happened at all for manual
        # subscribers, which is why "manual" looked broken). Held back entirely if
        # this signal still needs the provider's own approval (see above).
        provider_name = db.execute("SELECT username FROM users WHERE id=?", (user["id"],)).fetchone()["username"]
        copies_created = 0
        if approval_status == "approved":
            copies_created = _distribute_signal_to_subscribers(db, sig_id, sig, user["id"], provider_name)

        sig["id"] = sig_id
        sig["approval_status"] = approval_status
        sig["needs_approval"] = approval_status == "pending_review"
        sig["copies_distributed"] = copies_created
        sig["ohlcv"] = ohlcv
        if approval_status == "approved":
            broadcast_threadsafe("signals", {"type": "new_signal", "data": sig})
        return sig

def _distribute_signal_to_subscribers(db, sig_id: int, sig: dict, provider_id: int, provider_name: str) -> int:
    """Sends an approved signal to every active subscriber whose filters
    match. Pulled out of /signals/generate so both the immediate path
    (no-subscriber / non-provider fast path) and POST /signals/{id}/approve
    (the gated provider path) share exactly one copy of this logic."""
    subs = db.execute(
        """SELECT s.*, u.telegram_chat_id FROM subscriptions s
           JOIN users u ON s.follower_id = u.id
           WHERE s.provider_id=? AND s.is_active=1""",
        (provider_id,)).fetchall()
    copies_created = 0
    for sub in subs:
        if sig["confidence"] < sub["min_confidence"]:
            continue
        pf = json.loads(sub["pairs_filter"] or "[]")
        if pf and sig["pair"] not in pf:
            continue

        if not sub["auto_copy"]:
            # Manual mode: suggest it, don't spend the follower's balance yet.
            db.execute("""INSERT INTO copy_trades
                (follower_id,provider_id,signal_id,lot_size,risk_pct,entry_price,
                 stop_loss,take_profit,status,execution_mode)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (sub["follower_id"], provider_id, sig_id, sub["max_lot"], sub["risk_pct"],
                 sig["entry_price"], sig["stop_loss"], sig["take_profit"], "pending_approval", "simulated"))
            notify_user(db, sub["follower_id"], "signal",
                 f"Review to copy: {sig['pair']} {sig['direction']}",
                 f"{sig['confidence']}% confidence — open Copy Trading to approve or decline.", "/copy")
            if sub["telegram_chat_id"]:
                send_telegram_message(sub["telegram_chat_id"],
                    f"🔔 *{provider_name}* just posted a signal you're following (manual mode):\n\n"
                    f"*{sig['pair']} {sig['direction']}* — {sig['confidence']}% confidence\n"
                    f"Entry: `{sig['entry_price']}` · SL: `{sig['stop_loss']}` · TP: `{sig['take_profit']}`\n\n"
                    f"Open Copy Trading in the app to approve or decline.")
            copies_created += 1
            continue

        live = False
        if sub["auto_execute"]:
            follower = db.execute("SELECT bridge_token FROM users WHERE id=?",
                                   (sub["follower_id"],)).fetchone()
            live = bool(follower and follower["bridge_token"])
        exec_mode = "mt5" if live else "simulated"
        status0   = "pending_bridge" if live else "open"
        follower_bal = db.execute("SELECT balance FROM users WHERE id=?", (sub["follower_id"],)).fetchone()["balance"]
        computed_lot = compute_risk_based_lot(follower_bal, sub["risk_pct"], sig["pair"], sig["sl_pips"], sub["max_lot"])
        # MT5 trades don't touch the app's paper balance at all — the real
        # margin is reserved by the broker on the actual MT5 account. Only
        # simulated trades reserve margin here (previously both did, which
        # meant a live trade wrongly deducted twice: once for real on the
        # broker side, once again from the app balance).
        margin = 0.0 if live else compute_margin_usd(sig["pair"], computed_lot)
        if not live and follower_bal < margin:
            notify_user(db, sub["follower_id"], "signal", f"Skipped {sig['pair']} — low balance",
                 f"Needed ${margin:.2f} margin but balance is ${follower_bal:.2f}.", "/copy")
            continue
        db.execute("""INSERT INTO copy_trades
            (follower_id,provider_id,signal_id,lot_size,risk_pct,entry_price,
             stop_loss,take_profit,status,execution_mode,opened_at,margin_used)
            VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
            (sub["follower_id"], provider_id, sig_id,
             computed_lot, sub["risk_pct"],
             sig["entry_price"], sig["stop_loss"], sig["take_profit"], status0, exec_mode, margin))
        if margin:
            db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (margin, sub["follower_id"]))
        copies_created += 1
        notify_user(db, sub["follower_id"], "signal",
             f"Auto-copied: {sig['pair']} {sig['direction']}",
             f"Confidence: {sig['confidence']}% | Entry: {sig['entry_price']} | SL: {sig['stop_loss']} | TP: {sig['take_profit']}", "/copy")
        if sub["telegram_chat_id"]:
            send_telegram_message(sub["telegram_chat_id"],
                f"✅ Auto-copied *{provider_name}*'s signal:\n\n"
                f"*{sig['pair']} {sig['direction']}* — {sig['confidence']}% confidence\n"
                f"Entry: `{sig['entry_price']}` · SL: `{sig['stop_loss']}` · TP: `{sig['take_profit']}`\n"
                f"Lot: `{computed_lot}` ({'real MT5' if live else 'simulated'})")
    return copies_created

@app.get("/signals/pending-review")
def pending_review_signals(user=Depends(get_current_user)):
    """A provider's own AI-generated signals still awaiting their confirm/reject
    before followers see them. Not the same as a follower's own
    pending_approval copy_trades (Copy Trading page) — this is the provider-
    side gate that happens first."""
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM signals WHERE provider_id=? AND approval_status='pending_review'
            ORDER BY created_at DESC
        """, (user["id"],)).fetchall()
        return {"signals": [_expand_signal(dict(r)) for r in rows]}

@app.post("/signals/{signal_id}/approve")
def approve_signal(signal_id: int, user=Depends(get_current_user)):
    """Confirms an AI-generated signal was reviewed and should go out to
    followers now — the step that was missing before (generating used to
    mean instantly copied, with no chance to review it first)."""
    with get_db() as db:
        sig_row = db.execute("SELECT * FROM signals WHERE id=? AND provider_id=?", (signal_id, user["id"])).fetchone()
        if not sig_row:
            raise HTTPException(404, "Signal not found")
        if sig_row["approval_status"] != "pending_review":
            raise HTTPException(400, f"This signal is already {sig_row['approval_status']}")
        db.execute("UPDATE signals SET approval_status='approved' WHERE id=?", (signal_id,))
        provider_name = db.execute("SELECT username FROM users WHERE id=?", (user["id"],)).fetchone()["username"]
        copies_created = _distribute_signal_to_subscribers(db, signal_id, dict(sig_row), user["id"], provider_name)
        broadcast_threadsafe("signals", {"type": "new_signal", "data": _expand_signal(dict(sig_row))})
        return {"approved": True, "copies_distributed": copies_created}

@app.post("/signals/{signal_id}/reject")
def reject_signal(signal_id: int, user=Depends(get_current_user)):
    """Discards a generated signal before it ever reaches followers — no
    copy_trades are created, nobody gets notified."""
    with get_db() as db:
        sig_row = db.execute("SELECT * FROM signals WHERE id=? AND provider_id=?", (signal_id, user["id"])).fetchone()
        if not sig_row:
            raise HTTPException(404, "Signal not found")
        if sig_row["approval_status"] != "pending_review":
            raise HTTPException(400, f"This signal is already {sig_row['approval_status']}")
        db.execute("UPDATE signals SET approval_status='rejected', status='cancelled' WHERE id=?", (signal_id,))
        return {"rejected": True}

@app.post("/signals/manual")
def create_manual_signal(req: ManualSignalReq, user=Depends(get_current_user)):
    """Providers only. Unlike AI-generated signals, this is the provider's own
    call from their own analysis/external source. Two rules that make this
    different from /signals/generate:

    1. is_copyable controls whether followers see it at all — a provider can
       log a private trade here without ever exposing it to followers.
    2. If it IS copyable, the provider's own position (the 'master trade') is
       created right alongside it — a copyable signal always corresponds to a
       real position the provider is themselves running. Closing that master
       trade cascades and closes every follower's copy of it too (see
       /copy/trades/{id}/close), same as a real signal provider would expect:
       you don't leave your followers holding a position after you've bailed.
    """
    if req.pair not in PAIR_CONFIG: raise HTTPException(400, "Unknown pair")
    if req.timeframe not in TF_MAP: raise HTTPException(400, "Unknown timeframe")
    if req.direction not in ("BUY", "SELL"): raise HTTPException(400, "direction must be BUY or SELL")
    if req.execution_mode not in ("immediate", "pending"): raise HTTPException(400, "execution_mode must be 'immediate' or 'pending'")
    if req.execution_mode == "pending" and not req.trigger_price:
        raise HTTPException(400, "trigger_price is required for a pending signal")

    with get_db() as db:
        prow = db.execute("SELECT * FROM providers WHERE user_id=? AND is_active=1", (user["id"],)).fetchone()
        if not prow:
            raise HTTPException(403, "Only registered, active providers can create signals here")

        today_count = db.execute(
            "SELECT COUNT(*) c FROM signals WHERE provider_id=? AND source='manual' AND date(created_at)=date('now')",
            (user["id"],)).fetchone()["c"]
        if today_count >= (prow["max_signals_per_day"] or 10):
            raise HTTPException(403, f"You've hit your {prow['max_signals_per_day']}/day signal limit — raise it in Provider Settings.")

        _, _, pip, _, _ = PAIR_CONFIG[req.pair]
        sl_pips = abs(req.entry_price - req.stop_loss) / pip
        tp_pips = abs(req.take_profit - req.entry_price) / pip
        rr = round(tp_pips / sl_pips, 2) if sl_pips else 0

        status0 = "active" if req.execution_mode == "immediate" else "pending_trigger"
        cur = db.execute("""INSERT INTO signals
            (provider_id,pair,timeframe,direction,strength,confidence,entry_price,stop_loss,take_profit,
             sl_pips,tp_pips,risk_reward,ai_analysis,entry_time,expires_at,source,is_copyable,
             execution_mode,trigger_price,status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user["id"], req.pair, req.timeframe, req.direction, "PROVIDER", 100,
             req.entry_price, req.stop_loss, req.take_profit, round(sl_pips,1), round(tp_pips,1), rr,
             req.analysis or f"Manual signal from {prow['display_name']}", datetime.now().isoformat(),
             (datetime.now()+timedelta(hours=48)).isoformat(), "manual", int(req.is_copyable),
             req.execution_mode, req.trigger_price, status0))
        sig_id = cur.lastrowid

        result = {"id": sig_id, "status": status0, "master_trade_id": None, "copies_distributed": 0}
        if req.execution_mode == "immediate":
            result.update(_activate_manual_signal(db, user["id"], sig_id, req, prow))
        return result

def _activate_manual_signal(db, provider_id: int, sig_id: int, req_or_row, prow) -> dict:
    """Places the provider's own master trade and (if is_copyable) distributes
    to followers with master_trade_id linkage. Shared by immediate-execution and
    by the pending-trigger monitor once price actually reaches trigger_price."""
    pair = req_or_row.pair if hasattr(req_or_row, "pair") else req_or_row["pair"]
    direction = req_or_row.direction if hasattr(req_or_row, "direction") else req_or_row["direction"]
    entry = req_or_row.entry_price if hasattr(req_or_row, "entry_price") else req_or_row["entry_price"]
    stop = req_or_row.stop_loss if hasattr(req_or_row, "stop_loss") else req_or_row["stop_loss"]
    target = req_or_row.take_profit if hasattr(req_or_row, "take_profit") else req_or_row["take_profit"]
    lot = req_or_row.lot_size if hasattr(req_or_row, "lot_size") else 0.02
    execute_live = req_or_row.execute_live if hasattr(req_or_row, "execute_live") else False
    is_copyable = req_or_row.is_copyable if hasattr(req_or_row, "is_copyable") else True

    live = False
    if execute_live:
        u = db.execute("SELECT bridge_token FROM users WHERE id=?", (provider_id,)).fetchone()
        live = bool(u and u["bridge_token"])
    exec_mode = "mt5" if live else "simulated"
    status0 = "pending_bridge" if live else "open"
    margin = 0.0 if live else compute_margin_usd(pair, lot)
    balance = db.execute("SELECT balance FROM users WHERE id=?", (provider_id,)).fetchone()["balance"]
    if not live and balance < margin:
        raise HTTPException(400, f"Insufficient balance for your own position — needs ${margin:.2f}, you have ${balance:.2f}")

    cur = db.execute("""INSERT INTO copy_trades
        (follower_id,provider_id,signal_id,lot_size,risk_pct,entry_price,stop_loss,take_profit,
         status,execution_mode,opened_at,margin_used,pair,direction,is_master)
        VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,1)""",
        (provider_id, provider_id, sig_id, lot, 2.0, entry, stop, target, status0, exec_mode, margin, pair, direction))
    master_trade_id = cur.lastrowid
    if margin:
        db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (margin, provider_id))
    db.execute("UPDATE signals SET master_trade_id=? WHERE id=?", (master_trade_id, sig_id))

    copies_created = 0
    if is_copyable:
        provider_name = db.execute("SELECT username FROM users WHERE id=?", (provider_id,)).fetchone()["username"]
        subs = db.execute("""SELECT s.*, u.telegram_chat_id FROM subscriptions s
                              JOIN users u ON s.follower_id = u.id
                              WHERE s.provider_id=? AND s.is_active=1""", (provider_id,)).fetchall()
        for sub in subs:
            pf = json.loads(sub["pairs_filter"] or "[]")
            if pf and pair not in pf:
                continue
            f_live = False
            if sub["auto_copy"] and sub["auto_execute"]:
                fu = db.execute("SELECT bridge_token FROM users WHERE id=?", (sub["follower_id"],)).fetchone()
                f_live = bool(fu and fu["bridge_token"])
            f_bal = db.execute("SELECT balance FROM users WHERE id=?", (sub["follower_id"],)).fetchone()["balance"]

            if not sub["auto_copy"]:
                db.execute("""INSERT INTO copy_trades
                    (follower_id,provider_id,signal_id,lot_size,risk_pct,entry_price,stop_loss,take_profit,
                     status,execution_mode,pair,direction,master_trade_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sub["follower_id"], provider_id, sig_id, sub["max_lot"], sub["risk_pct"],
                     entry, stop, target, "pending_approval", "simulated", pair, direction, master_trade_id))
                notify_user(db, sub["follower_id"], "signal", f"Review to copy: {pair} {direction}",
                     f"{provider_name} is running this trade live — open Copy Trading to approve or decline.", "/copy")
                copies_created += 1
                continue

            f_lot = compute_risk_based_lot(f_bal, sub["risk_pct"], pair, abs(entry-stop)/PAIR_CONFIG.get(pair, PAIR_CONFIG["EURUSD"])[2], sub["max_lot"])
            f_margin = 0.0 if f_live else compute_margin_usd(pair, f_lot)
            if not f_live and f_bal < f_margin:
                continue
            f_exec = "mt5" if f_live else "simulated"
            f_status = "pending_bridge" if f_live else "open"
            db.execute("""INSERT INTO copy_trades
                (follower_id,provider_id,signal_id,lot_size,risk_pct,entry_price,stop_loss,take_profit,
                 status,execution_mode,opened_at,margin_used,pair,direction,master_trade_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,?,?)""",
                (sub["follower_id"], provider_id, sig_id, f_lot, sub["risk_pct"], entry, stop, target,
                 f_status, f_exec, f_margin, pair, direction, master_trade_id))
            if f_margin:
                db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (f_margin, sub["follower_id"]))
            copies_created += 1
            notify_user(db, sub["follower_id"], "signal", f"Auto-copied: {pair} {direction}",
                 f"{provider_name} opened this live — lot {f_lot} ({'real MT5' if f_live else 'simulated'})", "/copy")
            if sub["telegram_chat_id"]:
                send_telegram_message(sub["telegram_chat_id"],
                    f"✅ *{provider_name}* opened *{pair} {direction}* live — auto-copied for you (lot {f_lot}).")

    return {"master_trade_id": master_trade_id, "copies_distributed": copies_created}

@app.post("/signals/bulk")
def bulk_signals(req: BulkSignalReq, user=Depends(get_current_user)):
    limits = plan_limits(effective_plan(user))
    if not limits["bulk_generate"]:
        raise HTTPException(403, "Bulk signal generation requires a Pro plan or above. Upgrade to unlock it.")
    results = []
    seed_base = int(datetime.now().strftime("%Y%m%d%H"))
    for p in req.pairs:
        for tf in req.timeframes:
            if p not in PAIR_CONFIG or tf not in TF_MAP: continue
            try:
                from signals import synthetic_ohlcv
                df = synthetic_ohlcv(p, tf, 300, seed=seed_base + abs(hash(p+tf))%1000)
                df = add_indicators(df)
                sig = build_signal(p, tf, df, provider_id=user["id"])
                ohlcv = sig.pop("ohlcv", None)
                if sig["confidence"] >= req.min_confidence:
                    if req.direction_filter == "ALL" or sig["direction"] == req.direction_filter:
                        results.append({**sig, "ohlcv": ohlcv})
            except Exception as e:
                results.append({"pair": p, "timeframe": tf, "error": str(e)})
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    for sig in results[:3]:
        if "error" not in sig:
            broadcast_threadsafe("signals", {"type": "new_signal", "data": sig})
    return {"count": len(results), "signals": results}

def sync_equity(db, user_id: int) -> float:
    """balance + unrealized P&L of open SIMULATED trades only, using a fresh
    quote per unique pair. MT5-linked trades are excluded — that money lives on
    the broker's own account, not the app's paper balance, so it shouldn't count
    toward YobbyForex's own equity figure (see Profile/Settings for the real MT5
    account balance instead, reported by your EA's heartbeat).
    Persists to users.equity so any page reading the cached user object still
    sees a reasonably fresh number."""
    row = db.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
    balance = float(row["balance"]) if row else 0.0
    open_trades = db.execute(
        "SELECT ct.*, s.pair as sig_pair, s.direction as sig_direction "
        "FROM copy_trades ct LEFT JOIN signals s ON ct.signal_id=s.id "
        "WHERE ct.follower_id=? AND ct.status='open' AND ct.execution_mode != 'mt5'", (user_id,)).fetchall()
    floating = 0.0
    quote_cache = {}
    for t in open_trades:
        pair = t["pair"] or t["sig_pair"]
        if not pair: continue
        if pair not in quote_cache:
            try: quote_cache[pair] = float(get_live_quote(pair)["price"])
            except Exception: quote_cache[pair] = None
        price = quote_cache[pair]
        if price is None: continue
        _, _, pip, _, _ = PAIR_CONFIG.get(pair, PAIR_CONFIG["EURUSD"])
        is_buy = (t["direction"] or t["sig_direction"]) == "BUY"
        pnl_pips = (price - t["entry_price"]) / pip * (1 if is_buy else -1)
        floating += pip_value_usd(pair, pnl_pips, t["lot_size"])
    equity = round(balance + floating, 2)
    db.execute("UPDATE users SET equity=? WHERE id=?", (equity, user_id))
    return equity

def _expand_signal(row: dict) -> dict:
    d = dict(row)
    raw = d.pop("chart_data", None)
    extra = {"ohlcv": None, "markers": [], "support_resistance": [], "trendline": None}
    if raw:
        try:
            extra.update(json.loads(raw))
        except Exception:
            pass
    return {**d, **extra}

SIGNAL_DELAY_MINUTES = {"free": 15, "trader_pro": 0, "trader_elite": 0, "provider_pro": 0}

@app.get("/signals/latest")
def latest_signals(limit: int = Query(20), user=Depends(get_optional_user)):
    plan = effective_plan(dict(user)) if user else "free"
    delay = SIGNAL_DELAY_MINUTES.get(plan, 15)
    with get_db() as db:
        if delay > 0:
            rows = db.execute("""
                SELECT s.*, u.username as provider_name
                FROM signals s LEFT JOIN users u ON s.provider_id=u.id
                WHERE s.status='active' AND s.approval_status != 'pending_review' AND s.created_at <= datetime('now', ?)
                ORDER BY s.created_at DESC LIMIT ?
            """, (f'-{delay} minutes', limit)).fetchall()
        else:
            rows = db.execute("""
                SELECT s.*, u.username as provider_name
                FROM signals s LEFT JOIN users u ON s.provider_id=u.id
                WHERE s.status='active' AND s.approval_status != 'pending_review'
                ORDER BY s.created_at DESC LIMIT ?
            """, (limit,)).fetchall()
        # Let the free-tier UI show "N real-time signals available on Pro" rather
        # than just silently having fewer results with no explanation.
        realtime_count = 0
        if delay > 0:
            realtime_count = db.execute(
                "SELECT COUNT(*) c FROM signals WHERE status='active' AND created_at > datetime('now', ?)",
                (f'-{delay} minutes',)).fetchone()["c"]
        return {"signals": [_expand_signal(r) for r in rows],
                "plan_delay_minutes": delay, "realtime_signals_locked": realtime_count}

@app.get("/signals/backtest")
def backtest_signal_engine(pair: str = "EURUSD", timeframe: str = "H1", bars: int = 1000,
                            user=Depends(get_current_user)):
    if pair not in PAIR_CONFIG: raise HTTPException(400, "Unknown pair")
    if timeframe not in TF_MAP: raise HTTPException(400, "Unknown timeframe")
    bars = max(200, min(bars, 3000))  # keep this fast enough to run synchronously
    return run_backtest(pair, timeframe, bars)


@app.get("/signals/history")
def signal_history(pair: str = "EURUSD", timeframe: str = "H1", period: str = "1M",
                   user=Depends(get_optional_user)):
    n = {"1M":180,"3M":360,"6M":540,"1Y":720}.get(period, 180)
    from signals import synthetic_ohlcv
    df = synthetic_ohlcv(pair, timeframe, n+250, seed=42+abs(hash(pair))%100)
    df = add_indicators(df)
    signals = []; step = max(1, n//35)
    for i in range(len(df)-step, 250+step, -step):
        try:
            sig = build_signal(pair, timeframe, df.iloc[:i])
            sig.pop("ohlcv", None)
            signals.append(sig)
        except: pass
    signals.sort(key=lambda x: str(x.get("expires_at","")))
    wins = sum(1 for s in signals if s["confidence"] > 62)
    return {"pair": pair, "timeframe": timeframe, "period": period,
            "count": len(signals), "estimated_winrate": round(wins/max(len(signals),1)*100,1),
            "signals": signals}

# NOTE: this dynamic route MUST come after every other static /signals/* route
# (e.g. /signals/history above) — FastAPI/Starlette matches routes in
# registration order, so a /signals/{signal_id} declared earlier will swallow
# /signals/history requests and try (and fail) to parse "history" as an int.
@app.get("/signals/{signal_id}")
def get_signal(signal_id: int, user=Depends(get_optional_user)):
    with get_db() as db:
        row = db.execute("""
            SELECT s.*, u.username as provider_name
            FROM signals s LEFT JOIN users u ON s.provider_id=u.id
            WHERE s.id=?
        """, (signal_id,)).fetchone()
        if not row: raise HTTPException(404, "Signal not found")
        return _expand_signal(row)

# ── Providers & Copy Trading ──────────────────────────────────────────────────
@app.post("/providers/register")
def register_provider(req: ProviderRegisterReq, user=Depends(get_current_user)):
    """Self-service 'become a provider' — requires the Provider Pro plan (this is
    the paid side of the marketplace: providers earn from followers/revenue share,
    so it isn't included in the free/trader plans)."""
    limits = plan_limits(effective_plan(user))
    if not limits["can_be_provider"]:
        raise HTTPException(403, "Becoming a provider requires the Provider Pro plan. Upgrade in Billing to unlock it.")
    with get_db() as db:
        existing = db.execute("SELECT id FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        if existing:
            raise HTTPException(400, "You're already registered as a provider")
        db.execute("""INSERT INTO providers
            (user_id,display_name,description,win_rate,total_signals,total_pips,
             avg_rr,monthly_pips,followers_count,monthly_fee,is_verified,is_active)
            VALUES (?,?,?,0,0,0,0,0,0,?,1,1)""",
            (user["id"], req.display_name, req.description, req.monthly_fee))
        recompute_provider_stats(db, user["id"])
        db.execute("UPDATE users SET role='provider' WHERE id=?", (user["id"],))
        row = db.execute("SELECT * FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        return dict(row)

@app.get("/providers/me")
def my_provider_profile(user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute("SELECT * FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        if not row:
            raise HTTPException(404, "You haven't registered as a provider yet")
        recompute_provider_stats(db, user["id"])
        row = db.execute("SELECT * FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        return dict(row)

@app.get("/providers/me/followers")
def my_followers(user=Depends(get_current_user)):
    """Lets a provider see who's following them, their copy settings, their
    trade stats on this provider's signals, and — for percentage-pricing
    providers — how much each follower has generated in fees."""
    with get_db() as db:
        prow = db.execute("SELECT id FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        if not prow:
            raise HTTPException(404, "You haven't registered as a provider yet")
        subs = db.execute("""
            SELECT s.*, u.username, u.plan
            FROM subscriptions s JOIN users u ON s.follower_id=u.id
            WHERE s.provider_id=? AND s.is_active=1
            ORDER BY s.created_at DESC
        """, (user["id"],)).fetchall()
        followers = []
        for s in subs:
            stats = db.execute("""
                SELECT COUNT(*) c, COALESCE(SUM(pnl_usd),0) pnl,
                       COALESCE(SUM(margin_used),0) invested,
                       SUM(CASE WHEN status='closed' AND pnl_usd>0 THEN 1 ELSE 0 END) wins,
                       SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) closed,
                       SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) open
                FROM copy_trades WHERE follower_id=? AND provider_id=?
            """, (s["follower_id"], user["id"])).fetchone()
            earned = db.execute("""SELECT COALESCE(SUM(amount_usd),0) FROM provider_earnings
                                    WHERE provider_id=? AND follower_id=?""",
                                 (user["id"], s["follower_id"])).fetchone()[0]
            followers.append({
                "follower_id": s["follower_id"], "username": s["username"], "plan": s["plan"],
                "auto_copy": bool(s["auto_copy"]), "min_confidence": s["min_confidence"],
                "risk_pct": s["risk_pct"], "max_lot": s["max_lot"],
                "subscribed_since": s["created_at"],
                "trades_copied": stats["c"], "trades_closed": stats["closed"], "trades_open": stats["open"],
                "wins": stats["wins"] or 0,
                "amount_invested_usd": round(stats["invested"] or 0, 2),
                "pnl_from_your_signals": round(stats["pnl"] or 0, 2),
                "fees_earned_from_follower_usd": round(earned, 2),
            })
        return {"count": len(followers), "followers": followers}

@app.post("/providers/me/followers/{follower_id}/remove")
def remove_follower(follower_id: int, user=Depends(get_current_user)):
    """Provider forcibly unsubscribes a follower — stops future signal
    distribution to them. Doesn't touch trades already open; those run to
    their own TP/SL/close as normal."""
    with get_db() as db:
        prow = db.execute("SELECT id FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        if not prow:
            raise HTTPException(404, "You haven't registered as a provider yet")
        sub = db.execute("SELECT id FROM subscriptions WHERE provider_id=? AND follower_id=? AND is_active=1",
                         (user["id"], follower_id)).fetchone()
        if not sub:
            raise HTTPException(404, "This user isn't following you")
        db.execute("UPDATE subscriptions SET is_active=0 WHERE id=?", (sub["id"],))
        db.execute("UPDATE providers SET followers_count = MAX(0, followers_count-1) WHERE user_id=?", (user["id"],))
        notify_user(db, follower_id, "copy", "Subscription ended",
             "The provider you were following removed you as a subscriber — new signals from them will stop.", "/providers")
        return {"removed": True}

@app.get("/providers/me/earnings")
def my_earnings(user=Depends(get_current_user)):
    """Revenue dashboard for a provider: total earned (all-time), accrued vs
    paid, and a transaction-level breakdown. Only meaningful for
    subscription_type='percentage' providers — monthly-fee revenue comes
    through the existing subscription billing (Billing/Stripe/M-Pesa), not this
    ledger, since that's charged to the follower directly rather than skimmed
    from trade profit."""
    with get_db() as db:
        prow = db.execute("SELECT * FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        if not prow:
            raise HTTPException(404, "You haven't registered as a provider yet")
        rows = db.execute("""
            SELECT pe.*, u.username as follower_username
            FROM provider_earnings pe JOIN users u ON pe.follower_id = u.id
            WHERE pe.provider_id=? ORDER BY pe.created_at DESC LIMIT 100
        """, (user["id"],)).fetchall()
        totals = db.execute("""
            SELECT COALESCE(SUM(amount_usd),0) total,
                   COALESCE(SUM(CASE WHEN status='accrued' THEN amount_usd ELSE 0 END),0) accrued,
                   COALESCE(SUM(CASE WHEN status='paid' THEN amount_usd ELSE 0 END),0) paid,
                   COUNT(*) c
            FROM provider_earnings WHERE provider_id=?
        """, (user["id"],)).fetchone()
        return {
            "subscription_type": prow["subscription_type"], "commission_pct": prow["commission_pct"],
            "total_earned_usd": round(totals["total"], 2), "accrued_usd": round(totals["accrued"], 2),
            "paid_usd": round(totals["paid"], 2), "fee_events": totals["c"],
            "transactions": [dict(r) for r in rows],
        }


@app.put("/providers/me")
def update_provider_profile(req: ProviderUpdateReq, user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute("SELECT id FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        if not row:
            raise HTTPException(404, "You haven't registered as a provider yet")
        if req.subscription_type is not None and req.subscription_type not in ("monthly", "percentage"):
            raise HTTPException(400, "subscription_type must be 'monthly' or 'percentage'")
        if req.commission_pct is not None and not (0 <= req.commission_pct <= 50):
            raise HTTPException(400, "commission_pct must be between 0 and 50")
        fields, vals = [], []
        simple_fields = [
            ("display_name", req.display_name), ("description", req.description),
            ("monthly_fee", req.monthly_fee), ("subscription_type", req.subscription_type),
            ("commission_pct", req.commission_pct), ("max_signals_per_day", req.max_signals_per_day),
            ("risk_notes", req.risk_notes),
        ]
        for col, val in simple_fields:
            if val is not None:
                fields.append(f"{col}=?"); vals.append(val)
        if req.preferred_pairs is not None:
            fields.append("preferred_pairs=?"); vals.append(json.dumps(req.preferred_pairs))
        if req.preferred_timeframes is not None:
            fields.append("preferred_timeframes=?"); vals.append(json.dumps(req.preferred_timeframes))
        if fields:
            vals.append(user["id"])
            db.execute(f"UPDATE providers SET {', '.join(fields)} WHERE user_id=?", vals)
        row = db.execute("SELECT * FROM providers WHERE user_id=?", (user["id"],)).fetchone()
        return dict(row)

@app.post("/signals/{signal_id}/copy")
def copy_signal_manually(signal_id: int, req: CopySignalReq, user=Depends(get_current_user)):
    """One-off manual copy of a single signal — no subscription required."""
    with get_db() as db:
        sig = db.execute("SELECT * FROM signals WHERE id=?", (signal_id,)).fetchone()
        if not sig:
            raise HTTPException(404, "Signal not found")
        if sig["provider_id"] == user["id"]:
            raise HTTPException(400, "You can't copy your own signal")
        if sig["status"] != "active":
            raise HTTPException(400, "This signal has already closed")
        if sig["approval_status"] == "pending_review":
            raise HTTPException(400, "This signal is still awaiting the provider's confirmation")
        if sig["approval_status"] == "rejected":
            raise HTTPException(400, "This signal was withdrawn by its provider")
        dup = db.execute(
            "SELECT id FROM copy_trades WHERE follower_id=? AND signal_id=?",
            (user["id"], signal_id)).fetchone()
        if dup:
            raise HTTPException(400, "You've already copied this signal")

        limits = plan_limits(effective_plan(user))
        if limits["copies_per_day"] is not None:
            used = db.execute(
                "SELECT COUNT(*) c FROM copy_trades WHERE follower_id=? AND date(opened_at)=date('now')",
                (user["id"],)).fetchone()["c"]
            if used >= limits["copies_per_day"]:
                raise HTTPException(403, f"Free plan is limited to {limits['copies_per_day']} manual signal "
                                          f"copies/day — you've used all {used}. Upgrade to Pro for unlimited copies.")

        live = False
        if req.execute_live:
            u = db.execute("SELECT bridge_token FROM users WHERE id=?", (user["id"],)).fetchone()
            if not u or not u["bridge_token"]:
                raise HTTPException(400, "Connect your MT5 bridge in Profile first (Profile > MT5 Auto-Trading)")
            closed = _low_liquidity_window()
            if closed:
                raise HTTPException(400, f"Can't place a live order right now — {closed.lower()}. "
                                          f"Simulated copy is still available.")
            live = True

        fresh_balance = db.execute("SELECT balance FROM users WHERE id=?", (user["id"],)).fetchone()["balance"]
        computed_lot = compute_risk_based_lot(fresh_balance, req.risk_pct, sig["pair"], sig["sl_pips"], req.lot_size)
        # MT5 trades don't reserve app paper-balance margin — the broker handles
        # real margin on the actual MT5 account. Previously this deducted here
        # AND the real trade used real margin on MT5, i.e. deducted twice.
        margin = 0.0 if live else compute_margin_usd(sig["pair"], computed_lot)
        if not live and fresh_balance < margin:
            raise HTTPException(400, f"Insufficient balance — this trade needs ${margin:.2f} margin, "
                                      f"you have ${fresh_balance:.2f}. Reduce lot size or top up.")

        exec_mode = "mt5" if live else "simulated"
        status0   = "pending_bridge" if live else "open"
        cur = db.execute("""INSERT INTO copy_trades
            (follower_id,provider_id,signal_id,lot_size,risk_pct,entry_price,
             stop_loss,take_profit,status,execution_mode,opened_at,margin_used)
            VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
            (user["id"], sig["provider_id"], signal_id, computed_lot, req.risk_pct,
             sig["entry_price"], sig["stop_loss"], sig["take_profit"], status0, exec_mode, margin))
        # Reserve the margin immediately — it's released back (plus/minus P&L) on close.
        # Only applies to simulated trades (margin is 0 for MT5-linked ones — see above).
        if margin:
            db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (margin, user["id"]))
        return {"copied": True, "copy_trade_id": cur.lastrowid, "pair": sig["pair"],
                "direction": sig["direction"], "execution_mode": exec_mode, "margin_reserved": margin,
                "lot_size": computed_lot}

FOREX_ONLY_PAIRS = {"EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD","EURGBP","EURJPY","GBPJPY"}

@app.post("/trades/quick")
def place_quick_trade(req: QuickTradeReq, user=Depends(get_current_user)):
    """Lets a user place a trade straight from the price chart instead of copying
    a generated signal — same execution/margin machinery as a copied signal."""
    if req.pair not in PAIR_CONFIG: raise HTTPException(400, "Unknown pair")
    if req.pair not in FOREX_ONLY_PAIRS:
        raise HTTPException(400, "Direct trade placement is limited to forex currency pairs")
    if req.direction not in ("BUY", "SELL"): raise HTTPException(400, "direction must be BUY or SELL")
    quote = get_live_quote(req.pair)
    entry = float(quote["ask"] if req.direction == "BUY" else quote["bid"])
    _, _, pip, _, _ = PAIR_CONFIG[req.pair]
    sl = entry - req.sl_pips * pip if req.direction == "BUY" else entry + req.sl_pips * pip
    tp = entry + req.tp_pips * pip if req.direction == "BUY" else entry - req.tp_pips * pip

    with get_db() as db:
        live = False
        if req.execute_live:
            u = db.execute("SELECT bridge_token FROM users WHERE id=?", (user["id"],)).fetchone()
            if not u or not u["bridge_token"]:
                raise HTTPException(400, "Connect your MT5 bridge in Profile first")
            live = True
        # MT5 trades don't reserve app paper-balance margin — see the same fix in
        # /signals/{id}/copy above.
        margin = 0.0 if live else compute_margin_usd(req.pair, req.lot_size)
        balance = db.execute("SELECT balance FROM users WHERE id=?", (user["id"],)).fetchone()["balance"]
        if not live and balance < margin:
            raise HTTPException(400, f"Insufficient balance — needs ${margin:.2f} margin, you have ${balance:.2f}")
        exec_mode = "mt5" if live else "simulated"
        status0 = "pending_bridge" if live else "open"
        cur = db.execute("""INSERT INTO copy_trades
            (follower_id,provider_id,signal_id,lot_size,risk_pct,entry_price,
             stop_loss,take_profit,status,execution_mode,opened_at,margin_used,pair,direction)
            VALUES (?,NULL,NULL,?,?,?,?,?,?,?,datetime('now'),?,?,?)""",
            (user["id"], req.lot_size, 2.0, round(entry, 5), round(sl, 5), round(tp, 5), status0, exec_mode,
             margin, req.pair, req.direction))
        if margin:
            db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (margin, user["id"]))
        return {"placed": True, "copy_trade_id": cur.lastrowid, "entry_price": round(entry, 5),
                "stop_loss": round(sl, 5), "take_profit": round(tp, 5), "margin_reserved": margin,
                "execution_mode": exec_mode, "pair": req.pair, "direction": req.direction}

from trade_close import apply_trade_close

@app.post("/copy/trades/{trade_id}/close")
def close_trade_manually(trade_id: int, user=Depends(get_current_user)):
    """Manual close at current market price — for quick trades placed straight from
    the chart (these have no signal to auto-settle) and for closing any open
    position early instead of waiting for TP/SL.

    MT5-linked trades are NOT closed here directly — this used to fake a close in
    our DB (crediting balance immediately) while the real position stayed open on
    the user's broker account, which is a real money-risk bug. Instead this queues
    a close request the EA picks up on its next poll and executes for real; the
    trade only actually closes (and balance updates) once /bridge/report-close
    confirms MT5 did it.
    """
    with get_db() as db:
        t = db.execute("""SELECT ct.*, COALESCE(ct.pair, s.pair) as pair0, COALESCE(ct.direction, s.direction) as direction0
                           FROM copy_trades ct LEFT JOIN signals s ON ct.signal_id=s.id
                           WHERE ct.id=? AND ct.follower_id=? AND ct.status='open'""",
                        (trade_id, user["id"])).fetchone()
        if not t: raise HTTPException(404, "Open trade not found")
        pair, direction = t["pair0"], t["direction0"]
        if not pair: raise HTTPException(400, "Can't determine this trade's pair")

        if t["execution_mode"] == "mt5":
            if not t["mt5_ticket"]:
                raise HTTPException(400, "No MT5 ticket recorded for this trade yet — try again once the EA confirms the fill.")
            db.execute("UPDATE copy_trades SET status='close_requested' WHERE id=?", (trade_id,))
            return {"queued": True, "message": "Close request sent to your MT5 terminal — it'll confirm within a few seconds of your EA's next poll."}

        quote = get_live_quote(pair)
        close_price = float(quote["bid"] if direction == "BUY" else quote["ask"])
        _, _, pip, _, _ = PAIR_CONFIG.get(pair, PAIR_CONFIG["EURUSD"])
        pnl_pips = (close_price - t["entry_price"]) / pip * (1 if direction == "BUY" else -1)
        pnl_usd = pip_value_usd(pair, pnl_pips, t["lot_size"])
        result = "win" if pnl_usd > 0 else ("loss" if pnl_usd < 0 else "breakeven")
        closed_ids = apply_trade_close(db, trade_id, close_price, pnl_pips, pnl_usd, result, "Manually closed")
        return {"closed": True, "close_price": close_price, "pnl_usd": round(pnl_usd, 2), "pnl_pips": round(pnl_pips, 1),
                "cascaded_closes": len(closed_ids) - 1}

@app.put("/copy/trades/{trade_id}/adjust")
def adjust_trade(trade_id: int, req: AdjustTradeReq, user=Depends(get_current_user)):
    """Adjust stop-loss/take-profit on an open position. Simulated trades update
    instantly. MT5-linked trades queue a modify request the EA picks up and applies
    for real in MT5 (same pattern as the close-queue) — we don't just rewrite the
    number in our own DB while the real broker-side stop stays wherever it was."""
    if req.stop_loss is None and req.take_profit is None:
        raise HTTPException(400, "Provide at least a new stop_loss or take_profit")
    with get_db() as db:
        t = db.execute("SELECT * FROM copy_trades WHERE id=? AND follower_id=? AND status='open'",
                        (trade_id, user["id"])).fetchone()
        if not t: raise HTTPException(404, "Open trade not found")

        new_sl = req.stop_loss if req.stop_loss is not None else t["stop_loss"]
        new_tp = req.take_profit if req.take_profit is not None else t["take_profit"]

        if t["execution_mode"] == "mt5":
            if not t["mt5_ticket"]:
                raise HTTPException(400, "No MT5 ticket recorded for this trade yet")
            db.execute("""UPDATE copy_trades SET modify_requested=1, pending_stop_loss=?, pending_take_profit=?
                          WHERE id=?""", (new_sl, new_tp, trade_id))
            return {"queued": True, "message": "SL/TP change sent to your MT5 terminal — it'll confirm shortly."}

        db.execute("UPDATE copy_trades SET stop_loss=?, take_profit=? WHERE id=?", (new_sl, new_tp, trade_id))
        return {"adjusted": True, "stop_loss": new_sl, "take_profit": new_tp}

@app.post("/copy/trades/{trade_id}/approve")
def approve_pending_copy(trade_id: int, user=Depends(get_current_user)):
    """Follower approves a manual-mode copy suggestion — this is the moment margin
    actually gets reserved (for simulated trades only — see MT5 note below),
    matching the manual-copy flow on the Signals page."""
    with get_db() as db:
        t = db.execute("SELECT * FROM copy_trades WHERE id=? AND follower_id=?", (trade_id, user["id"])).fetchone()
        if not t: raise HTTPException(404, "Pending trade not found")
        if t["status"] != "pending_approval": raise HTTPException(400, "This trade is no longer pending")
        sig = db.execute("SELECT pair, status FROM signals WHERE id=?", (t["signal_id"],)).fetchone()
        if sig and sig["status"] != "active":
            db.execute("UPDATE copy_trades SET status='failed', fail_reason='Signal closed before approval' WHERE id=?", (trade_id,))
            raise HTTPException(400, "This signal already closed — can't approve it anymore")
        pair = sig["pair"] if sig else "EURUSD"
        # MT5 trades don't reserve app paper-balance margin — same fix as the other
        # trade-opening endpoints above (was double-deducting: once for real on the
        # broker, once again from the app balance).
        live = t["execution_mode"] == "mt5"
        margin = 0.0 if live else compute_margin_usd(pair, t["lot_size"])
        balance = db.execute("SELECT balance FROM users WHERE id=?", (user["id"],)).fetchone()["balance"]
        if not live and balance < margin:
            raise HTTPException(400, f"Insufficient balance — needs ${margin:.2f} margin, you have ${balance:.2f}")
        db.execute("UPDATE copy_trades SET status='open', margin_used=?, opened_at=datetime('now') WHERE id=?", (margin, trade_id))
        if margin:
            db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (margin, user["id"]))
        return {"approved": True, "margin_reserved": margin}

@app.post("/copy/trades/{trade_id}/decline")
def decline_pending_copy(trade_id: int, user=Depends(get_current_user)):
    with get_db() as db:
        t = db.execute("SELECT id FROM copy_trades WHERE id=? AND follower_id=? AND status='pending_approval'",
                        (trade_id, user["id"])).fetchone()
        if not t: raise HTTPException(404, "Pending trade not found")
        db.execute("UPDATE copy_trades SET status='declined' WHERE id=?", (trade_id,))
        return {"declined": True}

@app.get("/providers")
def list_providers(user=Depends(get_optional_user)):
    with get_db() as db:
        rows = db.execute("""
            SELECT p.*, u.username, u.email, u.avatar, u.bio
            FROM providers p JOIN users u ON p.user_id=u.id
            WHERE p.is_active=1
            ORDER BY p.win_rate DESC
        """).fetchall()
        return {"providers": [dict(r) for r in rows]}

@app.get("/providers/{provider_id}")
def get_provider(provider_id: int, user=Depends(get_optional_user)):
    with get_db() as db:
        p = db.execute("""
            SELECT p.*, u.username, u.email, u.bio, u.created_at as member_since
            FROM providers p JOIN users u ON p.user_id=u.id WHERE p.id=?
        """, (provider_id,)).fetchone()
        if not p: raise HTTPException(404)
        signals = db.execute(
            "SELECT * FROM signals WHERE provider_id=? ORDER BY created_at DESC LIMIT 20",
            (p["user_id"],)).fetchall()
        return {**dict(p), "recent_signals": [dict(s) for s in signals]}

@app.post("/copy/subscribe")
def subscribe(req: SubscribeReq, user=Depends(get_current_user)):
    with get_db() as db:
        provider_row = db.execute(
            "SELECT id FROM providers WHERE user_id=? AND is_active=1", (req.provider_id,)).fetchone()
        if not provider_row:
            raise HTTPException(404, "That user isn't an active signal provider")
        if req.provider_id == user["id"]:
            raise HTTPException(400, "You can't subscribe to your own provider profile")

        # Check not already subscribed
        existing = db.execute(
            "SELECT id FROM subscriptions WHERE follower_id=? AND provider_id=? AND is_active=1",
            (user["id"], req.provider_id)).fetchone()
        if existing: raise HTTPException(400, "Already subscribed to this provider")

        limits = plan_limits(effective_plan(user))
        if limits["max_subscriptions"] is not None:
            active_count = db.execute(
                "SELECT COUNT(*) c FROM subscriptions WHERE follower_id=? AND is_active=1",
                (user["id"],)).fetchone()["c"]
            if active_count >= limits["max_subscriptions"]:
                raise HTTPException(403, f"Your plan allows following up to {limits['max_subscriptions']} "
                                          f"provider(s) at once. Upgrade to follow more.")

        db.execute("""INSERT INTO subscriptions 
            (follower_id,provider_id,risk_pct,max_lot,min_confidence,auto_copy,auto_execute,pairs_filter)
            VALUES (?,?,?,?,?,?,?,?)""",
            (user["id"], req.provider_id, req.risk_pct, req.max_lot,
             req.min_confidence, int(req.auto_copy), int(req.auto_execute), json.dumps(req.pairs_filter)))
        
        # Update provider follower count
        db.execute("UPDATE providers SET followers_count=followers_count+1 WHERE user_id=?",
                   (req.provider_id,))
        
        mode_msg = "You are now copying trades automatically." if req.auto_copy else \
                   "Manual mode — you'll get a notification to review and approve each signal before it opens."
        notify_user(db, user["id"], "copy", "Copy Trading Activated", mode_msg, "/copy")
        return {"success": True, "message": mode_msg}

@app.delete("/copy/unsubscribe/{provider_id}")
def unsubscribe(provider_id: int, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("UPDATE subscriptions SET is_active=0 WHERE follower_id=? AND provider_id=?",
                   (user["id"], provider_id))
        db.execute("UPDATE providers SET followers_count=MAX(0,followers_count-1) WHERE user_id=?",
                   (provider_id,))
        return {"success": True}

@app.get("/copy/my-trades")
def my_copy_trades(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute("""
            SELECT ct.*, COALESCE(u.username, 'ForexPro AI') as provider_name,
                   s.pair as sig_pair, s.timeframe,
                   s.direction as sig_direction, s.ai_analysis, s.candle_pattern
            FROM copy_trades ct
            LEFT JOIN users u ON ct.provider_id=u.id
            LEFT JOIN signals s ON ct.signal_id=s.id
            WHERE ct.follower_id=?
            ORDER BY ct.created_at DESC LIMIT 50
        """, (user["id"],)).fetchall()
        trades = []
        quote_cache = {}
        for r in rows:
            d = dict(r)
            # ct.pair/ct.direction (set directly on quick trades) win when present,
            # otherwise fall back to the linked signal's pair/direction.
            d["pair"] = d.get("pair") or d.pop("sig_pair", None)
            d["direction"] = d.get("direction") or d.pop("sig_direction", None)

            # Live floating P&L for still-open trades — previously pnl_usd/pnl_pips
            # only ever got set when a trade closed, so the UI showed a flat 0 the
            # entire time a position was open regardless of how it was actually doing.
            if d["status"] == "open" and d["pair"] and d.get("entry_price"):
                pair = d["pair"]
                if pair not in quote_cache:
                    try: quote_cache[pair] = float(get_live_quote(pair)["price"])
                    except Exception: quote_cache[pair] = None
                price = quote_cache[pair]
                if price is not None:
                    _, _, pip, _, _ = PAIR_CONFIG.get(pair, PAIR_CONFIG["EURUSD"])
                    is_buy = d["direction"] == "BUY"
                    pnl_pips = (price - d["entry_price"]) / pip * (1 if is_buy else -1)
                    d["pnl_pips"] = round(pnl_pips, 1)
                    d["pnl_usd"] = pip_value_usd(pair, pnl_pips, d["lot_size"])
                    d["current_price"] = round(price, 5)
                    d["pnl_is_live"] = True
            trades.append(d)

        closed = [t for t in trades if t["status"] == "closed"]
        open_trades = [t for t in trades if t["status"] == "open"]
        realized_pnl = sum(t["pnl_usd"] or 0 for t in closed)
        floating_pnl = sum(t["pnl_usd"] or 0 for t in open_trades)
        wins = sum(1 for t in closed if (t["pnl_usd"] or 0) > 0)
        losses = sum(1 for t in closed if (t["pnl_usd"] or 0) <= 0)
        return {"trades": trades,
                "stats": {"total": len(trades), "open": len(open_trades),
                          "wins": wins, "losses": losses,
                          "total_pnl_usd": round(realized_pnl, 2),
                          "floating_pnl_usd": round(floating_pnl, 2)}}

@app.get("/copy/subscriptions")
def my_subscriptions(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute("""
            SELECT s.*, p.display_name, p.win_rate, p.total_pips, p.monthly_pips,
                   p.followers_count, p.is_verified, u.username
            FROM subscriptions s
            JOIN providers p ON s.provider_id=p.user_id
            JOIN users u ON p.user_id=u.id
            WHERE s.follower_id=? AND s.is_active=1
        """, (user["id"],)).fetchall()
        return {"subscriptions": [dict(r) for r in rows]}

@app.put("/copy/subscription/{provider_id}")
def update_subscription(provider_id: int, req: SubscribeReq, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("""UPDATE subscriptions SET risk_pct=?,max_lot=?,min_confidence=?,
                      auto_copy=?,auto_execute=?,pairs_filter=? WHERE follower_id=? AND provider_id=?""",
                   (req.risk_pct, req.max_lot, req.min_confidence, int(req.auto_copy),
                    int(req.auto_execute), json.dumps(req.pairs_filter), user["id"], provider_id))
        return {"success": True}

# ── Prices ────────────────────────────────────────────────────────────────────
@app.get("/prices/pairs")
def list_pairs():
    """Every pair the platform can price/chart/generate signals for — the
    frontend's pair search/picker pulls this instead of hardcoding a list,
    so adding a pair here is the only place it needs to be added."""
    groups = {
        "Majors":  ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD"],
        "EUR crosses": ["EURGBP","EURJPY","EURAUD","EURCAD","EURCHF","EURNZD"],
        "GBP crosses": ["GBPJPY","GBPAUD","GBPCAD","GBPCHF","GBPNZD"],
        "Other crosses": ["AUDCAD","AUDCHF","AUDJPY","AUDNZD","CADCHF","CADJPY","CHFJPY","NZDCAD","NZDCHF","NZDJPY"],
        "Exotics": ["USDSGD","USDZAR","USDMXN","USDTRY"],
        "Metals & Crypto": ["XAUUSD","XAGUSD","BTCUSD","ETHUSD"],
    }
    return {
        "pairs": [
            {"symbol": p, "display": PAIR_CONFIG[p][4], "group": g}
            for g, syms in groups.items() for p in syms if p in PAIR_CONFIG
        ],
        "groups": list(groups.keys()),
    }

@app.get("/prices/live")
def live_prices(pairs: str = Query("EURUSD,GBPUSD,USDJPY,AUDUSD,XAUUSD,BTCUSD")):
    pair_list = [p.strip() for p in pairs.split(",") if p.strip() in PAIR_CONFIG]
    prices = [get_live_quote(p) for p in pair_list]
    return {"prices": prices, "updated_at": datetime.now().isoformat()}

@app.get("/prices/chart")
def price_chart(pair: str = "EURUSD", timeframe: str = "H1", candles: int = 500):
    if pair not in PAIR_CONFIG: raise HTTPException(400, "Unknown pair")
    if timeframe not in TF_MAP: raise HTTPException(400, "Unknown timeframe")
    df = get_ohlcv(pair, timeframe, candles + 250)
    df = add_indicators(df)
    tail = df.tail(candles)
    _, _, pip_sz, _, _ = PAIR_CONFIG[pair]
    records = []
    for ts, row in tail.iterrows():
        rng = max(float(row["high"]) - float(row["low"]), pip_sz * 0.1)
        # No real broker tick-volume feed — approximate relative activity from
        # candle range + body size so the chart still has a meaningful volume pane.
        volume = int(rng / pip_sz * 37 + abs(float(row["close"]) - float(row["open"])) / pip_sz * 20)
        records.append({
            "time": to_unix_utc(ts), "open": round(float(row["open"]),5), # type: ignore
            "high": round(float(row["high"]),5), "low": round(float(row["low"]),5),
            "close": round(float(row["close"]),5), "ema20": round(float(row["ema20"]),5),
            "ema50": round(float(row["ema50"]),5), "bb_up": round(float(row["bb_up"]),5),
            "bb_low": round(float(row["bb_low"]),5), "rsi": round(float(row["rsi"]),2),
            "macd_h": round(float(row["macd_h"]),6), "stoch_k": round(float(row["stoch_k"]),2),
            "volume": max(volume, 1),
        })
    direction = "BUY" if float(tail["ema20"].iloc[-1]) > float(tail["ema50"].iloc[-1]) else "SELL"
    return {
        "pair": pair, "timeframe": timeframe, "candles": records,
        "support_resistance": detect_support_resistance(df),
        "trendline": detect_trendline(df),
        "markers": build_markers(df, direction),
        "source": "live" if "live" in str(df.index[0]) else "simulated",
    }

# ── Education ─────────────────────────────────────────────────────────────────
@app.get("/education/courses")
def list_courses(user=Depends(get_optional_user)):
    with get_db() as db:
        courses = db.execute("SELECT id,title,description,category,level,created_at FROM education_courses").fetchall()
        result = []
        for c in courses:
            cd = dict(c)
            if user:
                prog = db.execute("SELECT * FROM user_progress WHERE user_id=? AND course_id=?",
                                  (user["id"], c["id"])).fetchone()
                cd["progress"] = dict(prog) if prog else {"lesson_idx":0,"completed":0,"score":0}
            # Count lessons
            full = db.execute("SELECT lessons FROM education_courses WHERE id=?", (c["id"],)).fetchone()
            try:
                parsed = json.loads(full["lessons"])
                cd["lesson_count"] = len(parsed)
                cd["total_duration"] = sum(int(l.get("duration") or 0) for l in parsed)
            except Exception:
                cd["lesson_count"] = 0
                cd["total_duration"] = 0
            result.append(cd)
        return {"courses": result}

@app.get("/education/courses/{course_id}")
def get_course(course_id: int, user=Depends(get_optional_user)):
    with get_db() as db:
        course = db.execute("SELECT * FROM education_courses WHERE id=?", (course_id,)).fetchone()
        if not course: raise HTTPException(404, "Course not found")
        cd = dict(course)
        try: cd["lessons"] = json.loads(cd["lessons"])
        except: cd["lessons"] = []
        if user:
            prog = db.execute("SELECT * FROM user_progress WHERE user_id=? AND course_id=?",
                              (user["id"], course_id)).fetchone()
            cd["progress"] = dict(prog) if prog else {"lesson_idx":0,"completed":0,"score":0}
        return cd

@app.post("/education/progress")
def update_progress(req: UpdateProgressReq, user=Depends(get_current_user)):
    with get_db() as db:
        existing = db.execute("SELECT id FROM user_progress WHERE user_id=? AND course_id=?",
                              (user["id"], req.course_id)).fetchone()
        if existing:
            db.execute("""UPDATE user_progress SET lesson_idx=?,completed=?,score=?,
                          updated_at=datetime('now') WHERE user_id=? AND course_id=?""",
                       (req.lesson_idx, int(req.completed), req.score, user["id"], req.course_id))
        else:
            db.execute("""INSERT INTO user_progress (user_id,course_id,lesson_idx,completed,score)
                          VALUES (?,?,?,?,?)""",
                       (user["id"], req.course_id, req.lesson_idx, int(req.completed), req.score))
        if req.completed:
            notify_user(db, user["id"], "education", "Course Completed!",
                        f"You completed a course with score {req.score}%!", "/education")
        return {"success": True}

@app.get("/education/my-progress")
def my_progress(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute("""
            SELECT up.*, ec.title, ec.category, ec.level
            FROM user_progress up JOIN education_courses ec ON up.course_id=ec.id
            WHERE up.user_id=?
        """, (user["id"],)).fetchall()
        completed = sum(1 for r in rows if r["completed"])
        return {"progress": [dict(r) for r in rows],
                "stats": {"enrolled": len(rows), "completed": completed,
                          "in_progress": len(rows)-completed}}

# ── Trade Journal ─────────────────────────────────────────────────────────────
@app.post("/journal")
def add_journal(req: JournalEntryReq, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("""INSERT INTO trade_journal 
            (user_id,pair,direction,entry_price,exit_price,lot_size,pnl_usd,pnl_pips,notes,emotion,setup)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user["id"], req.pair, req.direction, req.entry_price, req.exit_price,
             req.lot_size, req.pnl_usd, req.pnl_pips, req.notes, req.emotion, req.setup))
        return {"success": True}

@app.get("/journal")
def get_journal(user=Depends(get_current_user)):
    """Combines the trader's own manual entries with their closed copy trades —
    previously these were two disconnected things: Copy Trading kept showing
    closed/failed trades forever (cluttering the "what's still open" view),
    while Journal only ever showed what someone typed in by hand and never
    picked up a closed copy trade at all. Now closed copy trades land here
    automatically, same as a manual entry would, tagged source='copy' so the
    UI can badge them differently."""
    with get_db() as db:
        manual_rows = db.execute(
            "SELECT * FROM trade_journal WHERE user_id=? ORDER BY traded_at DESC LIMIT 100",
            (user["id"],)).fetchall()
        manual = [{**dict(r), "source": "manual"} for r in manual_rows]

        copy_rows = db.execute("""
            SELECT ct.id, ct.pair, ct.direction, ct.entry_price, ct.close_price as exit_price,
                   ct.lot_size, ct.pnl_usd, ct.pnl_pips, ct.closed_at as traded_at, ct.status,
                   ct.execution_mode, ct.fail_reason, u.username as provider_name
            FROM copy_trades ct LEFT JOIN users u ON ct.provider_id = u.id
            WHERE ct.follower_id=? AND ct.status IN ('closed','failed')
            ORDER BY ct.closed_at DESC LIMIT 100
        """, (user["id"],)).fetchall()
        copy = [{**dict(r), "source": "copy", "notes": None, "emotion": None, "setup": None} for r in copy_rows]

        trades = sorted(manual + copy, key=lambda t: t.get("traded_at") or "", reverse=True)[:150]
        total_pnl = sum(t["pnl_usd"] or 0 for t in trades)
        wins = sum(1 for t in trades if (t["pnl_usd"] or 0) > 0)
        best = max((t["pnl_usd"] or 0 for t in trades), default=0)
        worst = min((t["pnl_usd"] or 0 for t in trades), default=0)
        return {"trades": trades,
                "stats": {"total": len(trades), "wins": wins, "losses": len(trades)-wins,
                          "win_rate": round(wins/max(len(trades),1)*100,1),
                          "total_pnl": round(total_pnl,2),
                          "best_trade": round(best,2), "worst_trade": round(worst,2)}}

# ── Notifications ─────────────────────────────────────────────────────────────
# ── Telegram linking ─────────────────────────────────────────────────────────
class TelegramLinkConfirmReq(BaseModel):
    code: str
    chat_id: str
    username: str = ""

@app.post("/telegram/link/start")
def telegram_link_start(user=Depends(get_current_user)):
    """User taps 'Connect Telegram' in Settings — generates a short code and a
    deep link that opens the bot with /start <code> pre-filled. The bot calls
    /telegram/link/confirm below once the user actually sends that /start."""
    if not telegram_configured():
        raise HTTPException(400, "Telegram bot isn't configured on this server yet (TELEGRAM_BOT_TOKEN missing).")
    code = generate_link_code()
    expires = (datetime.now() + timedelta(minutes=10)).isoformat()
    with get_db() as db:
        db.execute("UPDATE users SET telegram_link_code=?, telegram_link_expires=? WHERE id=?",
                   (code, expires, user["id"]))
    return {"code": code, "deep_link": bot_deep_link(code), "expires_at": expires}

@app.post("/telegram/link/confirm")
def telegram_link_confirm(req: TelegramLinkConfirmReq):
    """Called by the Telegram bot process itself (not the frontend) when a user
    sends /start <code>. No user auth here since the bot isn't a logged-in
    session — the short-lived code is the credential."""
    with get_db() as db:
        row = db.execute("SELECT id, telegram_link_expires FROM users WHERE telegram_link_code=?",
                         (req.code,)).fetchone()
        if not row:
            return {"linked": False, "reason": "Invalid or already-used code"}
        try:
            if datetime.fromisoformat(row["telegram_link_expires"]) < datetime.now():
                return {"linked": False, "reason": "Code expired — generate a new one in Settings"}
        except Exception:
            return {"linked": False, "reason": "Code expired — generate a new one in Settings"}
        db.execute("""UPDATE users SET telegram_chat_id=?, telegram_username=?,
                      telegram_link_code=NULL, telegram_link_expires=NULL WHERE id=?""",
                   (req.chat_id, req.username, row["id"]))
        notify_user(db, row["id"], "system", "Telegram connected ✅",
                    "You'll now get a Telegram message whenever a provider you follow posts a new signal.", "/settings")
    return {"linked": True}

@app.get("/telegram/status")
def telegram_status(user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute("SELECT telegram_chat_id, telegram_username FROM users WHERE id=?",
                         (user["id"],)).fetchone()
    return {"connected": bool(row and row["telegram_chat_id"]),
            "username": row["telegram_username"] if row else None,
            "bot_configured": telegram_configured()}

@app.post("/telegram/unlink")
def telegram_unlink(user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("UPDATE users SET telegram_chat_id=NULL, telegram_username=NULL WHERE id=?", (user["id"],))
    return {"unlinked": True}

# ── Web Push (PWA notifications) ────────────────────────────────────────────
class PushSubscribeReq(BaseModel):
    endpoint: str
    p256dh: str
    auth: str

@app.get("/push/vapid-public-key")
def push_vapid_public_key():
    return {"key": VAPID_PUBLIC_KEY, "configured": push_configured()}

@app.post("/push/subscribe")
def push_subscribe(req: PushSubscribeReq, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("""INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
                      VALUES (?,?,?,?)
                      ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id,
                        p256dh=excluded.p256dh, auth=excluded.auth""",
                   (user["id"], req.endpoint, req.p256dh, req.auth))
    return {"subscribed": True}

@app.post("/push/unsubscribe")
def push_unsubscribe(endpoint: str, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("DELETE FROM push_subscriptions WHERE endpoint=? AND user_id=?", (endpoint, user["id"]))
    return {"unsubscribed": True}

# push_to_user / notify_user now live in push_send.py — shared with
# mpesa.py, bridge.py, and payments.py so every event (not just the ones in
# this file) can fire a real push, not just an in-app notification row.


# ── Admin ─────────────────────────────────────────────────────────────────────
def _require_admin(user):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")

@app.get("/admin/revenue")
def admin_revenue(user=Depends(get_current_user)):
    _require_admin(user)
    with get_db() as db:
        platform = db.execute("""
            SELECT COUNT(DISTINCT provider_id) providers_earning,
                   COUNT(*) fee_events,
                   COALESCE(SUM(amount_usd),0) total_commission_paid_to_providers
            FROM provider_earnings
        """).fetchone()
        subs_revenue = db.execute("""
            SELECT COUNT(*) c, COALESCE(SUM(amount),0) total_kes
            FROM payments WHERE status='success' AND kind='subscription'
        """).fetchone()
        wallet_deposits = db.execute("""
            SELECT COUNT(*) c, COALESCE(SUM(amount_usd),0) total_usd
            FROM wallet_transactions WHERE type='deposit' AND status='completed'
        """).fetchone()
        wallet_withdrawals = db.execute("""
            SELECT COUNT(*) c, COALESCE(SUM(amount_usd),0) total_usd
            FROM wallet_transactions WHERE type='withdrawal' AND status='completed'
        """).fetchone()
        pending_withdrawals = db.execute("""
            SELECT COUNT(*) c, COALESCE(SUM(amount_usd),0) total_usd
            FROM wallet_transactions WHERE type='withdrawal' AND status='pending'
        """).fetchone()
        per_provider = db.execute("""
            SELECT p.user_id, u.username, p.display_name, p.subscription_type, p.commission_pct,
                   p.followers_count, p.total_earned_usd, p.win_rate, p.total_signals
            FROM providers p JOIN users u ON p.user_id=u.id
            WHERE p.is_active=1 ORDER BY p.total_earned_usd DESC LIMIT 50
        """).fetchall()
        user_counts = db.execute("""
            SELECT plan, COUNT(*) c FROM users GROUP BY plan
        """).fetchall()
        open_trades = db.execute("SELECT COUNT(*) c, COALESCE(SUM(margin_used),0) capital FROM copy_trades WHERE status='open'").fetchone()

        return {
            "provider_commissions": {
                "providers_earning": platform["providers_earning"],
                "fee_events": platform["fee_events"],
                "total_paid_to_providers_usd": round(platform["total_commission_paid_to_providers"], 2),
            },
            "subscription_revenue": {"successful_payments": subs_revenue["c"], "total_kes": subs_revenue["total_kes"]},
            "wallet": {
                "deposits": {"count": wallet_deposits["c"], "total_usd": round(wallet_deposits["total_usd"], 2)},
                "withdrawals": {"count": wallet_withdrawals["c"], "total_usd": round(wallet_withdrawals["total_usd"], 2)},
                "pending_withdrawals": {"count": pending_withdrawals["c"], "total_usd": round(pending_withdrawals["total_usd"], 2)},
            },
            "open_positions": {"count": open_trades["c"], "capital_deployed_usd": round(open_trades["capital"], 2)},
            "users_by_plan": {r["plan"]: r["c"] for r in user_counts},
            "top_providers": [dict(r) for r in per_provider],
        }

@app.get("/admin/pending-withdrawals")
def admin_pending_withdrawals(user=Depends(get_current_user)):
    _require_admin(user)
    with get_db() as db:
        rows = db.execute("""
            SELECT wt.*, u.username, u.email FROM wallet_transactions wt
            JOIN users u ON wt.user_id = u.id
            WHERE wt.type='withdrawal' AND wt.status='pending' ORDER BY wt.created_at ASC
        """).fetchall()
        return {"withdrawals": [dict(r) for r in rows]}

# ── Wallet ────────────────────────────────────────────────────────────────────
class WithdrawReq(BaseModel):
    amount_usd: float
    phone: str

@app.get("/wallet/summary")
def wallet_summary(user=Depends(get_current_user)):
    with get_db() as db:
        fresh = db.execute("SELECT balance, equity FROM users WHERE id=?", (user["id"],)).fetchone()
        pending_withdrawals = db.execute(
            "SELECT COALESCE(SUM(amount_usd),0) FROM wallet_transactions WHERE user_id=? AND type='withdrawal' AND status='pending'",
            (user["id"],)).fetchone()[0]
        return {"balance": fresh["balance"], "equity": fresh["equity"],
                "pending_withdrawals_usd": pending_withdrawals}

@app.get("/wallet/transactions")
def wallet_transactions(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM wallet_transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
            (user["id"],)).fetchall()
        return {"transactions": [dict(r) for r in rows]}

@app.post("/wallet/withdraw/request")
def request_withdrawal(req: WithdrawReq, user=Depends(get_current_user)):
    """Queues a withdrawal request and reserves the funds immediately (so the same
    balance can't be withdrawn twice or spent on a trade while pending). Actual
    payout (M-Pesa B2C or bank transfer) is NOT automated — Safaricom B2C requires
    a separate business registration/approval beyond what STK push (receiving
    payments) needs, so this creates a request an admin fulfills manually and
    marks complete via /wallet/withdrawals/{id}/approve."""
    if req.amount_usd <= 0:
        raise HTTPException(400, "Amount must be positive")
    with get_db() as db:
        balance = db.execute("SELECT balance FROM users WHERE id=?", (user["id"],)).fetchone()["balance"]
        if balance < req.amount_usd:
            raise HTTPException(400, f"Insufficient balance — you have ${balance:.2f}")
        db.execute("UPDATE users SET balance = balance - ? WHERE id=?", (req.amount_usd, user["id"]))
        cur = db.execute("""INSERT INTO wallet_transactions
            (user_id, type, amount_usd, method, status, phone)
            VALUES (?,'withdrawal',?,'mpesa','pending',?)""",
            (user["id"], req.amount_usd, req.phone))
        notify_user(db, user["id"], "billing", "Withdrawal requested",
             f"${req.amount_usd:.2f} reserved and queued for payout to {req.phone}. "
             f"This is processed manually — you'll get a notification once it's sent.", "/wallet")
        return {"requested": True, "transaction_id": cur.lastrowid}

@app.post("/wallet/withdrawals/{tx_id}/approve")
def approve_withdrawal(tx_id: int, mpesa_receipt: str = "", user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    with get_db() as db:
        tx = db.execute("SELECT * FROM wallet_transactions WHERE id=? AND type='withdrawal' AND status='pending'",
                        (tx_id,)).fetchone()
        if not tx: raise HTTPException(404, "Pending withdrawal not found")
        db.execute("""UPDATE wallet_transactions SET status='completed', mpesa_receipt=?,
                      processed_at=datetime('now') WHERE id=?""", (mpesa_receipt, tx_id))
        notify_user(db, tx["user_id"], "billing", "Withdrawal sent ✅",
             f"${tx['amount_usd']:.2f} has been sent to {tx['phone']}." +
             (f" M-Pesa ref: {mpesa_receipt}" if mpesa_receipt else ""), "/wallet")
        return {"approved": True}

@app.post("/wallet/withdrawals/{tx_id}/reject")
def reject_withdrawal(tx_id: int, reason: str = "", user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    with get_db() as db:
        tx = db.execute("SELECT * FROM wallet_transactions WHERE id=? AND type='withdrawal' AND status='pending'",
                        (tx_id,)).fetchone()
        if not tx: raise HTTPException(404, "Pending withdrawal not found")
        db.execute("""UPDATE wallet_transactions SET status='rejected', admin_note=?,
                      processed_at=datetime('now') WHERE id=?""", (reason, tx_id))
        db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (tx["amount_usd"], tx["user_id"]))
        notify_user(db, tx["user_id"], "billing", "Withdrawal declined",
             f"${tx['amount_usd']:.2f} was returned to your balance. Reason: {reason or 'Not specified'}", "/wallet")
        return {"rejected": True}

@app.get("/notifications")
def get_notifications(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
            (user["id"],)).fetchall()
        return {"notifications": [dict(r) for r in rows]}

@app.post("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: int, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notif_id, user["id"]))
    return {"success": True}

@app.post("/notifications/read-all")
def mark_all_notifications_read(user=Depends(get_current_user)):
    with get_db() as db:
        db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["id"],))
    return {"success": True}

# ── Dashboard Stats ───────────────────────────────────────────────────────────
@app.get("/account/usage")
def account_usage(user=Depends(get_current_user)):
    """Current plan limits + today's usage, so the frontend can show progress
    ('3/5 signals used today') and gate buttons before the user even hits a 403."""
    plan = effective_plan(user)
    limits = plan_limits(plan)
    with get_db() as db:
        signals_today = db.execute(
            "SELECT COUNT(*) c FROM signals WHERE provider_id=? AND date(created_at)=date('now')",
            (user["id"],)).fetchone()["c"]
        copies_today = db.execute(
            "SELECT COUNT(*) c FROM copy_trades WHERE follower_id=? AND date(opened_at)=date('now')",
            (user["id"],)).fetchone()["c"]
        active_subs = db.execute(
            "SELECT COUNT(*) c FROM subscriptions WHERE follower_id=? AND is_active=1",
            (user["id"],)).fetchone()["c"]
        is_provider = db.execute(
            "SELECT id FROM providers WHERE user_id=?", (user["id"],)).fetchone() is not None
    return {
        "plan": user.get("plan", "free"), "effective_plan": plan, "limits": limits,
        "usage": {
            "signals_today": signals_today, "copies_today": copies_today,
            "active_subscriptions": active_subs,
        },
        "is_provider": is_provider,
    }

@app.get("/dashboard/stats")
def dashboard_stats(user=Depends(get_current_user)):
    with get_db() as db:
        uid = user["id"]
        subs = db.execute("SELECT COUNT(*) FROM subscriptions WHERE follower_id=? AND is_active=1",(uid,)).fetchone()[0]
        copies = db.execute("SELECT COUNT(*) FROM copy_trades WHERE follower_id=?",(uid,)).fetchone()[0]
        pnl = db.execute("SELECT COALESCE(SUM(pnl_usd),0) FROM copy_trades WHERE follower_id=?",(uid,)).fetchone()[0]
        sig_count = db.execute("SELECT COUNT(*) FROM signals WHERE provider_id=?",(uid,)).fetchone()[0]
        notifs = db.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",(uid,)).fetchone()[0]
        prog = db.execute("SELECT COUNT(*) FROM user_progress WHERE user_id=? AND completed=1",(uid,)).fetchone()[0]
        return {
            "balance": user["balance"], "equity": user["equity"],
            "active_subscriptions": subs, "copy_trades": copies,
            "total_pnl_usd": round(float(pnl),2), "signals_generated": sig_count,
            "unread_notifications": notifs, "courses_completed": prog,
        }

# ── Real-time WebSocket Architecture ───────────────────────────────────────────
# Channels:
#   /ws/prices?pairs=EURUSD,GBPUSD   -> tick-level price updates, ~1.5s cadence, diffs only
#   /ws/candles?pair=EURUSD&timeframe=H1 -> live-forming candle updates + candle_closed events
#   /ws/signals                      -> broadcast of every newly generated signal (manual or auto)
MAIN_LOOP: Optional[asyncio.AbstractEventLoop] = None

class ConnectionManager:
    def __init__(self):
        self.channels: dict[str, set] = {"prices": set(), "signals": set(), "candles": set()}
        # Per-connection pair subscription for the "prices" channel — see
        # price_broadcaster_loop for why this replaced a single shared broadcast.
        self.price_pairs: dict = {}

    async def connect(self, channel: str, ws: WebSocket, pairs: list = None):
        await ws.accept()
        self.channels.setdefault(channel, set()).add(ws)
        if channel == "prices" and pairs:
            self.price_pairs[ws] = pairs

    def disconnect(self, channel: str, ws: WebSocket):
        self.channels.get(channel, set()).discard(ws)
        self.price_pairs.pop(ws, None)

    async def broadcast(self, channel: str, message: dict):
        dead = []
        for ws in list(self.channels.get(channel, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.channels.get(channel, set()).discard(ws)

manager = ConnectionManager()

def broadcast_threadsafe(channel: str, message: dict):
    """Call from sync (threadpool) request handlers to push a message onto a ws channel."""
    if MAIN_LOOP is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(channel, message), MAIN_LOOP)
    except Exception as e:
        print(f"[WS] broadcast failed: {e}")

DEFAULT_TICK_PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD","XAUUSD","BTCUSD"]

async def price_broadcaster_loop():
    """Background task: pushes fresh quotes to /ws/prices subscribers every ~1.5s.
    Each connection gets only the pairs it actually asked for via ?pairs= — this
    used to broadcast one fixed 9-pair list to every connection regardless of what
    was requested, so any watchlist pair outside that fixed set (most of the 36
    pairs the platform supports) never received a live tick over the socket at
    all, even though /prices/live (the REST endpoint) worked fine for them."""
    while True:
        try:
            conns = list(manager.channels.get("prices", set()))
            if conns:
                needed = set()
                for ws in conns:
                    needed.update(manager.price_pairs.get(ws) or DEFAULT_TICK_PAIRS)
                # Fetch each unique pair once and share it across every connection
                # asking for it, rather than re-fetching per connection.
                quote_cache = {p: get_live_quote(p) for p in needed}
                ts = datetime.now().isoformat()
                dead = []
                for ws in conns:
                    pair_list = manager.price_pairs.get(ws) or DEFAULT_TICK_PAIRS
                    payload = {"type": "prices",
                               "data": [quote_cache[p] for p in pair_list if p in quote_cache],
                               "ts": ts}
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    manager.disconnect("prices", ws)
        except Exception as e:
            print(f"[WS] price loop error: {e}")
        await asyncio.sleep(1.5)

@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket, pairs: str = Query(None)):
    pair_list = [p.strip() for p in (pairs or "").split(",") if p.strip() in PAIR_CONFIG] or None
    await manager.connect("prices", websocket, pairs=pair_list)
    try:
        while True:
            await websocket.receive_text()  # keepalive / ignored pings from client
    except WebSocketDisconnect:
        manager.disconnect("prices", websocket)

@app.websocket("/ws/candles")
async def ws_candles(websocket: WebSocket, pair: str = "EURUSD", timeframe: str = "H1"):
    """Dedicated per-connection stream: live-forming candle updates + candle_closed events
    for exactly the pair/timeframe this client is viewing (no cross-talk between viewers)."""
    if pair not in PAIR_CONFIG or timeframe not in TF_MAP:
        await websocket.close(code=4400)
        return
    await websocket.accept()
    last_bar_ts: Optional[str] = None
    try:
        while True:
            try:
                df = get_ohlcv(pair, timeframe, 260)
                df = add_indicators(df)
                last_ts = str(df.index[-1])[:16]
                quote = get_live_quote(pair)
                live_price = quote.get("bid") or quote.get("price")
                row = df.iloc[-1]
                forming = {
                    "time": to_unix_utc(df.index[-1]),
                    "open": round(float(row["open"]), 5),
                    "high": round(max(float(row["high"]), live_price), 5) if live_price else round(float(row["high"]),5),
                    "low":  round(min(float(row["low"]), live_price), 5) if live_price else round(float(row["low"]),5),
                    "close": round(float(live_price if live_price else row["close"]), 5),
                }
                closed = last_bar_ts is not None and last_bar_ts != last_ts
                last_bar_ts = last_ts

                if closed:
                    direction = "BUY" if row["ema20"] > row["ema50"] else "SELL"
                    payload = {
                        "type": "candle_closed", "pair": pair, "timeframe": timeframe,
                        "candle": forming,
                        "markers": build_markers(df, direction),
                        "support_resistance": detect_support_resistance(df),
                        "trendline": detect_trendline(df),
                    }
                else:
                    payload = {
                        "type": "candle_update", "pair": pair, "timeframe": timeframe,
                        "candle": forming, "price": live_price,
                    }
                try:
                    await websocket.send_json(payload)
                except Exception:
                    break  # client gone
            except Exception as e:
                print(f"[WS] candle loop error ({pair} {timeframe}): {e}")
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/signals")
async def ws_signals(websocket: WebSocket):
    await manager.connect("signals", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("signals", websocket)

AUTO_SIGNAL_ROTATION = [("EURUSD","H1"), ("GBPUSD","M30"), ("XAUUSD","H1"),
                         ("USDJPY","M15"), ("BTCUSD","H1"), ("GBPJPY","H4")]

async def auto_signal_loop():
    """Generates a fresh AI signal on rotation and broadcasts it, so /ws/signals stays live
    even without a user manually clicking 'generate' — new candles => new signal checks."""
    i = 0
    while True:
        await asyncio.sleep(40)
        try:
            if not manager.channels.get("signals"):
                continue
            pair, tf = AUTO_SIGNAL_ROTATION[i % len(AUTO_SIGNAL_ROTATION)]
            i += 1
            df = get_ohlcv(pair, tf, 260)
            df = add_indicators(df)
            sig = build_signal(pair, tf, df, provider_id=None)
            if sig["confidence"] < 60:
                continue  # only surface actionable auto-signals
            ohlcv = sig.pop("ohlcv", None)
            chart_data = {"ohlcv": ohlcv, "markers": sig.get("markers", []),
                          "support_resistance": sig.get("support_resistance", []),
                          "trendline": sig.get("trendline")}
            with get_db() as db:
                cur = db.execute("""
                    INSERT INTO signals (provider_id,pair,timeframe,direction,strength,confidence,
                    entry_price,stop_loss,take_profit,sl_pips,tp_pips,risk_reward,rsi,macd,
                    ema20,ema50,bb_upper,bb_lower,stoch_k,atr,candle_pattern,chart_pattern,
                    entry_time,ai_analysis,expires_at,chart_data)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (None, sig["pair"], sig["timeframe"], sig["direction"], sig["strength"],
                      sig["confidence"], sig["entry_price"], sig["stop_loss"], sig["take_profit"],
                      sig["sl_pips"], sig["tp_pips"], sig["risk_reward"], sig["rsi"], sig["macd"],
                      sig["ema20"], sig["ema50"], sig["bb_upper"], sig["bb_lower"], sig["stoch_k"],
                      sig["atr"], sig["candle_pattern"], sig["chart_pattern"], sig["entry_time"],
                      sig["ai_analysis"], sig["expires_at"], json.dumps(chart_data)))
                sig["id"] = cur.lastrowid
            sig["ohlcv"] = ohlcv
            sig["provider_name"] = "ForexPro AI"
            await manager.broadcast("signals", {"type": "new_signal", "data": sig})
        except Exception as e:
            print(f"[AutoSignal] error: {e}")

async def settlement_loop():
    """Watches every 'active' signal against live prices and closes it (+ every
    copy_trade riding on it) the moment price hits TP, SL, or the signal expires.
    This is what makes win-rates, pips, and copy-trade P&L actually move instead
    of sitting at zero forever."""
    while True:
        await asyncio.sleep(20)
        try:
            settle_once()
        except Exception as e:
            print(f"[Settlement] error: {e}")

def check_pending_triggers():
    """Manual provider signals saved with execution_mode='pending' sit here until
    price actually reaches trigger_price, then activate exactly like an
    'immediate' signal would — provider's own master trade opens, followers get
    distributed to. Expired pending signals (48h) get marked expired instead."""
    with get_db() as db:
        pending = db.execute("SELECT * FROM signals WHERE status='pending_trigger'").fetchall()
        for sig in pending:
            try:
                if sig["expires_at"] and datetime.fromisoformat(sig["expires_at"]) < datetime.now():
                    db.execute("UPDATE signals SET status='expired' WHERE id=?", (sig["id"],))
                    continue
                quote = get_live_quote(sig["pair"])
                price = float(quote["price"])
                trigger = float(sig["trigger_price"])
                _, _, pip, _, _ = PAIR_CONFIG.get(sig["pair"], PAIR_CONFIG["EURUSD"])
                # Fire once price is close to the trigger. This loop only checks
                # every 20s, so a tight tolerance can miss a fast-moving price
                # jumping straight past the level between checks — a few pips of
                # slack trades a little precision for actually firing reliably.
                hit = abs(price - trigger) <= (pip * 3)
                if not hit:
                    continue
                prow = db.execute("SELECT * FROM providers WHERE user_id=?", (sig["provider_id"],)).fetchone()
                if not prow:
                    db.execute("UPDATE signals SET status='expired' WHERE id=?", (sig["id"],))
                    continue
                db.execute("UPDATE signals SET status='active', entry_price=? WHERE id=?", (price, sig["id"]))
                _activate_manual_signal(db, sig["provider_id"], sig["id"], sig, prow)
                notify_user(db, sig["provider_id"], "signal", f"Pending signal triggered: {sig['pair']}",
                     f"Price hit your trigger ({trigger}) — trade opened at {price}.", "/signals")
            except Exception as e:
                print(f"[PendingTrigger] error on signal {sig['id']}: {e}")

def settle_once():
    """One settlement pass — pulled out of the loop so it can be unit-tested directly."""
    check_pending_triggers()
    with get_db() as db:
        check_stale_bridges(db)
        active = db.execute("SELECT * FROM signals WHERE status='active'").fetchall()
        for sig in active:
            try:
                quote = get_live_quote(sig["pair"])
                price = float(quote["price"])
            except Exception:
                continue

            _, _, pip, _, _ = PAIR_CONFIG.get(sig["pair"], PAIR_CONFIG["EURUSD"])
            result, close_price = None, None
            is_buy = sig["direction"] == "BUY"

            hit_tp = (price >= sig["take_profit"]) if is_buy else (price <= sig["take_profit"])
            hit_sl = (price <= sig["stop_loss"]) if is_buy else (price >= sig["stop_loss"])
            expired = sig["expires_at"] and str(sig["expires_at"]) < datetime.now().isoformat()

            if hit_tp:
                result, close_price = "win", sig["take_profit"]
            elif hit_sl:
                result, close_price = "loss", sig["stop_loss"]
            elif expired:
                diff_pips = (price - sig["entry_price"]) / pip * (1 if is_buy else -1)
                result = "win" if diff_pips > 1 else ("loss" if diff_pips < -1 else "breakeven")
                close_price = price

            if not result:
                continue

            pnl_pips = round((close_price - sig["entry_price"]) / pip * (1 if is_buy else -1), 1)
            db.execute("""UPDATE signals SET status='closed', result=?, pnl_pips=?,
                          close_price=?, closed_at=datetime('now') WHERE id=?""",
                       (result, pnl_pips, close_price, sig["id"]))

            trades = db.execute(
                "SELECT * FROM copy_trades WHERE signal_id=? AND status IN ('pending','open') AND execution_mode != 'mt5'",
                (sig["id"],)).fetchall()
            for t in trades:
                pnl_usd = pip_value_usd(sig["pair"], pnl_pips, t["lot_size"])
                apply_trade_close(db, t["id"], close_price, pnl_pips, pnl_usd, result,
                                    "Auto-closed on TP/SL")
                notify_user(db, t["follower_id"], "trade_closed",
                     f"{sig['pair']} {result.upper()}",
                     f"Closed at {close_price} · {pnl_pips:+.1f} pips · ${pnl_usd:+.2f}", "/copy")

            if sig["provider_id"]:
                recompute_provider_stats(db, sig["provider_id"])

            broadcast_threadsafe("signals", {"type": "signal_closed", "data": {
                "id": sig["id"], "pair": sig["pair"], "result": result,
                "pnl_pips": pnl_pips, "close_price": close_price,
                "copy_trades_settled": len(trades),
            }})

@app.get("/")
def root():
    return {"api": "ForexPro v4.0", "status": "running",
            "features": ["signals","copy-trading","education","journal",
                         "live-prices-ws","live-candles-ws","live-signals-ws",
                         "mpesa-payments","stripe-payments"],
            "docs": "/docs", "db": "SQLite (forexpro.db)"}
