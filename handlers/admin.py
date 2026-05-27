import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import database as db
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
router = Router(name="admin")
PRAGUE_TZ = ZoneInfo("Europe/Prague")


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
        "📊 <b>Reachable Stats</b>\n\n"
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


@router.message(Command("diag"))
async def cmd_diag(message: Message) -> None:
    """Admin diagnostic: inspect a Google Calendar for missing events."""
    if message.from_user.id not in ADMIN_IDS:
        return

    from services.calendar import _build_service

    args = message.text.strip().split()
    if len(args) < 2:
        await message.answer(
            "Usage: <code>/diag &lt;calendar_id&gt;</code>\n\n"
            'Example: <code>/diag c_e30ce55a...@group.calendar.google.com</code>',
            parse_mode="HTML",
        )
        return

    calendar_id = args[1].strip()
    windows = [
        ("2026-05-18", "2026-05-20", "May 19 bookings"),
        ("2026-05-25", "2026-05-27", "May 26 bookings"),
    ]

    await message.answer(f"🔍 Diagnosing <code>{calendar_id}</code>...", parse_mode="HTML")

    try:
        service = _build_service()
    except Exception as exc:
        await message.answer(f"❌ Failed to build calendar service: {exc}")
        return

    lines: list[str] = []

    for date_from, date_to, label in windows:
        tmin = datetime.fromisoformat(f"{date_from}T00:00:00").replace(tzinfo=PRAGUE_TZ).isoformat()
        tmax = datetime.fromisoformat(f"{date_to}T00:00:00").replace(tzinfo=PRAGUE_TZ).isoformat()

        try:
            events = service.events().list(
                calendarId=calendar_id,
                timeMin=tmin,
                timeMax=tmax,
                singleEvents=True,
                showDeleted=True,
                orderBy="startTime",
            ).execute()
        except Exception as exc:
            lines.append(f"<b>{label}:</b> ❌ {exc}")
            continue

        items = events.get("items", [])
        lines.append(f"<b>{label}:</b> {len(items)} event(s)")

        for ev in items:
            status = ev.get("status", "?")
            marker = " ⚠️CANCELLED" if status == "cancelled" else ""
            if status not in ("confirmed", "cancelled"):
                marker = f" [status={status}]"

            summary = ev.get("summary", "(none)")
            start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
            eid = ev.get("id", "?")
            updated = ev.get("updated", "?")

            lines.append(
                f"  {status}{marker} | {summary} | {start} | id={eid[:30]}... | updated={updated}"
            )

    # DB forensics
    rows = await db.pool().fetch(
        """
        SELECT b.id, b.user_id, b.specialist_id, b.calendar_event_id,
               b.start_time, b.created_at,
               u.telegram_id, u.name
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        WHERE b.start_time BETWEEN '2026-05-18' AND '2026-05-21'
           OR b.start_time BETWEEN '2026-05-25' AND '2026-05-28'
        ORDER BY b.start_time
        """
    )

    lines.append(f"\n<b>DB bookings in windows:</b> {len(rows)} row(s)")
    for r in rows:
        eid = r["calendar_event_id"]
        lines.append(
            f"  booking_id={r['id']} client={r['name']} tg={r['telegram_id']} "
            f"start={r['start_time']} event_id={eid[:30] if eid else 'NULL'}..."
        )

        if eid:
            try:
                ev = service.events().get(calendarId=r["specialist_id"], eventId=eid).execute()
                lines.append(f"    → GET OK status={ev.get('status','?')}")
            except Exception as exc:
                err = str(exc)[:100]
                lines.append(f"    → GET FAILED: {err}")

    result = "\n".join(lines)
    # Telegram limits: split if too long
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            await message.answer(result[i:i+4000], parse_mode="HTML")
    else:
        await message.answer(result, parse_mode="HTML")

    logger.info("Diag run by admin user_id=%s for calendar=%s", message.from_user.id, calendar_id)
