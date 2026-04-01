import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import database as db
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
router = Router(name="admin")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return  # silently ignore non-admins

    rows = await db.pool().fetch("""
        SELECT
            (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '1 day')   AS users_day,
            (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '7 days')  AS users_week,
            (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '30 days') AS users_month,
            (SELECT COUNT(*) FROM bookings WHERE created_at >= NOW() - INTERVAL '1 day')   AS books_day,
            (SELECT COUNT(*) FROM bookings WHERE created_at >= NOW() - INTERVAL '7 days')  AS books_week,
            (SELECT COUNT(*) FROM bookings WHERE created_at >= NOW() - INTERVAL '30 days') AS books_month
    """)
    r = rows[0]

    # Sessions by specialist type (based on specialist_id prefix convention)
    sp_rows = await db.pool().fetch("""
        SELECT specialist_id, COUNT(*) AS cnt
        FROM bookings
        GROUP BY specialist_id
        ORDER BY cnt DESC
    """)

    sp_lines = []
    for row in sp_rows:
        sp_lines.append(f"  • {row['specialist_id']}: {row['cnt']}")
    sp_block = "\n".join(sp_lines) if sp_lines else "  (no bookings yet)"

    text = (
        "📊 <b>SafeHaven Stats</b>\n\n"
        "<b>New clients</b>\n"
        f"  Today: {r['users_day']}\n"
        f"  Week:  {r['users_week']}\n"
        f"  Month: {r['users_month']}\n\n"
        "<b>Sessions booked</b>\n"
        f"  Today: {r['books_day']}\n"
        f"  Week:  {r['books_week']}\n"
        f"  Month: {r['books_month']}\n\n"
        "<b>Sessions by specialist</b>\n"
        f"{sp_block}"
    )

    await message.answer(text, parse_mode="HTML")
    logger.info("Stats requested by admin user_id=%s", message.from_user.id)
