"""
GDPR privacy commands.

/deleteme — hard-delete all personal data for the requesting user (Art. 17 right to erasure).
"""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import database as db
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

    deleted = await db.delete_user_data(message.from_user.id)
    await state.clear()

    if deleted:
        await message.answer(t(lang, "deleteme_confirm"))
    else:
        await message.answer(t(lang, "deleteme_notfound"))
