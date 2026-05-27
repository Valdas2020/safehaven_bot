"""
GDPR data retention cleanup.

Deletes users who have given consent but have been inactive for >= 30 days,
matching the Privacy Policy retention commitment.
"""

import logging

from aiogram import Bot

import database as db
from services.calendar import delete_user_calendar_events
from services.reporting import delete_user_from_sheets

logger = logging.getLogger(__name__)

INACTIVE_DAYS = 30


async def delete_inactive_users(bot: Bot) -> None:
    """Find and delete all users inactive for >= INACTIVE_DAYS days."""
    from config import CLEANUP_ENABLED

    if not CLEANUP_ENABLED:
        logger.info("Cleanup: skipped (CLEANUP_ENABLED=false)")
        return

    inactive = await db.get_inactive_users(days=INACTIVE_DAYS)
    if not inactive:
        logger.info("Cleanup: no inactive users found (>= %d days)", INACTIVE_DAYS)
        return

    logger.info("Cleanup: %d inactive user(s) to delete", len(inactive))

    for row in inactive:
        telegram_id: int = row["telegram_id"]
        try:
            bookings = await db.get_user_bookings_with_calendar(telegram_id)
            if bookings:
                await delete_user_calendar_events(bookings, telegram_id, reason="auto_cleanup")
            await delete_user_from_sheets(telegram_id)
            await db.delete_user_data(telegram_id)
            logger.info(
                "Auto-deleted inactive user %s after %d days of inactivity",
                telegram_id,
                INACTIVE_DAYS,
            )
        except Exception as exc:
            logger.error("Cleanup failed for user %s: %s", telegram_id, exc)
