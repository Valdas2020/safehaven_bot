import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from keyboards.inline import slots_keyboard, triage_keyboard
from services.calendar import get_free_slots
from states.user_states import UserFlow
from utils.i18n import t
from utils.triage import CATEGORY_TRIAGE, classify_text

logger = logging.getLogger(__name__)
router = Router(name="triage")


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

    # Normal flow → fetch slots matched to user profile
    fsm_data = await state.get_data()
    age_cat = fsm_data.get("age_cat", "adult")
    slots = await get_free_slots(lang, age_cat=age_cat, triage_level=triage_level)
    if not slots:
        await answer_fn(t(lang, "no_slots"))
        await state.clear()
        return

    await state.update_data(
        triage_description=description,
        slots=[
            {"specialist_id": s.specialist_id, "start": s.start.isoformat(), "end": s.end.isoformat()}
            for s in slots
        ],
    )
    await answer_fn(
        t(lang, "slots_header"),
        reply_markup=slots_keyboard(slots, lang),
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
        "cat_crisis":  {"UA": "🆘 Криза",        "RU": "🆘 Кризис",       "CZ": "🆘 Krize",       "EN": "🆘 Crisis"},
        "cat_consult": {"UA": "💬 Консультація", "RU": "💬 Консультация", "CZ": "💬 Konzultace", "EN": "💬 Consultation"},
        "cat_ikp":     {"UA": "🤝 Допомога / ІКП","RU": "🤝 Помощь / ИКП","CZ": "🤝 Pomoc / IKP","EN": "🤝 Assistance / IKP"},
    }
    description = category_labels.get(category, {}).get(lang, category)

    await callback.message.edit_reply_markup(reply_markup=None)
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
