"""
Google Sheets synchronization via gspread (lightweight alternative to googleapiclient).

Uses the same Service Account as Google Calendar.
Requires GOOGLE_SHEETS_ID in env and Editor access granted to the service account.

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

import gspread
from google.oauth2 import service_account

from config import GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEETS_ID
import database as db

logger = logging.getLogger(__name__)
PRAGUE_TZ = ZoneInfo("Europe/Prague")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_SESSIONS = "Sessions_Log"
SHEET_MONTHLY  = "Monthly_Summary"
SHEET_INTAKE   = "Intake_Stats"

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


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet, title: str) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=20)


# ── Row builders ───────────────────────────────────────────────────────────────

def _build_sessions_rows(records) -> list[list]:
    header = ["Date", "Weekday", "Time", "Specialist", "Type_of_Work",
              "Duration_min", "Status", "Client_Hash", "Note"]
    rows = [header]
    for r in records:
        local = r["start_time"].astimezone(PRAGUE_TZ)
        rows.append([
            local.strftime("%d.%m.%Y"),
            local.strftime("%A"),
            local.strftime("%H:%M"),
            r["specialist_id"],
            r["type_of_work"] or "",
            r["duration_minutes"] or 45,
            r["status"],
            _client_hash(r["user_id"]),
            r["note_short"] or "",
        ])
    return rows


def _build_monthly_rows(records) -> list[list]:
    header = ["Year", "Month", "Specialist", "Type_of_Work", "Total_min", "Total_hrs"]
    rows = [header]
    for r in records:
        rows.append([
            r["year"],
            r["month"],
            r["specialist_id"],
            r["type_of_work"] or "",
            r["total_minutes"],
            round(r["total_minutes"] / 60, 2),
        ])
    return rows


def _build_intake_rows(records) -> list[list]:
    header = ["Date", "Language", "Age_Group", "Triage_Level", "Category"]
    rows = [header]
    for r in records:
        date_str = r["date"].strftime("%d.%m.%Y") if r["date"] else ""
        rows.append([
            date_str,
            r["language"] or "",
            r["age_cat"] or "",
            r["triage_level"] or "",
            r["category"] or "",
        ])
    return rows


# ── Sync logic ─────────────────────────────────────────────────────────────────

def _write_all_sync(sessions_rows, monthly_rows, intake_rows) -> None:
    if not GOOGLE_SHEETS_ID:
        logger.warning("GOOGLE_SHEETS_ID not set — skipping Google Sheets sync")
        return
    try:
        gc = _get_client()
        sh = gc.open_by_key(GOOGLE_SHEETS_ID)

        for tab, rows in [
            (SHEET_SESSIONS, sessions_rows),
            (SHEET_MONTHLY,  monthly_rows),
            (SHEET_INTAKE,   intake_rows),
        ]:
            ws = _get_or_create_sheet(sh, tab)
            ws.clear()
            if rows:
                ws.update(rows, "A1")

        logger.info("Google Sheets sync complete (%d session rows)", len(sessions_rows) - 1)
    except Exception as exc:
        logger.error("Google Sheets sync failed: %s", exc)


async def _async_write_all(sessions_rows, monthly_rows, intake_rows) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write_all_sync, sessions_rows, monthly_rows, intake_rows)


async def sync_after_post_visit(booking_id: int) -> None:
    sessions = await db.get_sessions_for_sheet()
    monthly  = await db.get_monthly_summary()
    intake   = await db.get_intake_stats()

    sessions_rows = _build_sessions_rows(sessions)
    monthly_rows  = _build_monthly_rows(monthly)
    intake_rows   = _build_intake_rows(intake)

    asyncio.create_task(_async_write_all(sessions_rows, monthly_rows, intake_rows))
    logger.info("Sheets sync task queued for booking_id=%s", booking_id)
