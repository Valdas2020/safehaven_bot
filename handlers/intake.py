import logging
import re

import database as db
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from keyboards.inline import (
    age_keyboard,
    yes_no_keyboard,
)
from states.user_states import UserFlow
from utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="intake")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Czech format: +420 or 420 followed by exactly 9 digits (spaces/hyphens allowed)
PHONE_RE = re.compile(r"^\+?420[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}$")


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
        logger.info(
            "user_id=%s not eligible: no protection status", callback.from_user.id
        )
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

    if len(name.split()) < 2:
        await message.answer(t(lang, "intake_name_invalid"))
        return

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
    age_key = "intake_age_number_child" if age_cat == "child" else "intake_age_number"
    await callback.message.answer(t(lang, age_key))
    await state.set_state(UserFlow.intake_age_number)
    await callback.answer()


# ── Step 4b: Age in years ─────────────────────────────────────────────────────


@router.message(UserFlow.intake_age_number)
async def msg_age_number(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    raw = message.text.strip()

    if not raw.isdigit() or not (1 <= int(raw) <= 120):
        await message.answer(t(lang, "intake_age_number_invalid"))
        return

    age_years = int(raw)
    await state.update_data(age_years=age_years)
    await db.upsert_user(message.from_user.id, age_years=age_years)

    data = await state.get_data()
    if data.get("age_cat") == "child":
        await message.answer(t(lang, "intake_child_first_name"))
        await state.set_state(UserFlow.intake_child_first_name)
    else:
        await message.answer(t(lang, "intake_email"))
        await state.set_state(UserFlow.intake_email)


# ── Step 4c: Child first name (only when age_cat == "child") ─────────────────


@router.message(UserFlow.intake_child_first_name)
async def msg_child_first_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    first_name = message.text.strip()[:64]

    if len(first_name) < 2:
        await message.answer(t(lang, "intake_child_name_invalid"))
        return

    await state.update_data(child_first_name=first_name)
    await message.answer(t(lang, "intake_child_last_name"))
    await state.set_state(UserFlow.intake_child_last_name)


# ── Step 4d: Child last name ──────────────────────────────────────────────────


@router.message(UserFlow.intake_child_last_name)
async def msg_child_last_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    last_name = message.text.strip()[:64]

    if len(last_name) < 2:
        await message.answer(t(lang, "intake_child_name_invalid"))
        return

    await state.update_data(child_last_name=last_name)
    await message.answer(t(lang, "intake_email"))
    await state.set_state(UserFlow.intake_email)


# ── Step 5: Email (required) ──────────────────────────────────────────────────


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


# ── Step 6: Phone (required) → triage ────────────────────────────────────────


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

    await _go_to_triage(message, lang, state)
    logger.info("user_id=%s completed intake", message.from_user.id)


# ── Helper ────────────────────────────────────────────────────────────────────


async def _go_to_triage(message, lang: str, state: FSMContext) -> None:
    await message.answer(t(lang, "intake_situation"))
    await state.set_state(UserFlow.intake_situation)


# ── Situation description → show triage buttons ───────────────────────────────


@router.message(UserFlow.intake_situation)
async def msg_situation(message: Message, state: FSMContext) -> None:
    from keyboards.inline import triage_keyboard as _triage_kb

    data = await state.get_data()
    lang = data["lang"]
    situation = message.text.strip()[:2000]

    await state.update_data(situation_description=situation)
    await message.answer(t(lang, "triage_prompt"), reply_markup=_triage_kb(lang))
    await message.answer(t(lang, "ikp_description"))
    await state.set_state(UserFlow.triage_choice)
