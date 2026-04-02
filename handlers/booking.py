import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from config import SPECIALIST_TG_IDS
from handlers.post_visit import schedule_specialist_notification
from services.calendar import SPECIALISTS, create_calendar_event
from services.mailer import notify_specialist, send_client_confirmation
from states.user_states import UserFlow
from utils.i18n import t

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


OPERATOR_PHONE_DISPLAY = "+420 736 101 609"

OPERATOR_MSG = {
    "UA": f"☎️ Оператор: {OPERATOR_PHONE_DISPLAY}",
    "RU": f"☎️ Оператор: {OPERATOR_PHONE_DISPLAY}",
    "CZ": f"☎️ Operátor: {OPERATOR_PHONE_DISPLAY}",
    "EN": f"☎️ Operator: {OPERATOR_PHONE_DISPLAY}",
}


@router.callback_query(UserFlow.slot_selection, F.data == "call_operator")
async def cb_call_operator(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "RU")
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
    slots_raw: list[dict] = data.get("slots", [])

    try:
        idx = int(callback.data.split("_", 1)[1])
        chosen = slots_raw[idx]
    except (ValueError, IndexError):
        await callback.answer("Invalid slot", show_alert=True)
        return

    start = datetime.fromisoformat(chosen["start"]).replace(tzinfo=timezone.utc)
    end   = datetime.fromisoformat(chosen["end"]).replace(tzinfo=timezone.utc)
    specialist_id = chosen["specialist_id"]

    # Create Google Calendar event with client contact info
    event_id = create_calendar_event(
        specialist_id,
        callback.from_user.id,
        start,
        end,
        client_name=name,
        client_phone=data.get("phone", ""),
        client_email=data.get("email", ""),
        contact_method=data.get("contact_method", ""),
    )

    # Save booking to DB
    booking_id = await db.create_booking(db_user_id, specialist_id, start, end, event_id)

    # Send email notification to specialist
    sp = SPECIALISTS.get(specialist_id, {})
    description = data.get("triage_description", "—")
    await notify_specialist(
        specialist_email=sp.get("email", sp.get("calendar_id", "")),
        specialist_name=sp.get("name", specialist_id),
        client_name=data.get("name", "—"),
        client_description=description,
        start=start,
        end=end,
    )

    sp_name = sp.get("name", specialist_id)
    details = _slot_details(start, end, sp_name)

    # Send client confirmation email (if provided)
    client_email = data.get("email", "")
    if client_email:
        await send_client_confirmation(
            client_email=client_email,
            client_name=name,
            specialist_name=sp_name,
            start=start,
            end=end,
            lang=lang,
        )

    # Telegram confirmation
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer(
        t(lang, "slot_booked").format(details=details),
        parse_mode="HTML",
    )

    # Schedule Telegram reminder 2 hours before the session
    reminder_text = t(lang, "slot_reminder").format(details=details)
    remind_at = start - timedelta(hours=2)
    asyncio.create_task(
        _send_reminder(callback.bot, callback.from_user.id, reminder_text, remind_at)
    )

    # Schedule post-visit prompt to specialist 15 min after session ends
    sp_tg_id = SPECIALIST_TG_IDS.get(specialist_id)
    if sp_tg_id:
        asyncio.create_task(
            schedule_specialist_notification(
                callback.bot, sp_tg_id, booking_id, start, end, sp_name
            )
        )

    await state.clear()
    await callback.answer()
    logger.info(
        "Slot booked | user_id=%s specialist=%s start=%s event_id=%s",
        db_user_id, specialist_id, start, event_id,
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
