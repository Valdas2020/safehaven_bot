import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import database as db
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from config import SPECIALIST_TG_IDS
from models import BookingWindow
from services.calendar import create_event_from_window
from services.mailer import notify_specialist, send_client_confirmation
from states.user_states import UserFlow
from utils.i18n import t

from handlers.post_visit import schedule_specialist_notification

logger = logging.getLogger(__name__)
router = Router(name="booking")
PRAGUE_TZ = ZoneInfo("Europe/Prague")


def _slot_details(start: datetime, end: datetime, sp_name: str) -> str:
    local = start.astimezone(PRAGUE_TZ)
    local_end = end.astimezone(PRAGUE_TZ)
    return (
        f"📅 {local.strftime('%A, %d.%m.%Y')}\n"
        f"🕐 {local.strftime('%H:%M')}–{local_end.strftime('%H:%M')} (Прага)\n"
        f"👤 {sp_name}"
    )


async def _send_reminder(bot, telegram_id: int, text: str, send_at: datetime) -> None:
    delay = (send_at - datetime.now(timezone.utc)).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        await bot.send_message(telegram_id, text, parse_mode="HTML")
        logger.info("Reminder sent to telegram_id=%s", telegram_id)
    except Exception as exc:
        logger.error("Failed to send reminder to %s: %s", telegram_id, exc)


OPERATOR_PHONE_DISPLAY = "+420 778 979 211"
IKP_PHONE_DISPLAY = "+420 720 489 028"

OPERATOR_MSG = {
    "UA": f"☎️ Оператор: {OPERATOR_PHONE_DISPLAY}",
    "RU": f"☎️ Оператор: {OPERATOR_PHONE_DISPLAY}",
    "CZ": f"☎️ Operátor: {OPERATOR_PHONE_DISPLAY}",
    "EN": f"☎️ Operator: {OPERATOR_PHONE_DISPLAY}",
}

IKP_MSG = {
    "UA": f"☎️ ІКП: {IKP_PHONE_DISPLAY}",
    "RU": f"☎️ ИКП: {IKP_PHONE_DISPLAY}",
    "CZ": f"☎️ IKP: {IKP_PHONE_DISPLAY}",
    "EN": f"☎️ IKP: {IKP_PHONE_DISPLAY}",
}


@router.callback_query(UserFlow.slot_selection, F.data == "call_operator")
async def cb_call_operator(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "RU")
    if data.get("triage_category") == "cat_ikp":
        await callback.message.answer(IKP_MSG.get(lang, IKP_MSG["RU"]))
    else:
        await callback.message.answer(OPERATOR_MSG.get(lang, OPERATOR_MSG["RU"]))
    await callback.answer()


@router.callback_query(UserFlow.slot_selection, F.data == "slot_callback")
async def cb_callback_request(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    db_user_id = data["db_user_id"]

    await db.set_callback_requested(db_user_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer(t(lang, "callback_saved"))
    await state.clear()
    await callback.answer()
    logger.info("Callback requested | user_id=%s", db_user_id)


@router.callback_query(UserFlow.slot_selection, F.data.startswith("slot_"))
async def cb_slot_selected(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data["lang"]
    db_user_id = data["db_user_id"]
    name = data.get("name", "User")
    windows_raw: list[dict] = data.get("windows", [])

    try:
        idx = int(callback.data.split("_", 1)[1])
        if idx >= len(windows_raw):
            raise IndexError
    except (ValueError, IndexError):
        await callback.answer("Invalid slot", show_alert=True)
        return

    window = BookingWindow.from_dict(windows_raw[idx])
    _tz = ZoneInfo("Europe/Prague")
    start = datetime(
        window.date.year,
        window.date.month,
        window.date.day,
        window.start.hour,
        window.start.minute,
        tzinfo=_tz,
    ).astimezone(timezone.utc)
    end = datetime(
        window.date.year,
        window.date.month,
        window.date.day,
        window.end.hour,
        window.end.minute,
        tzinfo=_tz,
    ).astimezone(timezone.utc)
    # display_end is what we show to clients (45 min, not the full 60-min block)
    client_end = datetime(
        window.date.year,
        window.date.month,
        window.date.day,
        window.display_end.hour,
        window.display_end.minute,
        tzinfo=_tz,
    ).astimezone(timezone.utc)

    # Create Google Calendar event
    event_id = create_event_from_window(
        window,
        callback.from_user.id,
        client_name=name,
        client_phone=data.get("phone", ""),
        client_email=data.get("email", ""),
        contact_method=data.get("contact_method", ""),
    )

    # Save booking to DB (calendar_id is the specialist key)
    booking_id = await db.create_booking(
        db_user_id, window.calendar_id, start, end, event_id
    )

    # Email notification to specialist
    description = data.get("triage_description", "—")
    age_years = data.get("age_years", "")
    logger.info(
        "notify_specialist | specialist=%s email=%s",
        window.specialist_name,
        window.specialist_email,
    )
    await notify_specialist(
        specialist_email=window.specialist_email or window.calendar_id,
        specialist_name=window.specialist_name,
        client_name=name,
        client_description=description,
        start=start,
        end=end,
        address=window.address or "",
        is_online=window.is_online,
        client_age=str(age_years) if age_years else "",
    )

    # Client confirmation email
    client_email = data.get("email", "")
    if client_email:
        await send_client_confirmation(
            client_email=client_email,
            client_name=name,
            specialist_name=window.specialist_name,
            start=start,
            end=client_end,
            lang=lang,
            address=window.address or "",
            is_online=window.is_online,
        )

    # Telegram confirmation
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer(window.confirmation_text(lang))

    # Reminder 2 hours before session
    reminder_details = (
        f"<b>{window.date.strftime('%d.%m.%Y')}</b>  "
        f"{window.start.strftime('%H:%M')}–{window.display_end.strftime('%H:%M')}\n"
        f"👤 {window.specialist_name}"
    )
    reminder_text = t(lang, "slot_reminder").format(details=reminder_details)
    remind_at = start - timedelta(hours=2)
    asyncio.create_task(
        _send_reminder(callback.bot, callback.from_user.id, reminder_text, remind_at)
    )

    # Post-visit prompt to specialist 15 min after session ends
    sp_tg_id = SPECIALIST_TG_IDS.get(window.calendar_id)
    if sp_tg_id:
        asyncio.create_task(
            schedule_specialist_notification(
                callback.bot, sp_tg_id, booking_id, start, end, window.specialist_name
            )
        )

    await state.clear()
    await callback.answer()
    logger.info(
        "Slot booked | user_id=%s calendar=%s start=%s event_id=%s",
        db_user_id,
        window.calendar_id,
        start,
        event_id,
    )


@router.message(UserFlow.slot_selection)
async def msg_slot_hint(message: Message, state: FSMContext) -> None:
    """User typed text instead of pressing a slot button — remind them."""
    data = await state.get_data()
    lang = data.get("lang", "EN")
    hint = {
        "UA": "👆 Будь ласка, оберіть слот кнопкою вище або натисніть «Передзвоніть мені».",
        "RU": "👆 Пожалуйста, выберите слот кнопкой выше или нажмите «Перезвоните мне».",
        "CZ": "👆 Prosím vyberte termín tlačítkem výše nebo zvolte «Zavolejte mi zpět».",
        "EN": "👆 Please select a slot using the buttons above, or tap «Please call me back».",
    }.get(lang, "👆 Please use the buttons above to select a slot.")
    await message.answer(hint)
