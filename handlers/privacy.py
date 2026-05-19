"""
GDPR privacy commands.

/deleteme — hard-delete all personal data for the requesting user (Art. 17 right to erasure).
"""

import logging

import database as db
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from services.calendar import delete_user_calendar_events
from services.reporting import delete_user_from_sheets
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="privacy")


@router.message(Command("deleteme"))
async def cmd_deleteme(message: Message, state: FSMContext) -> None:
    # Determine language from FSM state if available, else fall back to DB
    fsm_data = await state.get_data()
    lang = fsm_data.get("lang")

    if not lang:
        user = await db.get_user(message.from_user.id)
        lang = user.get("language", "EN") if user else "EN"

    # 1. Collect bookings before deleting DB rows (we need calendar_event_id)
    bookings = await db.get_user_bookings_with_calendar(message.from_user.id)

    # 2. Delete Google Calendar events
    if bookings:
        await delete_user_calendar_events(bookings)

    # 3. Delete Google Sheets rows (Sessions_Log)
    await delete_user_from_sheets(message.from_user.id)

    # 4. Delete all DB data
    deleted = await db.delete_user_data(message.from_user.id)
    await state.clear()

    if deleted:
        await message.answer(t(lang, "deleteme_confirm"))
    else:
        await message.answer(t(lang, "deleteme_notfound"))
