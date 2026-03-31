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
                gdpr_accepted   BOOLEAN NOT NULL DEFAULT FALSE,
                status          TEXT NOT NULL DEFAULT 'active',
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
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
