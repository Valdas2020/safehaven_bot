"""
SafeHaven — Mental Health Support Telegram Bot
Webhook mode via FastAPI + aiogram 3.x
"""
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
from config import BOT_TOKEN, HOST, PORT, WEBHOOK_PATH, WEBHOOK_SECRET, WEBHOOK_URL
from handlers import admin, booking, fallback, gdpr, intake, start, triage
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
dp.include_router(start.router)
dp.include_router(gdpr.router)
dp.include_router(intake.router)
dp.include_router(triage.router)
dp.include_router(booking.router)
dp.include_router(fallback.router)  # must be last


# ── FastAPI app ───────────────────────────────────────────────────────────────

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
