import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards.inline import (
    age_keyboard, contact_method_keyboard, format_keyboard,
    yes_no_keyboard,
)
from states.user_states import UserFlow
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="intake")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"\d{7,}")  # at least 7 digits anywhere in the string


# ── Step 1: Prague eligibility (state set by gdpr.py) ────────────────────────

@router.callback_query(UserFlow.intake_prague, F.data.in_({"yn_yes", "yn_no"}))
async def cb_prague(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    if callback.data == "yn_no":
        await callback.message.answer(t(lang, "not_eligible_prague"))
        await state.clear()
        await callback.answer()
        logger.info("user_id=%s not eligible: not in Prague", callback.from_user.id)
        return

    await callback.message.answer(
        t(lang, "intake_protection"),
        reply_markup=yes_no_keyboard(lang),
    )
    await state.set_state(UserFlow.intake_protection)
    await callback.answer()


# ── Step 2: Temporary protection status ──────────────────────────────────────

@router.callback_query(UserFlow.intake_protection, F.data.in_({"yn_yes", "yn_no"}))
async def cb_protection(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    if callback.data == "yn_no":
        await callback.message.answer(t(lang, "not_eligible_protection"))
        await state.clear()
        await callback.answer()
        logger.info("user_id=%s not eligible: no protection status", callback.from_user.id)
        return

    await callback.message.answer(t(lang, "intake_name"))
    await state.set_state(UserFlow.intake_name)
    await callback.answer()


# ── Step 3: Name ──────────────────────────────────────────────────────────────

@router.message(UserFlow.intake_name)
async def msg_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    name = message.text.strip()[:64]

    await state.update_data(name=name)
    await db.upsert_user(message.from_user.id, name=name)

    await message.answer(t(lang, "intake_age"), reply_markup=age_keyboard(lang))
    await state.set_state(UserFlow.intake_age)


# ── Step 4: Age ───────────────────────────────────────────────────────────────

@router.callback_query(UserFlow.intake_age, F.data.in_({"age_child", "age_adult"}))
async def cb_age(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    age_cat = "child" if callback.data == "age_child" else "adult"

    await state.update_data(age_cat=age_cat)
    await db.upsert_user(callback.from_user.id, age_cat=age_cat)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer(t(lang, "intake_format"), reply_markup=format_keyboard(lang))
    await state.set_state(UserFlow.intake_format)
    await callback.answer()


# ── Step 5: Format ────────────────────────────────────────────────────────────

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
    await callback.message.answer(t(lang, "intake_email"))
    await state.set_state(UserFlow.intake_email)
    await callback.answer()


# ── Step 6: Email (required) ──────────────────────────────────────────────────

@router.message(UserFlow.intake_email)
async def msg_email(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    email = message.text.strip()

    if not EMAIL_RE.match(email):
        await message.answer(t(lang, "intake_email_invalid"))
        return

    await state.update_data(email=email[:254])
    await db.upsert_user(message.from_user.id, email=email[:254])

    await message.answer(t(lang, "intake_phone"))
    await state.set_state(UserFlow.intake_phone)


# ── Step 7: Phone (required) ──────────────────────────────────────────────────

@router.message(UserFlow.intake_phone)
async def msg_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    phone = message.text.strip()

    if not PHONE_RE.search(phone):
        await message.answer(t(lang, "intake_phone_invalid"))
        return

    await state.update_data(phone=phone[:32])
    await db.upsert_user(message.from_user.id, phone=phone[:32])

    await message.answer(t(lang, "intake_contact_method"), reply_markup=contact_method_keyboard(lang))
    await state.set_state(UserFlow.intake_contact_method)


# ── Step 8: Contact method → triage ──────────────────────────────────────────

@router.callback_query(
    UserFlow.intake_contact_method,
    F.data.in_({"cm_phone", "cm_telegram", "skip"}),
)
async def cb_contact_method(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]

    if callback.data != "skip":
        cm = callback.data[3:]  # strip "cm_"
        await state.update_data(contact_method=cm)
        await db.upsert_user(callback.from_user.id, contact_method=cm)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await _go_to_triage(callback.message, lang, state)
    await callback.answer()
    logger.info("user_id=%s completed intake", callback.from_user.id)


# ── Helper ────────────────────────────────────────────────────────────────────

async def _go_to_triage(message, lang: str, state: FSMContext) -> None:
    from keyboards.inline import triage_keyboard as _triage_kb
    await message.answer(
        t(lang, "triage_prompt"),
        reply_markup=_triage_kb(lang),
        parse_mode="Markdown",
    )
    await state.set_state(UserFlow.triage_choice)
