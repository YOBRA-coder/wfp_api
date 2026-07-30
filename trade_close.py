"""
Shared trade-close logic — used by manual close, auto TP/SL settlement, AND
the MT5 bridge's report-close callback, so a trade closes the same way no
matter which of those three paths triggered it: same commission math, same
cascading close for a provider's master trade, same journal/notification
behavior. Previously this logic was duplicated (and drifted) across all three
call sites.
"""
from database import get_db
from signals import PAIR_CONFIG, pip_value_usd

# Optional dependencies — best-effort, never break a trade close if these fail.
try:
    from push_send import send_push
except Exception:
    send_push = None
try:
    from telegram_send import send_telegram_message
except Exception:
    send_telegram_message = None


def _push_to_user(db, user_id: int, title: str, body: str, url: str = "/"):
    if not send_push:
        return
    try:
        subs = db.execute("SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id=?",
                           (user_id,)).fetchall()
        for s in subs:
            ok = send_push({"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}},
                            title, body, url)
            if not ok:
                db.execute("DELETE FROM push_subscriptions WHERE id=?", (s["id"],))
    except Exception:
        pass


def apply_trade_close(db, trade_id: int, close_price: float, pnl_pips: float, pnl_usd: float,
                       result: str, notes: str = "Closed") -> list:
    """Core close logic for ONE copy_trades row: credits balance (minus a
    performance fee if this follower's provider uses percentage-based pricing
    and the trade was profitable), logs the journal entry, and — if this is a
    provider's own master trade — cascades to close every linked follower
    trade at the same price. Returns every trade_id actually closed (master +
    cascaded).
    """
    row = db.execute("""
        SELECT ct.*, s.pair as sig_pair, s.direction as sig_direction
        FROM copy_trades ct LEFT JOIN signals s ON ct.signal_id = s.id
        WHERE ct.id = ?
    """, (trade_id,)).fetchone()
    if row is None:
        return []
    t = dict(row)
    t["pair"] = t.get("pair") or t.pop("sig_pair", None)
    t["direction"] = t.get("direction") or t.pop("sig_direction", None)
    if not t or t["status"] != "open":
        return []
    follower_id, provider_id = t["follower_id"], t["provider_id"]

    commission = 0.0
    commission_pct = None
    if not t["is_master"] and provider_id and provider_id != follower_id and pnl_usd > 0:
        prow = db.execute("SELECT subscription_type, commission_pct FROM providers WHERE user_id=?",
                           (provider_id,)).fetchone()
        if prow and prow["subscription_type"] == "percentage":
            commission_pct = prow["commission_pct"]
            commission = round(pnl_usd * (commission_pct / 100.0), 2)

    payout = round(float(t["margin_used"] or 0) + pnl_usd - commission, 2)
    db.execute("""UPDATE copy_trades SET status='closed', result=?, pnl_pips=?, pnl_usd=?,
                  close_price=?, closed_at=datetime('now'), commission_usd=? WHERE id=?""",
               (result, round(pnl_pips, 1), pnl_usd, close_price, commission, trade_id))
    db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (payout, follower_id))
    db.execute("""INSERT INTO trade_journal
        (user_id,pair,direction,entry_price,exit_price,lot_size,pnl_usd,pnl_pips,notes,setup)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (follower_id, t["pair"], t["direction"], t["entry_price"], close_price, t["lot_size"], pnl_usd, pnl_pips,
         notes, "Auto (Own Trade)" if t["is_master"] else "Auto (Copy Trade)"))

    if commission > 0:
        db.execute("""INSERT INTO provider_earnings
            (provider_id,follower_id,copy_trade_id,type,amount_usd,commission_pct,trade_pnl_usd,status)
            VALUES (?,?,?,?,?,?,?,'accrued')""",
            (provider_id, follower_id, trade_id, "percentage_fee", commission, commission_pct, pnl_usd))
        db.execute("UPDATE users SET balance = balance + ? WHERE id=?", (commission, provider_id))
        db.execute("UPDATE providers SET total_earned_usd = total_earned_usd + ? WHERE user_id=?",
                   (commission, provider_id))
        db.execute("""INSERT INTO notifications (user_id,type,title,message) VALUES (?,?,?,?)""",
            (provider_id, "billing", "Performance fee earned",
             f"${commission:.2f} ({commission_pct}% of ${pnl_usd:.2f} profit) from a follower's closed trade."))

    closed_ids = [trade_id]
    if t["is_master"]:
        linked = db.execute("SELECT id FROM copy_trades WHERE master_trade_id=? AND status='open'",
                            (trade_id,)).fetchall()
        for l in linked:
            lt = db.execute("SELECT * FROM copy_trades WHERE id=?", (l["id"],)).fetchone()
            _, _, l_pip, _, _ = PAIR_CONFIG.get(lt["pair"], PAIR_CONFIG["EURUSD"])
            l_pips = (close_price - lt["entry_price"]) / l_pip * (1 if lt["direction"] == "BUY" else -1)
            l_pnl = pip_value_usd(lt["pair"], l_pips, lt["lot_size"])
            l_result = "win" if l_pnl > 0 else ("loss" if l_pnl < 0 else "breakeven")
            closed_ids += apply_trade_close(db, l["id"], close_price, l_pips, l_pnl, l_result,
                                             "Closed — the provider you're copying exited their position")
            db.execute("""INSERT INTO notifications (user_id,type,title,message) VALUES (?,?,?,?)""",
                (lt["follower_id"], "trade_closed", f"{lt['pair']} closed — provider exited",
                 f"The provider you're copying closed their position, so this closed too. {l_pnl:+.2f} USD"))
            _push_to_user(db, lt["follower_id"], f"{lt['pair']} closed — provider exited", f"{l_pnl:+.2f} USD", "/copy")
    return closed_ids
