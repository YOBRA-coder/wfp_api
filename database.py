"""
Database: SQLite via Python's built-in sqlite3
- Zero setup, single file, production-ready for <10k users
- Easy to migrate to PostgreSQL later (just swap the connection)
- File: forexpro.db (auto-created on first run)
"""
import sqlite3, json, hashlib, os
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "forexpro.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrent reads
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    UNIQUE NOT NULL,
            username    TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    DEFAULT 'trader',  -- trader | provider | admin
            plan        TEXT    DEFAULT 'free',    -- free | pro | elite
            balance     REAL    DEFAULT 10000.0,
            equity      REAL    DEFAULT 10000.0,
            broker      TEXT    DEFAULT '',
            mt5_login   TEXT    DEFAULT '',
            mt5_server  TEXT    DEFAULT '',
            avatar      TEXT    DEFAULT '',
            bio         TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now')),
            last_login  TEXT,
            registration_paid      INTEGER DEFAULT 0,
            subscription_status    TEXT    DEFAULT 'inactive',  -- inactive|active|past_due|cancelled
            subscription_expires_at TEXT,
            stripe_customer_id     TEXT,
            stripe_sub_id          TEXT,
            mpesa_phone             TEXT
        );

        CREATE TABLE IF NOT EXISTS payments (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER REFERENCES users(id),
            provider            TEXT NOT NULL,   -- mpesa | stripe
            kind                TEXT NOT NULL,   -- registration | subscription
            plan                TEXT,
            amount              REAL,
            currency            TEXT DEFAULT 'KES',
            status              TEXT DEFAULT 'pending', -- pending|success|failed|cancelled
            checkout_request_id TEXT,
            merchant_request_id TEXT,
            mpesa_receipt       TEXT,
            phone               TEXT,
            stripe_session_id   TEXT,
            raw_response        TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            endpoint    TEXT UNIQUE,
            p256dh      TEXT,
            auth        TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER REFERENCES users(id),
            type                TEXT NOT NULL,    -- deposit | withdrawal
            amount_usd          REAL NOT NULL,
            method              TEXT,             -- mpesa | manual
            status              TEXT DEFAULT 'pending', -- pending|completed|rejected
            phone               TEXT,
            mpesa_receipt       TEXT,
            payment_id          INTEGER REFERENCES payments(id),
            admin_note          TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            processed_at        TEXT
        );

        CREATE TABLE IF NOT EXISTS signals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id     INTEGER REFERENCES users(id),
            pair            TEXT NOT NULL,
            timeframe       TEXT NOT NULL,
            direction       TEXT NOT NULL,
            strength        TEXT NOT NULL,
            confidence      INTEGER NOT NULL,
            entry_price     REAL NOT NULL,
            stop_loss       REAL NOT NULL,
            take_profit     REAL NOT NULL,
            sl_pips         REAL,
            tp_pips         REAL,
            risk_reward     REAL,
            rsi             REAL,
            macd            REAL,
            ema20           REAL,
            ema50           REAL,
            bb_upper        REAL,
            bb_lower        REAL,
            stoch_k         REAL,
            atr             REAL,
            candle_pattern  TEXT,
            chart_pattern   TEXT,
            entry_time      TEXT,
            ai_analysis     TEXT,
            status          TEXT DEFAULT 'active',  -- active|closed|expired|cancelled
            result          TEXT,                    -- win|loss|breakeven
            pnl_pips        REAL DEFAULT 0,
            close_price     REAL,
            closed_at       TEXT,
            expires_at      TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            chart_data      TEXT  -- JSON: {ohlcv, markers, support_resistance, trendline}
        );

        CREATE TABLE IF NOT EXISTS copy_trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id     INTEGER REFERENCES users(id),
            provider_id     INTEGER REFERENCES users(id),
            signal_id       INTEGER REFERENCES signals(id),
            lot_size        REAL    DEFAULT 0.01,
            risk_pct        REAL    DEFAULT 2.0,
            entry_price     REAL,
            stop_loss       REAL,
            take_profit     REAL,
            status          TEXT    DEFAULT 'pending',  -- pending|open|closed|failed
            result          TEXT,
            pnl_pips        REAL    DEFAULT 0,
            pnl_usd         REAL    DEFAULT 0,
            opened_at       TEXT,
            closed_at       TEXT,
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id     INTEGER REFERENCES users(id),
            provider_id     INTEGER REFERENCES users(id),
            risk_pct        REAL    DEFAULT 2.0,
            max_lot         REAL    DEFAULT 0.1,
            copy_sl         INTEGER DEFAULT 1,
            copy_tp         INTEGER DEFAULT 1,
            min_confidence  INTEGER DEFAULT 60,
            auto_copy       INTEGER DEFAULT 1,
            pairs_filter    TEXT    DEFAULT '[]',   -- JSON array, empty = all
            is_active       INTEGER DEFAULT 1,
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS providers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER UNIQUE REFERENCES users(id),
            display_name    TEXT NOT NULL,
            description     TEXT DEFAULT '',
            win_rate        REAL DEFAULT 0,
            total_signals   INTEGER DEFAULT 0,
            total_pips      REAL DEFAULT 0,
            avg_rr          REAL DEFAULT 0,
            monthly_pips    REAL DEFAULT 0,
            followers_count INTEGER DEFAULT 0,
            monthly_fee     REAL DEFAULT 0,
            is_verified     INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS education_courses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT,
            category    TEXT,   -- basics|technical|risk|psychology|advanced
            level       TEXT,   -- beginner|intermediate|advanced
            lessons     TEXT,   -- JSON
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            course_id   INTEGER REFERENCES education_courses(id),
            lesson_idx  INTEGER DEFAULT 0,
            completed   INTEGER DEFAULT 0,
            score       INTEGER DEFAULT 0,
            updated_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, course_id)
        );

        CREATE TABLE IF NOT EXISTS trade_journal (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            pair        TEXT,
            direction   TEXT,
            entry_price REAL,
            exit_price  REAL,
            lot_size    REAL,
            pnl_usd     REAL,
            pnl_pips    REAL,
            notes       TEXT,
            emotion     TEXT,   -- calm|fearful|greedy|confident
            setup       TEXT,
            traded_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            type        TEXT,   -- signal|copy|education|system
            title       TEXT,
            message     TEXT,
            is_read     INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS app_meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        -- Per-user watchlist: which pairs they've starred as favorites out of
        -- the full tradable pair list. Search/browse of the full list happens
        -- client-side; this table only stores what the user actually chose.
        CREATE TABLE IF NOT EXISTS user_watchlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            pair        TEXT NOT NULL,
            sort_order  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, pair)
        );

        -- Per-user chart defaults: last-used timeframe + which indicator
        -- overlays are toggled on. One row per user (applies app-wide, same
        -- as the old localStorage-only version) so it now follows them across
        -- devices instead of resetting on a new browser/phone.
        CREATE TABLE IF NOT EXISTS user_chart_prefs (
            user_id     INTEGER PRIMARY KEY REFERENCES users(id),
            timeframe   TEXT DEFAULT 'H1',
            indicators  TEXT DEFAULT '{"ema":true,"bb":true,"sr":true,"trendline":true,"volume":true}',
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        -- Per-user, per-category push toggle. Push was previously all-or-
        -- nothing (one browser permission covering every event type); this
        -- lets a user keep push on for trade closes/copy events but mute,
        -- say, education/system pushes, without losing the in-app bell
        -- notification either way (notify_user() always writes that row —
        -- this table only gates the push half).
        CREATE TABLE IF NOT EXISTS user_notification_prefs (
            user_id     INTEGER PRIMARY KEY REFERENCES users(id),
            categories  TEXT DEFAULT '{"signal":true,"copy":true,"billing":true,"system":true,"education":true,"trade_closed":true}',
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        -- Saved rectangle drawings on a chart, one row per user+pair+timeframe
        -- (matches how the drawing tool keys its local cache client-side).
        CREATE TABLE IF NOT EXISTS chart_drawings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            pair        TEXT NOT NULL,
            timeframe   TEXT NOT NULL,
            rects       TEXT DEFAULT '[]',  -- JSON array of {id,t1,p1,t2,p2}
            updated_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, pair, timeframe)
        );
        """)

        _migrate_users_table(db)
        _create_earnings_and_verification_tables(db)
        # One-time repair: a prior bug stored paid plans as bare 'elite'/'pro' instead
        # of the PLAN_LIMITS keys 'trader_elite'/'trader_pro'/'provider_pro', which
        # silently left every paying user capped at free-tier usage limits. Anyone
        # already on 'elite'/'pro' in the DB gets normalized here so the fix applies
        # retroactively instead of only to new purchases.
        db.execute("UPDATE users SET plan='trader_elite' WHERE plan='elite'")
        db.execute("UPDATE users SET plan='trader_pro' WHERE plan='pro' AND role != 'provider'")
        db.execute("UPDATE users SET plan='provider_pro' WHERE plan='pro' AND role='provider'")
        # Seed demo users
        _seed_demo_data(db)
        # Education courses are seeded independently of the users check above —
        # on any DB that already had real users (i.e. anything past initial setup),
        # the old code's single "if users table is empty" guard meant this content
        # never got inserted at all, leaving the Education page permanently empty.
        _seed_education_courses(db)
    print(f"[DB] SQLite initialized at {DB_PATH}")

def _migrate_users_table(db):
    """Add new columns to already-existing tables (idempotent, safe to re-run)."""
    def add_cols(table, additions):
        cols = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        for col, decl in additions.items():
            if col not in cols:
                try:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
                except Exception as e:
                    print(f"[DB] migration warning ({table}.{col}): {e}")

    add_cols("users", {
        "registration_paid":       "INTEGER DEFAULT 0",
        "subscription_status":     "TEXT DEFAULT 'inactive'",
        "subscription_expires_at": "TEXT",
        "stripe_customer_id":      "TEXT",
        "stripe_sub_id":           "TEXT",
        "mpesa_phone":             "TEXT",
        "bridge_token":            "TEXT",
        "bridge_connected_at":     "TEXT",
        "email_alerts_enabled":    "INTEGER DEFAULT 1",
        "default_lot_size":        "REAL DEFAULT 0.02",
        "default_risk_pct":        "REAL DEFAULT 2.0",
        "mt5_real_balance":        "REAL",
        "mt5_real_equity":         "REAL",
        "mt5_real_currency":       "TEXT",
        "mt5_real_login":          "TEXT",
        "mt5_real_server":         "TEXT",
        "mt5_real_leverage":       "INTEGER",
        "mt5_real_updated_at":     "TEXT",
        "telegram_chat_id":        "TEXT",
        "telegram_username":       "TEXT",
        "telegram_link_code":      "TEXT",
        "telegram_link_expires":   "TEXT",
        "email_verified":          "INTEGER DEFAULT 0",
        "email_verify_token":      "TEXT",
        "email_verify_expires":    "TEXT",
        "risk_disclaimer_accepted_at": "TEXT",
        "password_reset_otp":       "TEXT",
        "password_reset_expires":   "TEXT",
        "password_reset_attempts":  "INTEGER DEFAULT 0",
    })
    add_cols("signals", {
        "chart_data": "TEXT",
        "source": "TEXT DEFAULT 'ai'",           # ai | manual — manual = provider-entered from their own analysis/external source
        "is_copyable": "INTEGER DEFAULT 1",       # provider controls which of their signals followers can copy
        "execution_mode": "TEXT DEFAULT 'immediate'",  # immediate | pending (waits for trigger_price)
        "trigger_price": "REAL",
        "master_trade_id": "INTEGER",             # the provider's own copy_trades.id representing their live position
        "approval_status": "TEXT DEFAULT 'approved'",  # pending_review | approved | rejected — see /signals/{id}/approve
    })
    add_cols("copy_trades", {
        "execution_mode": "TEXT DEFAULT 'simulated'",  # simulated | mt5
        "mt5_ticket":      "TEXT",
        "fail_reason":     "TEXT",
        "close_price":     "REAL",
        "margin_used":     "REAL DEFAULT 0",  # cash reserved from user.balance while this trade is open
        "pair":            "TEXT",  # set directly for quick trades (no signal_id to join through)
        "direction":       "TEXT",
        "modify_requested": "INTEGER DEFAULT 0",
        "pending_stop_loss": "REAL",
        "pending_take_profit": "REAL",
        "is_master":       "INTEGER DEFAULT 0",  # this IS the provider's own position (not a copy)
        "master_trade_id": "INTEGER",            # for follower trades: which master trade they're linked to (cascades close)
        "commission_usd":  "REAL DEFAULT 0",     # performance fee charged to this trade's follower, if any
    })
    add_cols("subscriptions", {"auto_execute": "INTEGER DEFAULT 0"})
    add_cols("providers", {
        "subscription_type": "TEXT DEFAULT 'monthly'",  # monthly | percentage
        "commission_pct":    "REAL DEFAULT 25",         # % of a follower's profit on a winning trade, if percentage-based
        "preferred_pairs":   "TEXT DEFAULT '[]'",        # JSON array — the pairs this provider actually trades
        "preferred_timeframes": "TEXT DEFAULT '[]'",
        "max_signals_per_day": "INTEGER DEFAULT 10",
        "risk_notes":        "TEXT DEFAULT ''",          # provider's own stated risk approach, shown to prospective followers
        "total_earned_usd":  "REAL DEFAULT 0",
    })

def _create_earnings_and_verification_tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS provider_earnings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id     INTEGER REFERENCES users(id),
            follower_id     INTEGER REFERENCES users(id),
            copy_trade_id   INTEGER REFERENCES copy_trades(id),
            type            TEXT,      -- percentage_fee | monthly_subscription
            amount_usd      REAL,
            commission_pct  REAL,
            trade_pnl_usd   REAL,
            status          TEXT DEFAULT 'accrued',  -- accrued | paid
            created_at      TEXT DEFAULT (datetime('now'))
        );
    """)

def _seed_demo_data(db):
    import hashlib
    def hp(p): return hashlib.sha256(p.encode()).hexdigest()

    # Check if already seeded
    existing = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        return

    # Demo users
    db.execute("INSERT INTO users (email,username,password,role,plan,balance,equity) VALUES (?,?,?,?,?,?,?)",
               ("admin@forexpro.com","admin",hp("admin123"),"admin","trader_elite",50000,52300))
    db.execute("INSERT INTO users (email,username,password,role,plan,balance,equity) VALUES (?,?,?,?,?,?,?)",
               ("provider@forexpro.com","TopTrader_FX",hp("demo123"),"provider","provider_pro",125000,131450))
    db.execute("INSERT INTO users (email,username,password,role,plan,balance,equity) VALUES (?,?,?,?,?,?,?)",
               ("yobby@forexpro.com","Yobby",hp("demo123"),"trader","trader_pro",500,487))
    db.execute("INSERT INTO users (email,username,password,role,plan,balance,equity) VALUES (?,?,?,?,?,?,?)",
               ("demo@forexpro.com","DemoTrader",hp("demo123"),"trader","free",10000,9850))

    # Provider profile
    db.execute("""INSERT INTO providers (user_id,display_name,description,win_rate,total_signals,total_pips,avg_rr,monthly_pips,followers_count,monthly_fee,is_verified)
                  VALUES (2,'TopTrader FX','Professional forex trader with 7 years experience. Specializing in EUR/USD and GBP/USD using price action + multi-TF analysis.',68.4,247,3420.5,2.3,412.0,34,29.99,1)""")

    # Subscription: Yobby follows TopTrader
    db.execute("INSERT INTO subscriptions (follower_id,provider_id,risk_pct,max_lot,min_confidence,auto_copy) VALUES (3,2,2.0,0.05,65,1)")

    print("[DB] Demo data seeded")

def _seed_education_courses(db):
    """Seeds (or upgrades) the Learning Hub content from education_content.py.
    Guarded by a content-version marker in app_meta rather than a simple
    'table is empty' check — so shipping richer course content later actually
    reaches DBs that were already seeded with an older version, instead of
    silently no-op'ing forever. Bumping education_content.CONTENT_VERSION
    triggers a reseed: old course rows are replaced, and progress on the
    replaced courses is reset (the lesson structure changes too much for old
    lesson_idx pointers to still make sense)."""
    import education_content as ec

    row = db.execute("SELECT value FROM app_meta WHERE key='education_content_version'").fetchone()
    current_version = int(row["value"]) if row else 0

    if current_version >= ec.CONTENT_VERSION:
        return

    old_ids = [r["id"] for r in db.execute("SELECT id FROM education_courses").fetchall()]
    if old_ids:
        placeholders = ",".join("?" * len(old_ids))
        db.execute(f"DELETE FROM user_progress WHERE course_id IN ({placeholders})", old_ids)
        db.execute("DELETE FROM education_courses")

    for c in ec.COURSES:
        db.execute(
            "INSERT INTO education_courses (title,description,category,level,lessons) VALUES (?,?,?,?,?)",
            (c["title"], c["description"], c["category"], c["level"], json.dumps(c["lessons"])),
        )
    db.execute(
        "INSERT INTO app_meta (key,value) VALUES ('education_content_version',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(ec.CONTENT_VERSION),),
    )
    print(f"[DB] Education courses seeded (content v{ec.CONTENT_VERSION}, {len(ec.COURSES)} courses)")

def is_subscription_active(user: dict) -> bool:
    """True if the user's paid subscription is currently valid (free plan is always 'active')."""
    if not user:
        return False
    if user.get("plan", "free") == "free":
        return True
    exp = user.get("subscription_expires_at")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) > datetime.now()
    except Exception:
        return False

# Feature limits per plan. `None` means unlimited. Mirrors the marketing
# copy on the /payments/plans pricing cards — keep both in sync.
PLAN_LIMITS = {
    "free":         {"signals_per_day": 5,    "max_subscriptions": 1,    "copies_per_day": 3,    "can_be_provider": False, "bulk_generate": False},
    "trader_pro":   {"signals_per_day": None, "max_subscriptions": 3,    "copies_per_day": None, "can_be_provider": False, "bulk_generate": True},
    "trader_elite": {"signals_per_day": None, "max_subscriptions": None, "copies_per_day": None, "can_be_provider": False, "bulk_generate": True},
    "provider_pro": {"signals_per_day": None, "max_subscriptions": None, "copies_per_day": None, "can_be_provider": True,  "bulk_generate": True},
}

def plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

def effective_plan(user: dict) -> str:
    """The plan to actually enforce limits against — falls back to 'free' if a
    paid plan's subscription has lapsed, so an expired Pro account doesn't keep
    unlimited access forever."""
    plan = user.get("plan", "free") if user else "free"
    if plan != "free" and not is_subscription_active(user):
        return "free"
    return plan

def recompute_provider_stats(db, user_id: int):
    """Recalculate a provider's public track record from their real signal history.
    No-op if this user hasn't registered as a provider."""
    row = db.execute("SELECT id FROM providers WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return
    closed = db.execute(
        "SELECT result, pnl_pips, risk_reward, closed_at FROM signals WHERE provider_id=? AND status='closed'",
        (user_id,)).fetchall()
    total_signals = db.execute("SELECT COUNT(*) c FROM signals WHERE provider_id=?", (user_id,)).fetchone()["c"]
    wins = sum(1 for r in closed if r["result"] == "win")
    win_rate = round(wins / len(closed) * 100, 1) if closed else 0.0
    total_pips = round(sum(r["pnl_pips"] or 0 for r in closed), 1)
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    monthly_pips = round(sum(r["pnl_pips"] or 0 for r in closed if (r["closed_at"] or "") >= cutoff), 1)
    rr_vals = [r["risk_reward"] for r in closed if r["risk_reward"]]
    avg_rr = round(sum(rr_vals) / len(rr_vals), 2) if rr_vals else 0
    followers = db.execute(
        "SELECT COUNT(*) c FROM subscriptions WHERE provider_id=? AND is_active=1", (user_id,)).fetchone()["c"]
    db.execute("""UPDATE providers SET win_rate=?, total_signals=?, total_pips=?, monthly_pips=?,
                  avg_rr=?, followers_count=? WHERE user_id=?""",
               (win_rate, total_signals, total_pips, monthly_pips, avg_rr, followers, user_id))

def generate_bridge_token() -> str:
    """Random per-user token the MT5 EA uses to authenticate to /bridge/* endpoints
    (kept separate from the normal JWT since an EA can't do an interactive login)."""
    import secrets
    return "fpx_" + secrets.token_hex(20)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.encode()).hexdigest() == hashed
