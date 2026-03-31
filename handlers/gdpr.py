import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import database as db
from keyboards.inline import gdpr_keyboard
from states.user_states import UserFlow
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="gdpr")


@router.callback_query(UserFlow.language_selection, F.data.startswith("lang_"))
async def cb_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split("_", 1)[1]  # UA / RU / CZ / EN
    await state.update_data(lang=lang)

    user = await db.upsert_user(callback.from_user.id, language=lang)
    await state.update_data(db_user_id=user["id"])

    await callback.message.edit_text(
        t(lang, "gdpr"),
        reply_markup=gdpr_keyboard(lang),
        parse_mode="Markdown",
    )
    await state.set_state(UserFlow.gdpr_consent)
    await callback.answer()


@router.callback_query(UserFlow.gdpr_consent, F.data == "gdpr_accept")
async def cb_gdpr_accept(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    await db.upsert_user(callback.from_user.id, gdpr_accepted=True)

    await callback.message.edit_text(t(lang, "intake_name"), parse_mode="Markdown")
    await state.set_state(UserFlow.intake_name)
    await callback.answer()


@router.callback_query(UserFlow.gdpr_consent, F.data == "gdpr_decline")
async def cb_gdpr_decline(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    await db.upsert_user(callback.from_user.id, status="archived")
    await callback.message.edit_text(t(lang, "gdpr_decline"))
    await state.clear()
    await callback.answer()
    logger.info("user_id=%s declined GDPR", callback.from_user.id)
