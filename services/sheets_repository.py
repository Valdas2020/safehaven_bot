"""
Google Sheets repository — reads specialist schedules from the spreadsheet.

Auth: Service Account (GOOGLE_SERVICE_ACCOUNT_JSON).
Cache: in-memory, 60-second TTL.
"""

import json
import logging
import re
import time as _time_mod
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import gspread
from config import GOOGLE_SERVICE_ACCOUNT_JSON
from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.errors import HttpError
from models import BookingWindow

logger = logging.getLogger(__name__)

PRAGUE_TZ = ZoneInfo("Europe/Prague")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CACHE_TTL = 60  # seconds

# ── Location lookup ───────────────────────────────────────────────────────────

_OFFLINE_LOCATIONS: list[tuple[str, str]] = [
    ("belgická", "Belgická 539/11, Komunitní centrum AMIGA"),
    (
        "dům radost",
        "Dům RADOST, nám. Winstona Churchilla 1800/2, 4. patro, kancelář 306",
    ),
    ("winston", "Dům RADOST, nám. Winstona Churchilla 1800/2, 4. patro, kancelář 306"),
    ("rajské zahrady", "U Rajské zahrady 26, 130 00 Praha 3-Žižkov"),
    ("žižkov", "U Rajské zahrady 26, 130 00 Praha 3-Žižkov"),
]

_SLOT_RE = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")

# ── Singletons ────────────────────────────────────────────────────────────────

_gspread_client: gspread.Client | None = None
_cache: dict[str, tuple[list, float]] = {}


def _build_gspread_client() -> gspread.Client:
    global _gspread_client
    if _gspread_client is not None:
        return _gspread_client
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var not set")
    creds = SACredentials.from_service_account_info(
        json.loads(GOOGLE_SERVICE_ACCOUNT_JSON), scopes=SCOPES
    )
    _gspread_client = gspread.authorize(creds)
    return _gspread_client


# ── Parsing helpers ───────────────────────────────────────────────────────────


def _parse_date(raw: str) -> Optional[date]:
    raw = raw.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    logger.warning("Cannot parse date: %r — skipping row", raw)
    return None


def _parse_slot(raw: str) -> Optional[tuple[time, time]]:
    cleaned = re.sub(r"\s+", "", raw)
    if not cleaned or cleaned in ("-", "volno", "off"):
        return None
    m = _SLOT_RE.match(cleaned)
    if not m:
        logger.warning("Cannot parse Otevírací doba: %r — skipping row", raw)
        return None
    h1, m1, h2, m2 = map(int, m.groups())
    try:
        return time(h1, m1), time(h2, m2)
    except ValueError:
        logger.warning("Invalid time values in: %r — skipping row", raw)
        return None


def _resolve_location(raw: str) -> tuple[bool, Optional[str]]:
    stripped = raw.strip()
    if not stripped or stripped.lower() in ("-", "volno", "off"):
        return True, None
    lower = stripped.lower()
    if "online" in lower:
        return True, None
    for keyword, full_address in _OFFLINE_LOCATIONS:
        if keyword in lower:
            return False, full_address
    logger.warning("Unknown Místo konání value: %r — treating as online", stripped)
    return True, None


# ── Public API ────────────────────────────────────────────────────────────────


def load_rows(spreadsheet_id: str, sheet_tab: str) -> list[dict]:
    """Load all rows from the sheet, with 60-second TTL cache."""
    cache_key = f"{spreadsheet_id}:{sheet_tab}"
    now = _time_mod.monotonic()
    if cache_key in _cache:
        rows, ts = _cache[cache_key]
        if now - ts < CACHE_TTL:
            return rows
    client = _build_gspread_client()
    sh = client.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_tab)
    rows = ws.get_all_records()
    _cache[cache_key] = (rows, now)
    logger.info(
        "Loaded %d rows from sheet %s tab %s", len(rows), spreadsheet_id, sheet_tab
    )
    return rows


def get_specialist_slots(
    name: str,
    date_from: date,
    date_to: date,
    spreadsheet_id: str,
    sheet_tab: str,
) -> list[BookingWindow]:
    """Return all BookingWindows for a specialist in [date_from, date_to]."""
    rows = load_rows(spreadsheet_id, sheet_tab)
    result: list[BookingWindow] = []

    for row in rows:
        sp_name = str(row.get("Jméno a příjmení", "")).strip()
        if sp_name != name.strip():
            continue

        raw_date = str(row.get("Data", "")).strip()
        d = _parse_date(raw_date)
        if d is None or not (date_from <= d <= date_to):
            continue

        raw_slot = str(row.get("Otevírací doba", "")).strip()
        parsed = _parse_slot(raw_slot)
        if parsed is None:
            continue
        start_t, end_t = parsed

        # display_end = start + 45 min
        display_end_dt = datetime.combine(d, start_t) + timedelta(minutes=45)
        display_end_t = display_end_dt.time()

        raw_loc = str(row.get("Místo konání", "")).strip()
        is_online, address = _resolve_location(raw_loc)

        category = str(row.get("Kategorie", "")).strip()

        sp_email = str(row.get("E-mailová adresa", "")).strip()

        # Calendar ID for Google Calendar API — prefer dedicated column, fallback to email
        cal_id = str(row.get("ID kalendáře", "")).strip()
        if not cal_id:
            cal_id = sp_email
            if cal_id:
                logger.info(
                    "Using E-mailová adresa as calendar_id fallback for %s: %s",
                    name,
                    cal_id,
                )

        result.append(
            BookingWindow(
                date=d,
                start=start_t,
                end=end_t,
                display_end=display_end_t,
                is_online=is_online,
                address=address,
                category=category,
                calendar_id=cal_id,
                specialist_name=sp_name,
                specialist_email=sp_email,
            )
        )

    result.sort(key=lambda w: (w.date, w.start))
    return result


async def get_available_windows(
    specialist_name: str,
    date_from: date,
    date_to: date,
    spreadsheet_id: str,
    sheet_tab: str,
    limit: int = 3,
) -> list[BookingWindow]:
    """Return up to `limit` available (not busy) BookingWindows."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(
        None,
        _sync_get_available,
        specialist_name,
        date_from,
        date_to,
        spreadsheet_id,
        sheet_tab,
        limit,
    )


def _sync_get_available(
    specialist_name: str,
    date_from: date,
    date_to: date,
    spreadsheet_id: str,
    sheet_tab: str,
    limit: int,
) -> list[BookingWindow]:
    windows = get_specialist_slots(
        specialist_name, date_from, date_to, spreadsheet_id, sheet_tab
    )
    if not windows:
        return []

    # Fetch busy periods for all relevant calendars in one freebusy call
    from services.calendar import _build_service  # reuse OAuth2 service

    cal_ids = list({w.calendar_id for w in windows if w.calendar_id})
    time_min = datetime.combine(date_from, time.min).replace(tzinfo=PRAGUE_TZ)
    time_max = datetime.combine(date_to, time(23, 59, 59)).replace(tzinfo=PRAGUE_TZ)

    busy: dict[str, list[tuple[datetime, datetime]]] = {c: [] for c in cal_ids}

    try:
        service = _build_service()
        result = (
            service.freebusy()
            .query(
                body={
                    "timeMin": time_min.isoformat(),
                    "timeMax": time_max.isoformat(),
                    "timeZone": "UTC",
                    "items": [{"id": c} for c in cal_ids],
                }
            )
            .execute()
        )
        for cal_id in cal_ids:
            periods = result.get("calendars", {}).get(cal_id, {}).get("busy", [])
            busy[cal_id] = [
                (
                    datetime.fromisoformat(b["start"]).replace(tzinfo=timezone.utc),
                    datetime.fromisoformat(b["end"]).replace(tzinfo=timezone.utc),
                )
                for b in periods
            ]
    except HttpError as exc:
        logger.error(
            "freebusy query failed: %s — returning all windows unfiltered", exc
        )
    except Exception as exc:
        logger.error(
            "Calendar service error: %s — returning all windows unfiltered", exc
        )

    available: list[BookingWindow] = []
    for w in windows:
        if not w.calendar_id:
            continue
        start_utc = (
            datetime.combine(w.date, w.start)
            .replace(tzinfo=PRAGUE_TZ)
            .astimezone(timezone.utc)
        )
        end_utc = (
            datetime.combine(w.date, w.end)
            .replace(tzinfo=PRAGUE_TZ)
            .astimezone(timezone.utc)
        )
        ranges = busy.get(w.calendar_id, [])
        if any(b_start < end_utc and b_end > start_utc for b_start, b_end in ranges):
            continue
        available.append(w)
        if len(available) >= limit:
            break

    return available
