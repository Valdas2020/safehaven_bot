from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.i18n import t
from services.calendar import Slot, SPECIALISTS


def begin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶️  Start / Почати / Начать", callback_data="begin"),
    ]])


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_UA"),
            InlineKeyboardButton(text="🇷🇺 Русский",    callback_data="lang_RU"),
        ],
        [
            InlineKeyboardButton(text="🇨🇿 Čeština",    callback_data="lang_CZ"),
            InlineKeyboardButton(text="🇬🇧 English",    callback_data="lang_EN"),
        ],
    ])


def gdpr_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_accept"),  callback_data="gdpr_accept"),
        InlineKeyboardButton(text=t(lang, "btn_decline"), callback_data="gdpr_decline"),
    ]])


def age_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "age_child"), callback_data="age_child"),
        InlineKeyboardButton(text=t(lang, "age_adult"), callback_data="age_adult"),
    ]])


def format_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "format_online"),    callback_data="fmt_online"),
        InlineKeyboardButton(text=t(lang, "format_in_person"), callback_data="fmt_in_person"),
    ]])


def skip_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="skip"),
    ]])


def contact_method_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "contact_phone"),    callback_data="cm_phone"),
            InlineKeyboardButton(text=t(lang, "contact_telegram"), callback_data="cm_telegram"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="skip"),
        ],
    ])


def triage_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cat_crisis"),  callback_data="cat_crisis")],
        [InlineKeyboardButton(text=t(lang, "cat_consult"), callback_data="cat_consult")],
        [InlineKeyboardButton(text=t(lang, "cat_ikp"),     callback_data="cat_ikp")],
    ])


OPERATOR_PHONE = "tel:+420736101609"

def slots_keyboard(slots: list[Slot], lang: str) -> InlineKeyboardMarkup:
    rows = []
    for i, slot in enumerate(slots):
        sp = SPECIALISTS.get(slot.specialist_id, {})
        spec = sp.get("name", "")
        label = f"{slot.label(lang)} — {spec}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"slot_{i}")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_callback"), callback_data="slot_callback")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_call_operator"), url=OPERATOR_PHONE)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
