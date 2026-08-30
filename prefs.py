"""
User preferences — synced to the DB instead of the device's localStorage.

Covers three things the trader picks per-account, not per-browser:
  • watchlist   — which pairs they've starred as favorites (out of the full
                  tradable pair list; searching/browsing the full list is
                  entirely client-side, this table only stores the picks)
  • chart prefs — last-used timeframe + which indicator overlays are on
  • drawings    — rectangles drawn on a chart, one saved set per pair+timeframe

Mount in forexpro_main.py:
    from prefs import router as prefs_router
    app.include_router(prefs_router)
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db
from auth import get_current_user
from push_send import DEFAULT_NOTIF_CATEGORIES, get_notification_prefs

router = APIRouter(prefix="/prefs", tags=["prefs"])

DEFAULT_INDICATORS = {"ema": True, "bb": True, "sr": True, "trendline": True, "volume": True}


# ── Notification push categories ────────────────────────────────────────────
@router.get("/notifications")
def get_notification_categories(user=Depends(get_current_user)):
    with get_db() as db:
        return {"categories": get_notification_prefs(db, user["id"])}


class NotifPrefsReq(BaseModel):
    categories: dict  # e.g. {"signal": true, "education": false}


@router.put("/notifications")
def set_notification_categories(req: NotifPrefsReq, user=Depends(get_current_user)):
    with get_db() as db:
        existing = get_notification_prefs(db, user["id"])
        merged = {**existing, **{k: bool(v) for k, v in req.categories.items() if k in DEFAULT_NOTIF_CATEGORIES}}
        db.execute("""
            INSERT INTO user_notification_prefs (user_id, categories, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET categories=excluded.categories, updated_at=excluded.updated_at
        """, (user["id"], json.dumps(merged)))
    return {"categories": merged}


# ── Watchlist ──────────────────────────────────────────────────────────────
@router.get("/watchlist")
def get_watchlist(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT pair FROM user_watchlist WHERE user_id=? ORDER BY sort_order, id",
            (user["id"],)).fetchall()
    return {"watchlist": [r["pair"] for r in rows]}


class WatchlistReq(BaseModel):
    pairs: list[str]  # full replacement list, in display order


@router.put("/watchlist")
def set_watchlist(req: WatchlistReq, user=Depends(get_current_user)):
    pairs = [p.strip().upper() for p in dict.fromkeys(req.pairs) if p.strip()][:50]
    with get_db() as db:
        db.execute("DELETE FROM user_watchlist WHERE user_id=?", (user["id"],))
        for i, pair in enumerate(pairs):
            db.execute(
                "INSERT INTO user_watchlist (user_id, pair, sort_order) VALUES (?,?,?)",
                (user["id"], pair, i))
    return {"watchlist": pairs}


@router.post("/watchlist/{pair}")
def add_to_watchlist(pair: str, user=Depends(get_current_user)):
    pair = pair.strip().upper()
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) c FROM user_watchlist WHERE user_id=?", (user["id"],)).fetchone()["c"]
        if count >= 50:
            raise HTTPException(400, "Watchlist is full (50 max)")
        db.execute(
            "INSERT OR IGNORE INTO user_watchlist (user_id, pair, sort_order) VALUES (?,?,?)",
            (user["id"], pair, count))
    return {"added": pair}


@router.delete("/watchlist/{pair}")
def remove_from_watchlist(pair: str, user=Depends(get_current_user)):
    pair = pair.strip().upper()
    with get_db() as db:
        db.execute("DELETE FROM user_watchlist WHERE user_id=? AND pair=?", (user["id"], pair))
    return {"removed": pair}


# ── Chart prefs (timeframe + indicator toggles) ─────────────────────────────
@router.get("/chart")
def get_chart_prefs(user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute("SELECT * FROM user_chart_prefs WHERE user_id=?", (user["id"],)).fetchone()
    if not row:
        return {"timeframe": "H1", "indicators": DEFAULT_INDICATORS}
    try:
        indicators = {**DEFAULT_INDICATORS, **json.loads(row["indicators"] or "{}")}
    except Exception:
        indicators = DEFAULT_INDICATORS
    return {"timeframe": row["timeframe"] or "H1", "indicators": indicators}


class ChartPrefsReq(BaseModel):
    timeframe: Optional[str] = None
    indicators: Optional[dict] = None


@router.put("/chart")
def set_chart_prefs(req: ChartPrefsReq, user=Depends(get_current_user)):
    with get_db() as db:
        existing = db.execute("SELECT * FROM user_chart_prefs WHERE user_id=?", (user["id"],)).fetchone()
        timeframe = req.timeframe or (existing["timeframe"] if existing else "H1")
        if req.indicators is not None:
            base = json.loads(existing["indicators"]) if existing else DEFAULT_INDICATORS
            indicators = {**base, **req.indicators}
        else:
            indicators = json.loads(existing["indicators"]) if existing else DEFAULT_INDICATORS
        db.execute("""
            INSERT INTO user_chart_prefs (user_id, timeframe, indicators, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                timeframe=excluded.timeframe, indicators=excluded.indicators, updated_at=excluded.updated_at
        """, (user["id"], timeframe, json.dumps(indicators)))
    return {"timeframe": timeframe, "indicators": indicators}


# ── Chart drawings (rectangles) ─────────────────────────────────────────────
@router.get("/drawings")
def get_drawings(pair: str, timeframe: str, user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute(
            "SELECT rects FROM chart_drawings WHERE user_id=? AND pair=? AND timeframe=?",
            (user["id"], pair, timeframe)).fetchone()
    try:
        rects = json.loads(row["rects"]) if row else []
    except Exception:
        rects = []
    return {"pair": pair, "timeframe": timeframe, "rects": rects}


class DrawingsReq(BaseModel):
    pair: str
    timeframe: str
    rects: list[dict]


@router.put("/drawings")
def set_drawings(req: DrawingsReq, user=Depends(get_current_user)):
    rects_json = json.dumps(req.rects[:200])  # sane cap — this is a chart annotation, not a database
    with get_db() as db:
        db.execute("""
            INSERT INTO chart_drawings (user_id, pair, timeframe, rects, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, pair, timeframe) DO UPDATE SET
                rects=excluded.rects, updated_at=excluded.updated_at
        """, (user["id"], req.pair, req.timeframe, rects_json))
    return {"saved": True}


@router.delete("/drawings")
def clear_drawings(pair: str, timeframe: str, user=Depends(get_current_user)):
    with get_db() as db:
        db.execute(
            "DELETE FROM chart_drawings WHERE user_id=? AND pair=? AND timeframe=?",
            (user["id"], pair, timeframe))
    return {"cleared": True}
