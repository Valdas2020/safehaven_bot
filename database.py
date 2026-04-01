"""
PostgreSQL via asyncpg.
All raw SQL — no ORM overhead for the MVP.
"""
import logging
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from config import DATABASE_URL

logger = logging.getLogger(__name__)
_pool: asyncpg.Pool | None = None


async def init_db() -> None:
    global _pool
    # Render gives URLs starting with postgres://, asyncpg needs postgresql://
    dsn = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              BIGSERIAL PRIMARY KEY,
                telegram_id     BIGINT UNIQUE NOT NULL,
                language        TEXT NOT NULL DEFAULT 'EN',
                name            TEXT,
                age_cat         TEXT,
                location        TEXT,
                format          TEXT,
                email           TEXT,
                phone           TEXT,
                contact_method  TEXT,
                gdpr_accepted   BOOLEAN NOT NULL DEFAULT FALSE,
                status          TEXT NOT NULL DEFAULT 'active',
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Migrate existing deployments that lack the new columns
        for col, coltype in [("email", "TEXT"), ("phone", "TEXT"), ("contact_method", "TEXT")]:
            await conn.execute(f"""
                DO $$ BEGIN
                    ALTER TABLE users ADD COLUMN {col} {coltype};
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id                      BIGSERIAL PRIMARY KEY,
                user_id                 BIGINT NOT NULL REFERENCES users(id),
                triage_level            TEXT NOT NULL DEFAULT 'normal',
                category                TEXT,
                description             TEXT,
                created_at              TIMESTAMPTZ DEFAULT NOW(),
                assigned_specialist_id  BIGINT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id              BIGSERIAL PRIMARY KEY,
                user_id         BIGINT NOT NULL REFERENCES users(id),
                specialist_id   TEXT NOT NULL,
                start_time      TIMESTAMPTZ NOT NULL,
                end_time        TIMESTAMPTZ NOT NULL,
                calendar_event_id TEXT,
                status          TEXT NOT NULL DEFAULT 'confirmed',
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS post_visit (
                id               BIGSERIAL PRIMARY KEY,
                booking_id       BIGINT NOT NULL REFERENCES bookings(id),
                status           TEXT NOT NULL,
                duration_minutes INT NOT NULL DEFAULT 45,
                type_of_work     TEXT,
                note_short       TEXT,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    logger.info("PostgreSQL initialised")


async def close_db() -> None:
    if _pool:
        await _pool.close()


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised")
    return _pool


# ── helpers ──────────────────────────────────────────────────────────────────

async def get_user(telegram_id: int) -> dict | None:
    row = await pool().fetchrow(
        "SELECT * FROM users WHERE telegram_id = $1", telegram_id
    )
    return dict(row) if row else None


async def upsert_user(telegram_id: int, **kwargs) -> dict:
    await pool().execute(
        "INSERT INTO users (telegram_id) VALUES ($1) ON CONFLICT DO NOTHING",
        telegram_id,
    )
    if kwargs:
        cols = list(kwargs.keys())
        vals = list(kwargs.values())
        set_clause = ", ".join(f"{c} = ${i+2}" for i, c in enumerate(cols))
        await pool().execute(
            f"UPDATE users SET {set_clause} WHERE telegram_id = $1",
            telegram_id, *vals,
        )
    row = await pool().fetchrow(
        "SELECT * FROM users WHERE telegram_id = $1", telegram_id
    )
    return dict(row)


async def create_case(
    user_id: int, triage_level: str, category: str, description: str
) -> int:
    row = await pool().fetchrow(
        """
        INSERT INTO cases (user_id, triage_level, category, description)
        VALUES ($1, $2, $3, $4) RETURNING id
        """,
        user_id, triage_level, category, description,
    )
    logger.info("Case #%s created triage=%s", row["id"], triage_level)
    return row["id"]


async def create_booking(
    user_id: int,
    specialist_id: str,
    start_time,
    end_time,
    calendar_event_id: str | None = None,
) -> int:
    row = await pool().fetchrow(
        """
        INSERT INTO bookings (user_id, specialist_id, start_time, end_time, calendar_event_id)
        VALUES ($1, $2, $3, $4, $5) RETURNING id
        """,
        user_id, specialist_id, start_time, end_time, calendar_event_id,
    )
    return row["id"]


async def set_callback_requested(user_id: int) -> None:
    await pool().execute(
        "UPDATE users SET status = 'callback_requested' WHERE id = $1", user_id
    )


async def create_post_visit(
    booking_id: int,
    status: str,
    duration_minutes: int = 45,
    type_of_work: str | None = None,
    note_short: str | None = None,
) -> int:
    row = await pool().fetchrow(
        """
        INSERT INTO post_visit (booking_id, status, duration_minutes, type_of_work, note_short)
        VALUES ($1, $2, $3, $4, $5) RETURNING id
        """,
        booking_id, status, duration_minutes, type_of_work, note_short,
    )
    logger.info("Post-visit #%s created status=%s booking_id=%s", row["id"], status, booking_id)
    return row["id"]


async def get_sessions_for_sheet():
    """All post-visit records joined with booking info (no PII)."""
    return await pool().fetch("""
        SELECT b.start_time, b.end_time, b.specialist_id, b.user_id,
               pv.type_of_work, pv.duration_minutes, pv.status, pv.note_short
        FROM post_visit pv
        JOIN bookings b ON b.id = pv.booking_id
        ORDER BY b.start_time DESC
    """)


async def get_monthly_summary():
    """Aggregated hours per specialist per type of work."""
    return await pool().fetch("""
        SELECT
            EXTRACT(YEAR  FROM b.start_time)::int AS year,
            EXTRACT(MONTH FROM b.start_time)::int AS month,
            b.specialist_id,
            pv.type_of_work,
            SUM(pv.duration_minutes)::int AS total_minutes
        FROM post_visit pv
        JOIN bookings b ON b.id = pv.booking_id
        WHERE pv.status = 'completed'
        GROUP BY year, month, b.specialist_id, pv.type_of_work
        ORDER BY year DESC, month DESC, b.specialist_id
    """)


async def get_pending_bookings_for_notification():
    """
    Bookings where the post-visit notification hasn't been sent yet:
    - session end + 15 min is still in the future (not yet triggered), OR
    - session ended recently but no post_visit record exists (missed after restart)
    Excludes bookings that already have a post_visit entry.
    """
    return await pool().fetch("""
        SELECT b.id, b.specialist_id, b.start_time, b.end_time
        FROM bookings b
        WHERE b.end_time + INTERVAL '15 minutes' > CURRENT_DATE
          AND NOT EXISTS (
              SELECT 1 FROM post_visit pv WHERE pv.booking_id = b.id
          )
        ORDER BY b.end_time
    """)


async def get_intake_stats():
    """Anonymized intake data for reporting (no names, no Telegram IDs)."""
    return await pool().fetch("""
        SELECT DATE(u.created_at) AS date,
               u.language, u.age_cat,
               c.triage_level, c.category
        FROM cases c
        JOIN users u ON u.id = c.user_id
        ORDER BY c.created_at DESC
    """)
