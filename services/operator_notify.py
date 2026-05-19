"""
Telegram notifications to operators when a client requests a callback.
"""

import html
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

logger = logging.getLogger(__name__)
PRAGUE_TZ = ZoneInfo("Europe/Prague")

_CAT_DISPLAY = {
    "cat_consult": "Психолог",
    "cat_ikp": "ИКП",
    "cat_crisis": "Кризис",
    "free_text": "Описание ситуации",
}

_CM_DISPLAY = {
    "phone": "Телефон",
    "telegram": "Telegram",
}


def _build_message(data: dict, user_id: int, username: str | None) -> str:
    def esc(v) -> str:
        return html.escape(str(v)) if v else "не указано"

    name = esc(data.get("name"))
    age_years = data.get("age_years")
    age_cat = data.get("age_cat", "")
    age_display = esc(age_years if age_years else age_cat)
    email = esc(data.get("email"))
    phone = esc(data.get("phone"))

    raw_cat = data.get("triage_category", "")
    category = html.escape(
        _CAT_DISPLAY.get(raw_cat, raw_cat) if raw_cat else "не указано"
    )

    raw_cm = data.get("contact_method", "")
    contact_method = html.escape(
        _CM_DISPLAY.get(raw_cm, raw_cm) if raw_cm else "не указано"
    )

    description = esc(data.get("triage_description"))
    tg_user = f"@{html.escape(username)}" if username else "не указан"
    now_str = datetime.now(PRAGUE_TZ).strftime("%d.%m.%Y %H:%M")

    return (
        "🔔 <b>Новая заявка — «Перезвоните мне»</b>\n\n"
        f"👤 Клиент: {name}\n"
        f"🎂 Возраст: {age_display}\n"
        f"📧 Email: {email}\n"
        f"📱 Телефон: {phone}\n"
        f"🗂 Категория: {category}\n"
        f"💬 Формат: {contact_method}\n"
        f"📝 Описание: {description}\n\n"
        f"🔗 Telegram: {tg_user}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"🕐 Время заявки: {now_str}\n\n"
        "⚡️ Пожалуйста, свяжитесь с клиентом в ближайшее время."
    )


async def notify_operator(
    bot: Bot,
    operator_ids: int | list[int],
    data: dict,
    user_id: int,
    username: str | None,
) -> None:
    """Send callback-request notification to one or several operators."""
    if isinstance(operator_ids, int):
        operator_ids = [operator_ids]

    text = _build_message(data, user_id, username)

    for oid in operator_ids:
        try:
            await bot.send_message(oid, text, parse_mode="HTML")
            logger.info("Operator %s notified (callback from user_id=%s)", oid, user_id)
        except TelegramForbiddenError:
            logger.warning(
                "Operator %s hasn't started the bot — callback not delivered", oid
            )
            from config import ADMIN_IDS

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ Не удалось уведомить оператора {oid}: бот не запущен оператором.",
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.error("Failed to notify operator %s: %s", oid, exc)
