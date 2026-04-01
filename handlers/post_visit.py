"""
Post-visit reporting flow for specialists.

Triggered 15 minutes after a session ends.
The specialist receives an inline keyboard to report the outcome.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
from services.reporting import sync_after_post_visit
from states.user_states import SpecialistFlow

logger = logging.getLogger(__name__)
router = Router(name="post_visit")
PRAGUE_TZ = ZoneInfo("Europe/Prague")

# Short codes used in callback_data → full DB values
TYPE_MAP = {
    "cons": "consultation",
    "intk": "intake",
    "dopr": "doprovod",
    "admn": "admin",
}


# ── Scheduler — called from booking.py after booking is confirmed ──────────────

async def schedule_specialist_notification(
    bot,
    specialist_tg_id: int,
    booking_id: int,
    start: datetime,
    end: datetime,
    sp_name: str,
) -> None:
    """Sleep until 15 min after session end, then ask the specialist for a report."""
    notify_at = end + timedelta(minutes=15)
    delay = (notify_at - datetime.now(timezone.utc)).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)

    local_start = start.astimezone(PRAGUE_TZ)
    local_end   = end.astimezone(PRAGUE_TZ)
    session_label = (
        f"{local_start.strftime('%d.%m.%Y')}  "
        f"{local_start.strftime('%H:%M')}–{local_end.strftime('%H:%M')}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Завершено",   callback_data=f"pv_comp_{booking_id}"),
            InlineKeyboardButton(text="❌ Не явился",   callback_data=f"pv_noshow_{booking_id}"),
        ],
        [
            InlineKeyboardButton(text="📅 Перенесено",  callback_data=f"pv_resc_{booking_id}"),
        ],
    ])

    try:
        await bot.send_message(
            specialist_tg_id,
            f"📋 <b>Отчёт о сессии</b>\n\n"
            f"🗓 {session_label}\n\n"
            f"Как прошла встреча с клиентом?",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        logger.info(
            "Post-visit prompt sent tg_id=%s booking_id=%s", specialist_tg_id, booking_id
        )
    except Exception as exc:
        logger.error("Failed to send post-visit prompt to %s: %s", specialist_tg_id, exc)


# ── Step 1: Status selection ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv_noshow_"))
async def cb_noshow(callback: CallbackQuery) -> None:
    booking_id = int(callback.data.removeprefix("pv_noshow_"))
    await db.create_post_visit(booking_id, status="no_show")
    await sync_after_post_visit(booking_id)
    await callback.message.edit_text(
        "✅ Отмечено: <b>клиент не явился</b>. Отчёт сохранён.",
        reply_markup=None, parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pv_resc_"))
async def cb_rescheduled(callback: CallbackQuery) -> None:
    booking_id = int(callback.data.removeprefix("pv_resc_"))
    await db.create_post_visit(booking_id, status="rescheduled")
    await sync_after_post_visit(booking_id)
    await callback.message.edit_text(
        "✅ Отмечено: <b>перенесено</b>. Отчёт сохранён.",
        reply_markup=None, parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pv_comp_"))
async def cb_completed(callback: CallbackQuery) -> None:
    booking_id = callback.data.removeprefix("pv_comp_")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="45 мин", callback_data=f"pvd_45_{booking_id}"),
        InlineKeyboardButton(text="60 мин", callback_data=f"pvd_60_{booking_id}"),
        InlineKeyboardButton(text="90 мин", callback_data=f"pvd_90_{booking_id}"),
    ]])
    await callback.message.edit_text("⏱ Продолжительность сессии:", reply_markup=keyboard)
    await callback.answer()


# ── Step 2: Duration selection ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pvd_"))
async def cb_duration(callback: CallbackQuery) -> None:
    _, minutes, booking_id = callback.data.split("_", 2)  # pvd / 45 / 12345
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Консультация",   callback_data=f"pvt_cons_{booking_id}_{minutes}"),
            InlineKeyboardButton(text="📋 Приём",           callback_data=f"pvt_intk_{booking_id}_{minutes}"),
        ],
        [
            InlineKeyboardButton(text="🚶 Сопровождение",  callback_data=f"pvt_dopr_{booking_id}_{minutes}"),
            InlineKeyboardButton(text="📊 Административ.", callback_data=f"pvt_admn_{booking_id}_{minutes}"),
        ],
    ])
    await callback.message.edit_text("📂 Тип работы:", reply_markup=keyboard)
    await callback.answer()


# ── Step 3: Type of work selection ────────────────────────────────────────────

@router.callback_query(F.data.startswith("pvt_"))
async def cb_type(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("_", 3)  # pvt / cons / 12345 / 45
    type_code   = parts[1]
    booking_id  = int(parts[2])
    minutes     = int(parts[3])
    type_of_work = TYPE_MAP.get(type_code, "consultation")

    await state.update_data(pv_booking_id=booking_id, pv_duration=minutes, pv_type=type_of_work)
    await state.set_state(SpecialistFlow.awaiting_note)

    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ Пропустить", callback_data="pvnote_skip"),
    ]])
    await callback.message.edit_text(
        "📝 Добавьте короткую заметку (до 200 символов) или пропустите:",
        reply_markup=skip_kb,
    )
    await callback.answer()


# ── Step 4: Note (text or skip) ───────────────────────────────────────────────

@router.callback_query(SpecialistFlow.awaiting_note, F.data == "pvnote_skip")
async def cb_skip_note(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await _save_completed(data, note=None)
    await state.clear()
    await callback.message.edit_text("✅ Отчёт сохранён. Спасибо!", reply_markup=None)
    await callback.answer()


@router.message(SpecialistFlow.awaiting_note)
async def msg_note(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    note = message.text.strip()[:200]
    await _save_completed(data, note=note)
    await state.clear()
    await message.answer("✅ Отчёт сохранён. Спасибо!")


# ── Internal helper ────────────────────────────────────────────────────────────

async def _save_completed(fsm_data: dict, note: str | None) -> None:
    booking_id   = fsm_data["pv_booking_id"]
    duration     = fsm_data["pv_duration"]
    type_of_work = fsm_data["pv_type"]
    await db.create_post_visit(
        booking_id=booking_id,
        status="completed",
        duration_minutes=duration,
        type_of_work=type_of_work,
        note_short=note,
    )
    await sync_after_post_visit(booking_id)
    logger.info(
        "Post-visit completed: booking_id=%s type=%s duration=%s",
        booking_id, type_of_work, duration,
    )
