import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

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


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=begin_keyboard(), parse_mode="HTML")
    await state.set_state(UserFlow.language_selection)
    logger.info("user_id=%s started the bot", message.from_user.id)


@router.callback_query(UserFlow.language_selection, F.data == "begin")
async def cb_begin(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "🌐 Оберіть мову / Выберите язык / Vyberte jazyk / Select language:",
        reply_markup=lang_keyboard(),
    )
    await callback.answer()
