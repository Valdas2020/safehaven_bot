"""
Fallback handler — catches any unhandled callback_query or message
(e.g. stale buttons after a server restart) and asks user to /start again.
"""
import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)
router = Router(name="fallback")

RESTART_TEXT = (
    "🔄 Сессия устарела — пожалуйста, начните заново: /start\n"
    "Session expired — please restart: /start"
)


@router.callback_query()
async def fallback_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.answer(RESTART_TEXT)
    logger.info("Fallback callback | user_id=%s data=%s", callback.from_user.id, callback.data)


@router.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(RESTART_TEXT)
    logger.info("Fallback message | user_id=%s text=%s", message.from_user.id, message.text)
