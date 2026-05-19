"""
Google Sheets synchronization via gspread (lightweight alternative to googleapiclient).

Uses the same Service Account as Google Calendar.
Requires GOOGLE_SHEETS_ID in env and Editor access granted to the service account.

NOTE: GOOGLE_SHEETS_ID is the REPORTING sheet (Sessions_Log, Monthly_Summary, Intake_Stats).
      SPREADSHEET_ID is the SCHEDULE sheet (specialist availability rows) — these are different.

Three tabs:
  - Sessions_Log     : one row per post-visit entry
  - Monthly_Summary  : aggregated hours per specialist per type of work
  - Intake_Stats     : anonymized client intake data (no names, no Telegram IDs)
"""

import asyncio
import hashlib
import json
import logging
from zoneinfo import ZoneInfo

import database as db
import gspread
from config import GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEETS_ID
from google.oauth2 import service_account

logger = logging.getLogger(__name__)
PRAGUE_TZ = ZoneInfo("Europe/Prague")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_SESSIONS = "Sessions_Log"
SHEET_MONTHLY = "Monthly_Summary"
SHEET_INTAKE = "Intake_Stats"

_gc: gspread.Client | None = None


# ── Privacy helper ─────────────────────────────────────────────────────────────


def _client_hash(user_id: int) -> str:
    return "C_" + hashlib.sha256(str(user_id).encode()).hexdigest()[:10].upper()


# ── gspread client (cached singleton) ─────────────────────────────────────────


def _get_client() -> gspread.Client:
    global _gc
    if _gc is not None:
        return _gc
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    _gc = gspread.authorize(creds)
    return _gc


def _get_or_create_sheet(
    spreadsheet: gspread.Spreadsheet, title: str
) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        logger.info("Tab '%s' not found — creating it", title)
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=20)


# ── Row builders ───────────────────────────────────────────────────────────────


def _build_sessions_rows(records) -> list[list]:
    header = [
        "Date",
        "Weekday",
        "Time",
        "Specialist",
        "Type_of_Work",
        "Duration_min",
        "Status",
        "Client_Hash",
        "Note",
    ]
    rows = [header]
    for r in records:
        local = r["start_time"].astimezone(PRAGUE_TZ)
        rows.append(
            [
                local.strftime("%d.%m.%Y"),
                local.strftime("%A"),
                local.strftime("%H:%M"),
                r["specialist_id"],
                r["type_of_work"] or "",
                r["duration_minutes"] or 45,
                r["status"],
                _client_hash(r["user_id"]),
                r["note_short"] or "",
            ]
        )
    return rows


def _build_monthly_rows(records) -> list[list]:
    header = ["Year", "Month", "Specialist", "Type_of_Work", "Total_min", "Total_hrs"]
    rows = [header]
    for r in records:
        rows.append(
            [
                r["year"],
                r["month"],
                r["specialist_id"],
                r["type_of_work"] or "",
                r["total_minutes"],
                round(r["total_minutes"] / 60, 2),
            ]
        )
    return rows


def _build_intake_rows(records) -> list[list]:
    header = ["Date", "Language", "Age_Group", "Triage_Level", "Category"]
    rows = [header]
    for r in records:
        date_str = r["date"].strftime("%d.%m.%Y") if r["date"] else ""
        rows.append(
            [
                date_str,
                r["language"] or "",
                r["age_cat"] or "",
                r["triage_level"] or "",
                r["category"] or "",
            ]
        )
    return rows


# ── Sync logic ─────────────────────────────────────────────────────────────────


def _write_all_sync(sessions_rows, monthly_rows, intake_rows) -> None:
    if not GOOGLE_SHEETS_ID:
        logger.warning(
            "GOOGLE_SHEETS_ID env var is not set — skipping Google Sheets sync. "
            "Set GOOGLE_SHEETS_ID to the reporting spreadsheet ID to enable sync."
        )
        return
    logger.info(
        "Sheets sync start: %d session rows, %d monthly rows, %d intake rows",
        len(sessions_rows) - 1,
        len(monthly_rows) - 1,
        len(intake_rows) - 1,
    )
    try:
        gc = _get_client()
        sh = gc.open_by_key(GOOGLE_SHEETS_ID)

        for tab, rows in [
            (SHEET_SESSIONS, sessions_rows),
            (SHEET_MONTHLY, monthly_rows),
            (SHEET_INTAKE, intake_rows),
        ]:
            ws = _get_or_create_sheet(sh, tab)
            ws.clear()
            if rows:
                ws.update(rows, "A1")
            logger.info("Sheets tab '%s' written: %d data rows", tab, len(rows) - 1)

        logger.info("Google Sheets sync complete")
    except Exception as exc:
        logger.error("Google Sheets sync FAILED: %s", exc, exc_info=True)
        raise


async def _async_write_all(sessions_rows, monthly_rows, intake_rows) -> None:
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None, _write_all_sync, sessions_rows, monthly_rows, intake_rows
        )
    except Exception as exc:
        logger.error("Sheets async write task failed: %s", exc)


async def sync_after_post_visit(booking_id: int) -> None:
    logger.info("sync_after_post_visit called for booking_id=%s", booking_id)

    sessions = await db.get_sessions_for_sheet()
    monthly = await db.get_monthly_summary()
    intake = await db.get_intake_stats()

    logger.info(
        "DB data fetched: %d sessions, %d monthly, %d intake",
        len(sessions),
        len(monthly),
        len(intake),
    )

    sessions_rows = _build_sessions_rows(sessions)
    monthly_rows = _build_monthly_rows(monthly)
    intake_rows = _build_intake_rows(intake)

    asyncio.create_task(_async_write_all(sessions_rows, monthly_rows, intake_rows))
    logger.info("Sheets sync task queued for booking_id=%s", booking_id)


# ── GDPR erasure — remove user rows from Sessions_Log ─────────────────────────


def _delete_user_rows_sync(telegram_id: int) -> None:
    """Remove all Sessions_Log rows matching this user's Client_Hash."""
    if not GOOGLE_SHEETS_ID:
        logger.warning(
            "GOOGLE_SHEETS_ID not set — cannot delete Sheets rows for user %s",
            telegram_id,
        )
        return

    client_hash = _client_hash(telegram_id)
    logger.info(
        "Deleting Sessions_Log rows for telegram_id=%s hash=%s",
        telegram_id,
        client_hash,
    )

    try:
        gc = _get_client()
        sh = gc.open_by_key(GOOGLE_SHEETS_ID)
        ws = _get_or_create_sheet(sh, SHEET_SESSIONS)

        all_values = ws.get_all_values()
        if not all_values:
            logger.info("Sessions_Log is empty — nothing to delete")
            return

        header = all_values[0]
        try:
            hash_col = header.index("Client_Hash")
        except ValueError:
            logger.warning(
                "Client_Hash column not found in Sessions_Log header — cannot delete rows"
            )
            return

        # Collect 0-based row indices (row 0 = header, data starts at 1)
        matching = [
            i
            for i, row in enumerate(all_values)
            if i > 0 and len(row) > hash_col and row[hash_col] == client_hash
        ]

        if not matching:
            logger.info("No Sessions_Log rows found for hash=%s", client_hash)
            return

        # Delete in reverse order to avoid row-index shifting
        requests = [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": ws.id,
                        "dimension": "ROWS",
                        "startIndex": row_idx,
                        "endIndex": row_idx + 1,
                    }
                }
            }
            for row_idx in sorted(matching, reverse=True)
        ]

        sh.batch_update({"requests": requests})
        logger.info(
            "Deleted %d Sessions_Log row(s) for telegram_id=%s hash=%s",
            len(requests),
            telegram_id,
            client_hash,
        )
    except Exception as exc:
        logger.error(
            "Failed to delete Sessions_Log rows for telegram_id=%s: %s",
            telegram_id,
            exc,
        )


async def delete_user_from_sheets(telegram_id: int) -> None:
    """Async wrapper for GDPR erasure from Google Sheets."""
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _delete_user_rows_sync, telegram_id)
    except Exception as exc:
        logger.error(
            "delete_user_from_sheets failed for telegram_id=%s: %s", telegram_id, exc
        )
