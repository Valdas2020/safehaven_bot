"""
GDPR privacy commands.

/deleteme — hard-delete all personal data (Art. 17 right to erasure).
/privacy  — show privacy policy in user's language.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import database as db
from services.calendar import delete_user_calendar_events
from services.reporting import delete_user_from_sheets
from texts.privacy_policy import PRIVACY_POLICY
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="privacy")

_PRIVACY_BUTTON_TEXT = "🔒 Privacy Policy / Конфіденційність"


async def _get_lang(message: Message, state: FSMContext) -> str:
    fsm_data = await state.get_data()
    lang = fsm_data.get("lang")
    if not lang:
        user = await db.get_user(message.from_user.id)
        lang = user.get("language", "EN") if user else "EN"
    return lang


@router.message(Command("privacy"))
async def cmd_privacy(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message, state)
    await message.answer(
        PRIVACY_POLICY.get(lang, PRIVACY_POLICY["EN"]),
        parse_mode="HTML",
    )


@router.message(F.text == _PRIVACY_BUTTON_TEXT)
async def msg_privacy_button(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message, state)
    await message.answer(
        PRIVACY_POLICY.get(lang, PRIVACY_POLICY["EN"]),
        parse_mode="HTML",
    )


@router.message(Command("deleteme"))
async def cmd_deleteme(message: Message, state: FSMContext) -> None:
    lang = await _get_lang(message, state)

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
