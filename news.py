"""
Financial news feed — aggregates real forex/market news from public RSS
feeds (no API key required, unlike the Twelve Data quote/OHLCV endpoints).

Verified live sources (checked directly, both return real current items):
  - Investing.com "Forex News"  https://www.investing.com/rss/news_1.rss
  - FXStreet "Forex & Commodities News"  https://www.fxstreet.com/rss

The two feeds use different dialects (Investing.com: no <description>, a
non-standard "YYYY-MM-DD HH:MM:SS" pubDate with no timezone marker, assumed
UTC; FXStreet: standard RFC-822 pubDate, CDATA-wrapped description) — each
source has its own tolerant parser, and a single malformed item never takes
the rest of that source (or the other source) down with it.

Mount in forexpro_main.py:
    from news import router as news_router
    app.include_router(news_router)
"""
import time
import threading
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from fastapi import APIRouter, Depends

from auth import get_current_user

router = APIRouter(prefix="/news", tags=["news"])

SOURCES = [
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news_1.rss", "dialect": "investing"},
    {"name": "FXStreet",      "url": "https://www.fxstreet.com/rss",             "dialect": "fxstreet"},
]

_CACHE = {"at": 0.0, "items": []}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 300  # 5 minutes — RSS feeds like these update every few minutes
                  # at most, so polling them on every dashboard load would be
                  # both pointless and a good way to get our server IP rate
                  # limited by the source site.


def _strip(s):
    return (s or "").strip()


def _parse_investing_date(raw):
    # "2026-08-31 14:49:44" — no timezone marker in the feed; Investing.com's
    # own feed generator doesn't document one, so UTC is the standard
    # assumption for undated RSS timestamps and is what every reader/aggregator
    # that ingests this feed does in practice.
    try:
        dt = datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _parse_rfc822_date(raw):
    try:
        dt = parsedate_to_datetime(raw.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _fetch_source(source):
    """Fetch + parse one RSS source. Never raises — returns [] on any failure
    so one broken/unreachable feed doesn't take the whole endpoint down."""
    items = []
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": "ForexPro/1.0 (+news-aggregator)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item"):
            try:
                title = _strip(item.findtext("title"))
                link = _strip(item.findtext("link"))
                if not title or not link:
                    continue  # unusable without a headline + a place to send the reader

                raw_date = _strip(item.findtext("pubDate"))
                if source["dialect"] == "investing":
                    published = _parse_investing_date(raw_date)
                    summary = ""
                else:
                    published = _parse_rfc822_date(raw_date)
                    summary = _strip(item.findtext("description"))
                    if len(summary) > 220:
                        summary = summary[:217].rsplit(" ", 1)[0] + "…"

                image = ""
                enclosure = item.find("enclosure")
                if enclosure is not None:
                    image = enclosure.get("url", "")

                items.append({
                    "title": title,
                    "link": link,
                    "source": source["name"],
                    "summary": summary,
                    "image": image,
                    # None sorts as "oldest" below rather than falsely looking freshest
                    "_published_dt": published,
                    "published_at": published.isoformat() if published else None,
                })
            except Exception:
                continue  # skip just this one malformed item
    except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, TimeoutError, OSError):
        return []
    except Exception:
        return []
    return items


def _refresh_cache():
    all_items = []
    for source in SOURCES:
        all_items.extend(_fetch_source(source))
    all_items.sort(key=lambda it: it["_published_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    for it in all_items:
        it.pop("_published_dt", None)
    with _CACHE_LOCK:
        _CACHE["items"] = all_items
        _CACHE["at"] = time.monotonic()
    return all_items


@router.get("/feed")
def get_news_feed(limit: int = 20, user=Depends(get_current_user)):
    now = time.monotonic()
    with _CACHE_LOCK:
        fresh = bool(_CACHE["items"]) and (now - _CACHE["at"]) < _CACHE_TTL
        cached = list(_CACHE["items"])

    stale = False
    if fresh:
        items = cached
    else:
        items = _refresh_cache()
        if not items and cached:
            # Every source failed just now — better to show yesterday's
            # headlines than an empty panel.
            items = cached
            stale = True

    limit = max(1, min(50, limit))
    return {
        "items": items[:limit],
        "sources": [s["name"] for s in SOURCES],
        "stale": stale,
    }
