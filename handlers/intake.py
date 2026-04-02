import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards.inline import age_keyboard, contact_method_keyboard, format_keyboard, skip_keyboard, triage_keyboard
from states.user_states import UserFlow
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="intake")


# ── Step 1: Name ────────────────────────────────────────────────────────────

@router.message(UserFlow.intake_name)
async def msg_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    name = message.text.strip()[:64]  # sanitise length

    await state.update_data(name=name)
    await db.upsert_user(message.from_user.id, name=name)

    await message.answer(t(lang, "intake_age"), reply_markup=age_keyboard(lang))
    await state.set_state(UserFlow.intake_age)


# ── Step 2: Age ──────────────────────────────────────────────────────────────

@router.callback_query(UserFlow.intake_age, F.data.in_({"age_child", "age_adult"}))
async def cb_age(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    age_cat = "child" if callback.data == "age_child" else "adult"

    await state.update_data(age_cat=age_cat)
    await db.upsert_user(callback.from_user.id, age_cat=age_cat)

    await callback.message.edit_text(t(lang, "intake_location"), parse_mode="Markdown")
    await state.set_state(UserFlow.intake_location)
    await callback.answer()


# ── Step 3: Location ─────────────────────────────────────────────────────────

@router.message(UserFlow.intake_location)
async def msg_location(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    location = message.text.strip()[:128]

    await state.update_data(location=location)
    await db.upsert_user(message.from_user.id, location=location)

    await message.answer(t(lang, "intake_format"), reply_markup=format_keyboard(lang))
    await state.set_state(UserFlow.intake_format)


# ── Step 4: Format ───────────────────────────────────────────────────────────

@router.callback_query(UserFlow.intake_format, F.data.in_({"fmt_online", "fmt_in_person"}))
async def cb_format(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    fmt = "online" if callback.data == "fmt_online" else "in_person"

    await state.update_data(format=fmt)
    await db.upsert_user(callback.from_user.id, format=fmt)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer(
        t(lang, "intake_email"),
        reply_markup=skip_keyboard(lang),
        parse_mode="Markdown",
    )
    await state.set_state(UserFlow.intake_email)
    await callback.answer()


# ── Step 5: Email ─────────────────────────────────────────────────────────────

@router.message(UserFlow.intake_email)
async def msg_email(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    email = message.text.strip()[:254]

    await state.update_data(email=email)
    await db.upsert_user(message.from_user.id, email=email)

    await message.answer(t(lang, "intake_phone"), reply_markup=skip_keyboard(lang), parse_mode="Markdown")
    await state.set_state(UserFlow.intake_phone)


@router.callback_query(UserFlow.intake_email, F.data == "skip")
async def cb_skip_email(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer(t(lang, "intake_phone"), reply_markup=skip_keyboard(lang), parse_mode="Markdown")
    await state.set_state(UserFlow.intake_phone)
    await callback.answer()


# ── Step 6: Phone ─────────────────────────────────────────────────────────────

@router.message(UserFlow.intake_phone)
async def msg_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    phone = message.text.strip()[:32]

    await state.update_data(phone=phone)
    await db.upsert_user(message.from_user.id, phone=phone)

    await message.answer(t(lang, "intake_contact_method"), reply_markup=contact_method_keyboard(lang))
    await state.set_state(UserFlow.intake_contact_method)


@router.callback_query(UserFlow.intake_phone, F.data == "skip")
async def cb_skip_phone(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await _go_to_triage(callback.message, lang, state)
    await callback.answer()
    logger.info("user_id=%s completed intake (no phone)", callback.from_user.id)


# ── Step 7: Contact method ────────────────────────────────────────────────────

@router.callback_query(
    UserFlow.intake_contact_method,
    F.data.in_({"cm_phone", "cm_viber", "cm_whatsapp", "cm_telegram", "skip"}),
)
async def cb_contact_method(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    if callback.data != "skip":
        cm = callback.data[3:]  # strip "cm_" prefix
        await state.update_data(contact_method=cm)
        await db.upsert_user(callback.from_user.id, contact_method=cm)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await _go_to_triage(callback.message, lang, state)
    await callback.answer()
    logger.info("user_id=%s completed intake", callback.from_user.id)


async def _go_to_triage(message, lang: str, state: FSMContext) -> None:
    from keyboards.inline import triage_keyboard as _triage_kb
    await message.answer(
        t(lang, "triage_prompt"),
        reply_markup=_triage_kb(lang),
        parse_mode="Markdown",
    )
    await state.set_state(UserFlow.triage_choice)
