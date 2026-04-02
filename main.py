"""
SafeHaven — Mental Health Support Telegram Bot
Webhook mode via FastAPI + aiogram 3.x
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
import uvicorn
from fastapi import FastAPI, Request, Response

import database as db
from config import BOT_TOKEN, HOST, PORT, SPECIALIST_TG_IDS, WEBHOOK_PATH, WEBHOOK_SECRET, WEBHOOK_URL
from handlers import admin, booking, fallback, gdpr, intake, post_visit, privacy, start, triage
from middlewares.logging_mw import LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Bot & Dispatcher ──────────────────────────────────────────────────────────

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())
dp.update.outer_middleware(LoggingMiddleware())
dp.include_router(admin.router)
dp.include_router(privacy.router)
dp.include_router(post_visit.router)
dp.include_router(start.router)
dp.include_router(gdpr.router)
dp.include_router(intake.router)
dp.include_router(triage.router)
dp.include_router(booking.router)
dp.include_router(fallback.router)  # must be last


# ── FastAPI app ───────────────────────────────────────────────────────────────

async def _reschedule_pending_notifications() -> None:
    """On startup: re-create asyncio tasks for all bookings that still need a post-visit prompt."""
    from services.calendar import SPECIALISTS
    bookings = await db.get_pending_bookings_for_notification()
    count = 0
    for b in bookings:
        sp_tg_id = SPECIALIST_TG_IDS.get(b["specialist_id"])
        if sp_tg_id:
            sp_name = SPECIALISTS.get(b["specialist_id"], {}).get("name", b["specialist_id"])
            asyncio.create_task(
                post_visit.schedule_specialist_notification(
                    bot, sp_tg_id, b["id"], b["start_time"], b["end_time"], sp_name
                )
            )
            count += 1
    logger.info("Rescheduled %d pending post-visit notification(s)", count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    logger.info("Webhook set: %s", WEBHOOK_URL)
    await _reschedule_pending_notifications()
    yield
    # NOTE: do NOT delete_webhook on shutdown — Render rolling restarts would
    # clear the webhook before the new instance registers it.
    await db.close_db()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> Response:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return Response()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
