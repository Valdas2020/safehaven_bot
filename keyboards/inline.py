from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from models import BookingWindow
from services.calendar import SPECIALISTS, Slot
from utils.i18n import t


def begin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️  Start / Почати / Начать", callback_data="begin"
                ),
            ]
        ]
    )


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_UA"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_RU"),
            ],
            [
                InlineKeyboardButton(text="🇨🇿 Čeština", callback_data="lang_CZ"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_EN"),
            ],
        ]
    )


_PP_LABEL = {
    "UA": "📄 Політика конфіденційності",
    "RU": "📄 Политика конфиденциальности",
    "CZ": "📄 Zásady ochrany osobních údajů",
    "EN": "📄 Privacy Policy",
}

_BACK_LABEL = {
    "UA": "⬅️ Назад",
    "RU": "⬅️ Назад",
    "CZ": "⬅️ Zpět",
    "EN": "⬅️ Back",
}


def gdpr_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_accept"), callback_data="gdpr_accept"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_decline"), callback_data="gdpr_decline"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_PP_LABEL.get(lang, _PP_LABEL["EN"]),
                    callback_data="show_privacy_from_consent",
                )
            ],
        ]
    )


def privacy_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_BACK_LABEL.get(lang, _BACK_LABEL["EN"]),
                    callback_data="back_to_gdpr",
                )
            ]
        ]
    )


def age_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "age_child"), callback_data="age_child"
                ),
                InlineKeyboardButton(
                    text=t(lang, "age_adult"), callback_data="age_adult"
                ),
            ]
        ]
    )


def format_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "format_online"), callback_data="fmt_online"
                ),
                InlineKeyboardButton(
                    text=t(lang, "format_in_person"), callback_data="fmt_in_person"
                ),
            ]
        ]
    )


def yes_no_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_yes"), callback_data="yn_yes"),
                InlineKeyboardButton(text=t(lang, "btn_no"), callback_data="yn_no"),
            ]
        ]
    )


def skip_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="skip"),
            ]
        ]
    )


def contact_method_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "contact_phone"), callback_data="cm_phone"
                ),
                InlineKeyboardButton(
                    text=t(lang, "contact_telegram"), callback_data="cm_telegram"
                ),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="skip"),
            ],
        ]
    )


def triage_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "cat_crisis"), callback_data="cat_crisis"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "cat_consult"), callback_data="cat_consult"
                )
            ],
            [InlineKeyboardButton(text=t(lang, "cat_ikp"), callback_data="cat_ikp")],
        ]
    )


def slots_keyboard(slots: list[Slot], lang: str) -> InlineKeyboardMarkup:
    rows = []
    for i, slot in enumerate(slots):
        sp = SPECIALISTS.get(slot.specialist_id, {})
        name_i18n = sp.get("name_i18n", {})
        spec = name_i18n.get(lang, name_i18n.get("EN", sp.get("name", "")))
        label = f"{slot.label(lang)} — {spec}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"slot_{i}")])
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "btn_callback"), callback_data="slot_callback"
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "btn_call_operator"), callback_data="call_operator"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def windows_keyboard(windows: list[BookingWindow], lang: str) -> InlineKeyboardMarkup:
    rows = []
    for i, w in enumerate(windows):
        label = f"{w.label(lang)} — {w.specialist_name}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"slot_{i}")])
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "btn_callback"), callback_data="slot_callback"
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "btn_call_operator"), callback_data="call_operator"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
