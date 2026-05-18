import logging
from datetime import date, timedelta

import database as db
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from config import SCHEDULE_SHEET_TAB, SPREADSHEET_ID
from keyboards.inline import windows_keyboard
from services.calendar import SPECIALISTS, match_specialists
from services.sheets_repository import get_windows_for_calendars
from states.user_states import UserFlow
from utils.i18n import t
from utils.triage import CATEGORY_TRIAGE, classify_text

logger = logging.getLogger(__name__)
router = Router(name="triage")

# Maps triage category to specialist type for filtering
_CATEGORY_SP_TYPE: dict[str, str] = {
    "cat_consult": "psychologist",
    "cat_ikp": "ikp",
}


async def _handle_triage_result(
    telegram_id: int,
    db_user_id: int,
    lang: str,
    triage_level: str,
    category: str,
    description: str,
    answer_fn,
    state: FSMContext,
) -> None:
    await db.create_case(db_user_id, triage_level, category, description)

    if triage_level == "urgent":
        await answer_fn(t(lang, "triage_urgent"), parse_mode="Markdown")
        logger.warning("URGENT | telegram_id=%s category=%s", telegram_id, category)
        await state.clear()
        return

    # Match specialists by age group and service type
    data = await state.get_data()
    age_cat = data.get("age_cat", "adult")
    sp_type = _CATEGORY_SP_TYPE.get(category)  # None = any type (free_text)
    matched_ids = match_specialists(age_cat, triage_level, sp_type)
    calendar_ids = [SPECIALISTS[sp_id]["calendar_id"] for sp_id in matched_ids]

    logger.info(
        "Slot search | age=%s triage=%s category=%s matched=%s",
        age_cat,
        triage_level,
        category,
        matched_ids,
    )

    today = date.today()
    windows = await get_windows_for_calendars(
        calendar_ids,
        today,
        today + timedelta(days=14),
        SPREADSHEET_ID,
        SCHEDULE_SHEET_TAB,
    )
    if not windows:
        await answer_fn(t(lang, "no_slots"))
        await state.clear()
        return

    await state.update_data(
        triage_description=description,
        triage_category=category,
        windows=[w.to_dict() for w in windows],
    )
    await answer_fn(
        t(lang, "slots_header"),
        reply_markup=windows_keyboard(windows, lang),
    )
    await state.set_state(UserFlow.slot_selection)


@router.callback_query(
    UserFlow.triage_choice,
    F.data.in_({"cat_crisis", "cat_consult", "cat_ikp"}),
)
async def cb_category(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    db_user_id = data["db_user_id"]
    category = callback.data
    triage_level = CATEGORY_TRIAGE[category]

    category_labels = {
        "cat_crisis": {
            "UA": "🆘 Криза",
            "RU": "🆘 Кризис",
            "CZ": "🆘 Krize",
            "EN": "🆘 Crisis",
        },
        "cat_consult": {
            "UA": "🧠 Психолог",
            "RU": "🧠 Психолог",
            "CZ": "🧠 Psycholog",
            "EN": "🧠 Psychologist",
        },
        "cat_ikp": {
            "UA": "🤝 Допомога / ІКП",
            "RU": "🤝 Помощь / ИКП",
            "CZ": "🤝 Pomoc / IKP",
            "EN": "🤝 Assistance / IKP",
        },
    }
    description = category_labels.get(category, {}).get(lang, category)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass  # already removed (double-tap)
    await _handle_triage_result(
        telegram_id=callback.from_user.id,
        db_user_id=db_user_id,
        lang=lang,
        triage_level=triage_level,
        category=category,
        description=description,
        answer_fn=lambda text, **kw: callback.message.answer(text, **kw),
        state=state,
    )
    await callback.answer()


@router.message(UserFlow.triage_choice)
async def msg_free_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    db_user_id = data["db_user_id"]
    description = message.text.strip()[:2000]
    triage_level = classify_text(description)

    await _handle_triage_result(
        telegram_id=message.from_user.id,
        db_user_id=db_user_id,
        lang=lang,
        triage_level=triage_level,
        category="free_text",
        description=description,
        answer_fn=lambda text, **kw: message.answer(text, **kw),
        state=state,
    )
