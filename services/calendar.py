"""
Google Calendar integration via Service Account.

Specialists are defined in SPECIALISTS dict — add/remove as needed.
Each entry:
  calendar_id  — Google Calendar ID (usually specialist@domain.com)
  language     — preferred language code
  specialization — short description shown to user
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ── Specialist registry ───────────────────────────────────────────────────────
# Fill in real calendar IDs before deploying.
SPECIALISTS: dict[str, dict] = {
    "sp_01": {
        "calendar_id": "specialist1@example.com",
        "language": "UA",
        "specialization": "Психолог / Психотерапевт",
    },
    "sp_02": {
        "calendar_id": "specialist2@example.com",
        "language": "RU",
        "specialization": "Кризисный консультант",
    },
    "sp_03": {
        "calendar_id": "specialist3@example.com",
        "language": "CZ",
        "specialization": "Psycholog / IKP",
    },
}

SLOT_DURATION = timedelta(minutes=60)   # booked in calendar
SLOT_DISPLAY  = 45                      # shown to user (minutes)
LOOK_AHEAD_DAYS = 7                     # search window
TOP_SLOTS = 3


class Slot(NamedTuple):
    specialist_id: str
    start: datetime
    end: datetime           # start + 60 min
    display_end: datetime   # start + 45 min (shown to user)

    def label(self, lang: str = "EN") -> str:
        weekdays = {
            "UA": ["Пн","Вт","Ср","Чт","Пт","Сб","Нд"],
            "RU": ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"],
            "CZ": ["Po","Út","St","Čt","Pá","So","Ne"],
            "EN": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        }.get(lang, ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        wd = weekdays[self.start.weekday()]
        return (
            f"{wd} {self.start.strftime('%d.%m')}  "
            f"{self.start.strftime('%H:%M')}–{self.display_end.strftime('%H:%M')}"
        )


def _build_service():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var not set")
    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _working_hours(dt: datetime) -> bool:
    """Mon–Fri 09:00–18:00 Prague time (UTC+1/+2 — simplified to UTC+1)."""
    local = dt + timedelta(hours=1)
    return local.weekday() < 5 and 9 <= local.hour < 18


async def get_free_slots(lang: str = "EN") -> list[Slot]:
    """
    Fetch free/busy for all specialists and return top-3 nearest slots.
    Runs synchronously inside thread pool — fine for MVP load.
    """
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, _sync_get_slots, lang)


def _sync_get_slots(lang: str) -> list[Slot]:
    try:
        service = _build_service()
    except Exception as exc:
        logger.error("Calendar service init failed: %s", exc)
        return []

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    time_max = now + timedelta(days=LOOK_AHEAD_DAYS)

    items = [
        {"id": sp["calendar_id"]}
        for sp in SPECIALISTS.values()
    ]
    body = {
        "timeMin": now.isoformat(),
        "timeMax": time_max.isoformat(),
        "timeZone": "UTC",
        "items": items,
    }

    try:
        result = service.freebusy().query(body=body).execute()
    except HttpError as exc:
        logger.error("freebusy query failed: %s", exc)
        return []

    all_slots: list[Slot] = []

    for sp_id, sp_meta in SPECIALISTS.items():
        cal_id = sp_meta["calendar_id"]
        busy_periods = result.get("calendars", {}).get(cal_id, {}).get("busy", [])
        busy_ranges = [
            (
                datetime.fromisoformat(b["start"]).replace(tzinfo=timezone.utc),
                datetime.fromisoformat(b["end"]).replace(tzinfo=timezone.utc),
            )
            for b in busy_periods
        ]

        # Walk through time in 60-min steps
        cursor = now
        while cursor < time_max:
            slot_end = cursor + SLOT_DURATION
            if _working_hours(cursor) and not any(
                b_start < slot_end and b_end > cursor
                for b_start, b_end in busy_ranges
            ):
                all_slots.append(Slot(
                    specialist_id=sp_id,
                    start=cursor,
                    end=slot_end,
                    display_end=cursor + timedelta(minutes=SLOT_DISPLAY),
                ))
            cursor += SLOT_DURATION

    all_slots.sort(key=lambda s: s.start)
    return all_slots[:TOP_SLOTS]


def create_calendar_event(
    specialist_id: str,
    user_name: str,
    start: datetime,
    end: datetime,
) -> str | None:
    """Create a 60-min event and return its Google event ID."""
    try:
        service = _build_service()
        sp = SPECIALISTS[specialist_id]
        event = {
            "summary": f"DUMKA — {user_name}",
            "description": "Сессия 45 мин + 15 мин буфер. Забронировано через бот.",
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end":   {"dateTime": end.isoformat(),   "timeZone": "UTC"},
        }
        created = (
            service.events()
            .insert(calendarId=sp["calendar_id"], body=event)
            .execute()
        )
        logger.info("Calendar event created: %s", created.get("id"))
        return created.get("id")
    except Exception as exc:
        logger.error("Failed to create calendar event: %s", exc)
        return None
