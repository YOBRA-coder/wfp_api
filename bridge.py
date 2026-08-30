"""
MT5 Bridge — connects a real MetaTrader 5 terminal to ForexPro.

How it works:
  1. A user generates a "bridge token" from their Profile page (a random
     secret, separate from their normal login — an EA can't do an
     interactive JWT login flow).
  2. They install the ForexProEA.mq5 (download it from /bridge/ea/download)
     in their MT5 terminal, paste in the backend URL + bridge token.
  3. The EA polls GET /bridge/pending-orders every few seconds. Any
     copy_trades marked execution_mode='mt5' and status='pending_bridge'
     come back as simple pipe-delimited lines (MQL5 has no JSON library,
     so we deliberately keep this wire format trivial to parse with
     StringSplit rather than shipping a JSON parser inside the EA).
  4. The EA places the real order in MT5, then calls
     POST /bridge/report-fill with the real ticket + fill price.
  5. When MT5 closes the position (TP/SL/manual), the EA calls
     POST /bridge/report-close with the real P&L — this is authoritative
     and is NOT touched by the simulated settlement engine in
     forexpro_main.py (which explicitly skips execution_mode='mt5' trades).

Everything here uses simple query-string parameters (not JSON bodies) on
purpose — building a URL with query params is far easier from MQL5 than
constructing/parsing JSON.
"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from trade_close import apply_trade_close
from database import get_db, generate_bridge_token, recompute_provider_stats
from auth import get_current_user
from push_send import notify_user

router = APIRouter(prefix="/bridge", tags=["mt5-bridge"])

HEARTBEAT_STALE_SECONDS = 90


def get_bridge_user(token: str = Query(..., description="Per-user bridge token from Profile")):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE bridge_token=?", (token,)).fetchone()
        if not user:
            raise HTTPException(401, "Invalid or unknown bridge token")
        return dict(user)


def check_stale_bridges(db):
    """Watchdog: alert anyone whose MT5 EA has gone quiet. If a client is
    relying on live copy trading and their terminal disconnects (closed,
    crashed, PC off, internet down), signals simply stop executing on their
    real account with no visible error — this is the one bridge event that
    genuinely needs a push, not just an in-app row, since it's silent
    otherwise. Called from the main settlement loop every ~20s; the
    'notifications' dupe-check keeps it to one alert per outage, not one
    every loop tick."""
    cutoff = (datetime.now() - timedelta(seconds=HEARTBEAT_STALE_SECONDS)).isoformat()
    rows = db.execute("""
        SELECT id, bridge_connected_at FROM users
        WHERE bridge_token IS NOT NULL AND bridge_token != ''
          AND bridge_connected_at IS NOT NULL AND bridge_connected_at < ?
    """, (cutoff,)).fetchall()
    for row in rows:
        has_open = db.execute("""
            SELECT 1 FROM copy_trades WHERE follower_id=? AND execution_mode='mt5'
              AND status IN ('open','pending_bridge') LIMIT 1
        """, (row["id"],)).fetchone()
        if not has_open:
            continue  # nothing riding on the bridge right now — don't alarm them for nothing
        dupe = db.execute("""
            SELECT 1 FROM notifications WHERE user_id=? AND title='MT5 bridge disconnected ⚠️'
              AND created_at > datetime('now','-30 minutes')
        """, (row["id"],)).fetchone()
        if dupe:
            continue
        notify_user(db, row["id"], "system", "MT5 bridge disconnected ⚠️",
            "Your MT5 terminal stopped reporting in — live copy trades won't execute until "
            "it reconnects. Check that MT5 is open and the EA is attached and running.",
            "/profile")


# ── Setup (JWT-authenticated — called from the web app, not the EA) ──────────
@router.post("/token/generate")
def generate_token(user=Depends(get_current_user)):
    token = generate_bridge_token()
    with get_db() as db:
        db.execute("UPDATE users SET bridge_token=? WHERE id=?", (token, user["id"]))
    return {"bridge_token": token}


@router.get("/status")
def bridge_status(user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute(
            """SELECT bridge_token, bridge_connected_at, mt5_real_balance, mt5_real_equity,
                      mt5_real_currency, mt5_real_login, mt5_real_server, mt5_real_leverage,
                      mt5_real_updated_at
               FROM users WHERE id=?""",
            (user["id"],)).fetchone()
    connected = False
    if row and row["bridge_connected_at"]:
        try:
            connected = datetime.fromisoformat(row["bridge_connected_at"]) > \
                datetime.now() - timedelta(seconds=HEARTBEAT_STALE_SECONDS)
        except Exception:
            connected = False
    return {
        "has_token": bool(row and row["bridge_token"]),
        "bridge_token": row["bridge_token"] if row else None,
        "connected": connected,
        "last_seen": row["bridge_connected_at"] if row else None,
        "account": {
            "balance": row["mt5_real_balance"] if row else None,
            "equity": row["mt5_real_equity"] if row else None,
            "currency": row["mt5_real_currency"] if row else None,
            "login": row["mt5_real_login"] if row else None,
            "server": row["mt5_real_server"] if row else None,
            "leverage": row["mt5_real_leverage"] if row else None,
            "updated_at": row["mt5_real_updated_at"] if row else None,
        } if row and row["mt5_real_balance"] is not None else None,
    }


@router.get("/ea/download")
def download_ea():
    """Serves the ForexPro Expert Advisor source (.mq5) — compile it in MetaEditor
    (F7) inside your MT5 terminal, then attach it to any chart."""
    path = os.path.join(os.path.dirname(__file__), "mt5_ea", "ForexProEA.mq5")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise HTTPException(404, "EA source not found on server")
    return Response(
        content=content, media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ForexProEA.mq5"},
    )


# ── EA-facing endpoints (bridge-token authenticated) ─────────────────────────
@router.get("/pending-orders", response_class=PlainTextResponse)
def pending_orders(user=Depends(get_bridge_user)):
    with get_db() as db:
        db.execute("UPDATE users SET bridge_connected_at=datetime('now') WHERE id=?", (user["id"],))

        # New positions to open
        open_rows = db.execute("""
            SELECT ct.id, COALESCE(ct.pair, s.pair) as pair, COALESCE(ct.direction, s.direction) as direction,
                   ct.lot_size, ct.entry_price, ct.stop_loss, ct.take_profit
            FROM copy_trades ct LEFT JOIN signals s ON ct.signal_id = s.id
            WHERE ct.follower_id=? AND ct.execution_mode='mt5' AND ct.status='pending_bridge'
            ORDER BY ct.id ASC
        """, (user["id"],)).fetchall()
        lines = [
            f"OPEN|{r['id']}|{r['pair']}|{r['direction']}|{r['lot_size']}|{r['entry_price']}|{r['stop_loss']}|{r['take_profit']}"
            for r in open_rows
        ]
        if open_rows:
            ids = [r["id"] for r in open_rows]
            db.execute(
                f"UPDATE copy_trades SET status='sent_to_bridge' WHERE id IN ({','.join('?' * len(ids))})",
                ids)

        # Open positions the user asked the app to close — the EA closes the real
        # ticket in MT5, then calls /report-close same as it would for a TP/SL hit.
        close_rows = db.execute("""
            SELECT id, mt5_ticket FROM copy_trades
            WHERE follower_id=? AND execution_mode='mt5' AND status='close_requested' AND mt5_ticket IS NOT NULL
            ORDER BY id ASC
        """, (user["id"],)).fetchall()
        lines += [f"CLOSE|{r['id']}|{r['mt5_ticket']}" for r in close_rows]
        if close_rows:
            ids = [r["id"] for r in close_rows]
            db.execute(
                f"UPDATE copy_trades SET status='close_sent_to_bridge' WHERE id IN ({','.join('?' * len(ids))})",
                ids)

        # Open positions with a pending SL/TP change
        modify_rows = db.execute("""
            SELECT id, mt5_ticket, pending_stop_loss, pending_take_profit FROM copy_trades
            WHERE follower_id=? AND execution_mode='mt5' AND status='open' AND modify_requested=1 AND mt5_ticket IS NOT NULL
            ORDER BY id ASC
        """, (user["id"],)).fetchall()
        lines += [f"MODIFY|{r['id']}|{r['mt5_ticket']}|{r['pending_stop_loss']}|{r['pending_take_profit']}" for r in modify_rows]
        if modify_rows:
            ids = [r["id"] for r in modify_rows]
            db.execute(
                f"UPDATE copy_trades SET modify_requested=2 WHERE id IN ({','.join('?' * len(ids))})",
                ids)  # 2 = sent, awaiting EA confirmation (distinct from 1 = queued)
    return "\n".join(lines)


@router.post("/heartbeat")
def heartbeat(
    account_balance: float = None, account_equity: float = None, account_currency: str = "",
    account_login: str = "", account_server: str = "", account_leverage: int = None,
    user=Depends(get_bridge_user),
):
    """Called every ~10s by the EA. Besides the connection keepalive, this is how
    the app learns the REAL broker account balance/equity — the app's own
    balance/equity (shown elsewhere) is a separate simulated/paper ledger for
    demo copy trades, it is never the same number as this."""
    with get_db() as db:
        updates = ["bridge_connected_at=datetime('now')"]
        params = []
        if account_balance is not None:
            updates.append("mt5_real_balance=?"); params.append(account_balance)
        if account_equity is not None:
            updates.append("mt5_real_equity=?"); params.append(account_equity)
        if account_currency:
            updates.append("mt5_real_currency=?"); params.append(account_currency)
        if account_login:
            updates.append("mt5_real_login=?"); params.append(account_login)
        if account_server:
            updates.append("mt5_real_server=?"); params.append(account_server)
        if account_leverage is not None:
            updates.append("mt5_real_leverage=?"); params.append(account_leverage)
        if account_balance is not None or account_equity is not None:
            updates.append("mt5_real_updated_at=datetime('now')")
        params.append(user["id"])
        db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
    return {"ok": True}


@router.post("/report-modify")
def report_modify(
    copy_trade_id: int, success: bool, new_sl: float = 0, new_tp: float = 0, error_msg: str = "",
    user=Depends(get_bridge_user),
):
    with get_db() as db:
        ct = db.execute("SELECT * FROM copy_trades WHERE id=? AND follower_id=?",
                         (copy_trade_id, user["id"])).fetchone()
        if not ct:
            raise HTTPException(404, "Copy trade not found")
        if success:
            db.execute("""UPDATE copy_trades SET stop_loss=?, take_profit=?,
                          modify_requested=0, pending_stop_loss=NULL, pending_take_profit=NULL
                          WHERE id=?""", (new_sl, new_tp, copy_trade_id))
            notify_user(db, user["id"], "trade_closed", "SL/TP updated", f"New SL {new_sl} / TP {new_tp} confirmed in MT5.", "/copy")
        else:
            db.execute("UPDATE copy_trades SET modify_requested=0, pending_stop_loss=NULL, pending_take_profit=NULL WHERE id=?",
                       (copy_trade_id,))
            notify_user(db, user["id"], "trade_closed", "SL/TP change failed", error_msg or "MT5 rejected the change.", "/copy")
    return {"ok": True}

@router.post("/report-fill")
def report_fill(
    copy_trade_id: int, status: str, ticket: str = "",
    fill_price: float = 0, error_msg: str = "",
    user=Depends(get_bridge_user),
):
    with get_db() as db:
        ct = db.execute("SELECT * FROM copy_trades WHERE id=? AND follower_id=?",
                         (copy_trade_id, user["id"])).fetchone()
        if not ct:
            raise HTTPException(404, "Copy trade not found")
        if status == "filled":
            db.execute("""UPDATE copy_trades SET status='open', mt5_ticket=?, entry_price=?
                          WHERE id=?""", (ticket, fill_price or ct["entry_price"], copy_trade_id))
        else:
            db.execute("""UPDATE copy_trades SET status='failed', fail_reason=? WHERE id=?""",
                       (error_msg or "EA reported failure", copy_trade_id))
            # The order never actually opened on the broker — give the reserved margin back.
            if ct["margin_used"]:
                db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (ct["margin_used"], user["id"]))
    return {"ok": True}


@router.post("/report-close")
def report_close(
    copy_trade_id: int, close_price: float, pnl_usd: float, pnl_pips: float,
    result: str, ticket: str = "",
    user=Depends(get_bridge_user),
):
    with get_db() as db:
        ct = db.execute("SELECT * FROM copy_trades WHERE id=? AND follower_id=?",
                         (copy_trade_id, user["id"])).fetchone()
        if not ct:
            raise HTTPException(404, "Copy trade not found")
        if ticket:
            db.execute("UPDATE copy_trades SET mt5_ticket=? WHERE id=?", (ticket, copy_trade_id))
        # Real MT5 P&L is authoritative here. apply_trade_close() handles the
        # balance credit, commission (if this follower's provider is
        # percentage-based), journal entry, and — if this was the provider's own
        # master trade — cascades to close every linked follower trade too.
        apply_trade_close(db, copy_trade_id, close_price, pnl_pips, pnl_usd, result,
                           "Closed via MT5 (real account)")
        notify_user(db, user["id"], "trade_closed", f"MT5 trade {result.upper()}",
                    f"Closed at {close_price} · {pnl_pips:+.1f} pips · ${pnl_usd:+.2f} (real account)", "/copy")
        if ct["provider_id"]:
            recompute_provider_stats(db, ct["provider_id"])
    return {"ok": True}
