import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.inline import lang_keyboard
from states.user_states import UserFlow
from utils.i18n import TEXTS

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    # Use first available language for the initial prompt (it's just "pick your language")
    first_lang = next(iter(TEXTS))
    await message.answer(
        TEXTS[first_lang]["lang_prompt"],
        reply_markup=lang_keyboard(),
    )
    await state.set_state(UserFlow.language_selection)
    logger.info("user_id=%s started the bot", message.from_user.id)
