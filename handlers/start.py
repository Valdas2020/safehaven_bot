import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, KeyboardButton, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

from keyboards.inline import begin_keyboard, lang_keyboard
from states.user_states import UserFlow

logger = logging.getLogger(__name__)
router = Router(name="start")

WELCOME_TEXT = (
    "💙 <b>SafeHaven</b>\n\n"
    "🇺🇦 Психологічна підтримка для українців у Чехії.\n"
    "🇷🇺 Психологическая поддержка для украинцев в Чехии.\n"
    "🇨🇿 Psychologická podpora pro Ukrajince v ČR.\n"
    "🇬🇧 Psychological support for Ukrainians in Czechia."
)

# Persistent restart button — shown as Reply keyboard throughout the flow
RESTART_TEXT = "🔄 Начать заново"

def _restart_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=RESTART_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="...",
    )


async def _do_start(message: Message, state: FSMContext) -> None:
    """Common logic for /start and restart button."""
    await state.clear()
    await message.answer(
        WELCOME_TEXT,
        reply_markup=_restart_kb(),
        parse_mode="HTML",
    )
    await message.answer(
        "🌐 Оберіть мову / Выберите язык / Vyberte jazyk / Select language:",
        reply_markup=lang_keyboard(),
    )
    await state.set_state(UserFlow.language_selection)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await _do_start(message, state)
    logger.info("user_id=%s started the bot", message.from_user.id)


@router.message(F.text == RESTART_TEXT)
async def msg_restart(message: Message, state: FSMContext) -> None:
    """Restart button pressed at any point in the flow."""
    await _do_start(message, state)
    logger.info("user_id=%s restarted via button", message.from_user.id)


@router.callback_query(UserFlow.language_selection, F.data == "begin")
async def cb_begin(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "🌐 Оберіть мову / Выберите язык / Vyberte jazyk / Select language:",
        reply_markup=lang_keyboard(),
    )
    await callback.answer()
