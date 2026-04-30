"""
Google Calendar integration via Service Account.

IMPORTANT — each specialist must share their Google Calendar with:
    dumka-bot@dumka-bot.iam.gserviceaccount.com
    Access level: "Make changes and manage sharing"

Matching logic:
  - Filter by age_group (child / adult) from user intake
  - Filter by triage_level (urgent → only specialists who handle urgent)
  - Round-robin across matched specialists
  - Return top 3 earliest free slots
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
PRAGUE_TZ = ZoneInfo("Europe/Prague")

# ── Specialist registry ───────────────────────────────────────────────────────
# Add/remove specialists here. calendar_id = Google Calendar email address.
SPECIALISTS: dict[str, dict] = {
    "psych_adult_1": {
        "calendar_id": "ralph.drogheda@gmail.com",
        "email": "ralph.drogheda@gmail.com",
        "name": "Psychologist (Adults)",
        "name_i18n": {
            "UA": "Психолог (дорослі)",
            "RU": "Психолог (взрослые)",
            "CZ": "Psycholog (dospělí)",
            "EN": "Psychologist (Adults)",
        },
        "type": "psychologist",
        "slot_minutes": 60,     # 45 min session + 15 min buffer
        "display_minutes": 45,
        "age_group": ["adult"],
        "triage_level": ["normal"],
        "lang": ["EN", "CZ", "UA", "RU"],
    },
    "psych_adult_crisis": {
        "calendar_id": "timbookedtwo2@gmail.com",
        "email": "timbookedtwo2@gmail.com",
        "name": "Psychologist (Adults — Crisis)",
        "name_i18n": {
            "UA": "Психолог — Кризис (дорослі)",
            "RU": "Психолог — Кризис (взрослые)",
            "CZ": "Psycholog — Krize (dospělí)",
            "EN": "Psychologist — Crisis (Adults)",
        },
        "type": "psychologist",
        "slot_minutes": 60,     # 45 min session + 15 min buffer
        "display_minutes": 45,
        "age_group": ["adult"],
        "triage_level": ["normal", "urgent"],
        "lang": ["EN", "CZ", "UA", "RU"],
    },
    "psych_children": {
        "calendar_id": "yurkevichirina@gmail.com",
        "email": "yurkevichirina@gmail.com",
        "name": "Psychologist (Children)",
        "name_i18n": {
            "UA": "Психолог (діти)",
            "RU": "Психолог (дети)",
            "CZ": "Psycholog (děti)",
            "EN": "Psychologist (Children)",
        },
        "type": "psychologist",
        "slot_minutes": 60,     # 45 min session + 15 min buffer
        "display_minutes": 45,
        "age_group": ["child"],
        "triage_level": ["normal"],
        "lang": ["EN", "CZ", "UA", "RU"],
    },
    # IKP specialists: add here with slot_minutes=45, display_minutes=30
}

# Fallback defaults (each specialist overrides via slot_minutes / display_minutes)
SLOT_DURATION  = timedelta(minutes=60)
SLOT_DISPLAY   = 45
LOOK_AHEAD_DAYS = 7
TOP_SLOTS = 4    # 2 regular + 2 crisis
MIN_LEAD_HOURS = 4  # first slot no sooner than 4h from now
WORK_START = 9   # first slot starts 09:00 Prague
WORK_END   = 21  # last slot starts 20:00, ends 21:00 (displayed as 20:00–20:45)
AM_CUTOFF  = 13  # slots before 13:00 Prague are "AM"


# ── Data types ────────────────────────────────────────────────────────────────

class Slot(NamedTuple):
    specialist_id: str
    start: datetime        # UTC
    end: datetime          # start + 60 min
    display_end: datetime  # start + 45 min (shown to user)

    def label(self, lang: str = "EN") -> str:
        weekdays = {
            "UA": ["Пн","Вт","Ср","Чт","Пт","Сб","Нд"],
            "RU": ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"],
            "CZ": ["Po","Út","St","Čt","Pá","So","Ne"],
            "EN": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        }.get(lang, ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        local = self.start.astimezone(PRAGUE_TZ)
        local_end = self.display_end.astimezone(PRAGUE_TZ)
        wd = weekdays[local.weekday()]
        return f"{wd} {local.strftime('%d.%m')}  {local.strftime('%H:%M')}–{local_end.strftime('%H:%M')}"


# ── Matching ──────────────────────────────────────────────────────────────────

def match_specialists(age_cat: str, triage_level: str) -> list[str]:
    """Return specialist IDs that match user's age group and triage level."""
    matched = [
        sp_id for sp_id, sp in SPECIALISTS.items()
        if age_cat in sp["age_group"] and triage_level in sp["triage_level"]
    ]
    return matched


# ── Calendar helpers ──────────────────────────────────────────────────────────

_calendar_service = None

def _build_service():
    global _calendar_service
    if _calendar_service is not None:
        return _calendar_service
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var not set")
    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    _calendar_service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return _calendar_service


def _is_working_hour(dt: datetime) -> bool:
    """True if dt falls within 09:00–20:00 Europe/Prague (7 days a week)."""
    local = dt.astimezone(PRAGUE_TZ)
    return WORK_START <= local.hour < WORK_END


# ── Main public API ───────────────────────────────────────────────────────────

async def get_free_slots(
    lang: str = "EN",
    age_cat: str = "adult",
    triage_level: str = "normal",
) -> list[Slot]:
    """Async wrapper — runs sync calendar logic in thread pool."""
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(
        None, _sync_get_slots, lang, age_cat, triage_level
    )


def _sync_get_slots(lang: str, age_cat: str, triage_level: str) -> list[Slot]:
    matched_ids = match_specialists(age_cat, triage_level)
    if not matched_ids:
        logger.warning("No specialists match age_cat=%s triage=%s", age_cat, triage_level)
        return []

    try:
        service = _build_service()
    except Exception as exc:
        logger.error("Calendar service init failed: %s", exc)
        return []

    now      = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    time_max = now + timedelta(days=LOOK_AHEAD_DAYS)

    # First slot must be at least MIN_LEAD_HOURS from now; round up to full hour
    min_start = now + timedelta(hours=MIN_LEAD_HOURS)
    if min_start.minute != 0:
        cursor = min_start.replace(minute=0, microsecond=0) + timedelta(hours=1)
    else:
        cursor = min_start

    # Fetch free/busy for matched specialists only
    items = [{"id": SPECIALISTS[sp_id]["calendar_id"]} for sp_id in matched_ids]
    try:
        result = service.freebusy().query(body={
            "timeMin": now.isoformat(),
            "timeMax": time_max.isoformat(),
            "timeZone": "UTC",
            "items": items,
        }).execute()
    except HttpError as exc:
        logger.error("freebusy query failed: %s", exc)
        return []

    # Build busy ranges per specialist
    busy: dict[str, list[tuple]] = {}
    for sp_id in matched_ids:
        cal_id = SPECIALISTS[sp_id]["calendar_id"]
        periods = result.get("calendars", {}).get(cal_id, {}).get("busy", [])
        busy[sp_id] = [
            (
                datetime.fromisoformat(b["start"]).replace(tzinfo=timezone.utc),
                datetime.fromisoformat(b["end"]).replace(tzinfo=timezone.utc),
            )
            for b in periods
        ]

    # Collect all free slots per specialist (each uses its own slot duration)
    slots_per_sp: dict[str, list[Slot]] = {}
    for sp_id in matched_ids:
        sp = SPECIALISTS[sp_id]
        dur     = timedelta(minutes=sp.get("slot_minutes",   SLOT_DURATION.seconds // 60))
        display = sp.get("display_minutes", SLOT_DISPLAY)
        sp_cursor = cursor
        sp_slots: list[Slot] = []
        while sp_cursor < time_max:
            if _is_working_hour(sp_cursor):
                slot_end = sp_cursor + dur
                if not any(b_start < slot_end and b_end > sp_cursor for b_start, b_end in busy[sp_id]):
                    sp_slots.append(Slot(
                        specialist_id=sp_id,
                        start=sp_cursor,
                        end=slot_end,
                        display_end=sp_cursor + timedelta(minutes=display),
                    ))
            sp_cursor += dur
        slots_per_sp[sp_id] = sp_slots

    # For each specialist pick 1 AM slot (< 13:00 Prague) + 1 PM slot (≥ 13:00 Prague)
    def _pick_am_pm(slots: list[Slot]) -> list[Slot]:
        am = next((s for s in slots if s.start.astimezone(PRAGUE_TZ).hour < AM_CUTOFF), None)
        pm = next((s for s in slots if s.start.astimezone(PRAGUE_TZ).hour >= AM_CUTOFF), None)
        return [s for s in [am, pm] if s is not None]

    # Separate normal vs urgent-capable specialists, pick AM/PM from each group
    normal_ids  = [sp for sp in matched_ids if "normal"  in SPECIALISTS[sp]["triage_level"]
                                            and "urgent" not in SPECIALISTS[sp]["triage_level"]]
    crisis_ids  = [sp for sp in matched_ids if "urgent"  in SPECIALISTS[sp]["triage_level"]]

    selected: list[Slot] = []
    for sp_id in normal_ids:
        selected.extend(_pick_am_pm(slots_per_sp[sp_id]))
    for sp_id in crisis_ids:
        selected.extend(_pick_am_pm(slots_per_sp[sp_id]))

    selected.sort(key=lambda s: s.start)
    return selected[:TOP_SLOTS]


def create_calendar_event(
    specialist_id: str,
    telegram_id: int,
    start: datetime,
    end: datetime,
    client_name: str = "",
    client_phone: str = "",
    client_email: str = "",
    contact_method: str = "",
) -> str | None:
    """
    Create a 60-min event in specialist's calendar.
    Returns Google event ID or None on failure.
    NOTE: specialist must grant 'Make changes to events' to service account.
    """
    try:
        service = _build_service()
        sp = SPECIALISTS[specialist_id]
        contact_lines = []
        if client_phone:
            cm_label = f" ({contact_method})" if contact_method else ""
            contact_lines.append(f"Phone: {client_phone}{cm_label}")
        elif contact_method:
            contact_lines.append(f"Contact via: {contact_method}")
        if client_email:
            contact_lines.append(f"Email: {client_email}")
        contact_lines.append(f"Telegram ID: {telegram_id}")
        contact_str = "\n".join(contact_lines)
        session_min  = sp.get("display_minutes", SLOT_DISPLAY)
        buffer_min   = sp.get("slot_minutes", SLOT_DURATION.seconds // 60) - session_min
        event = {
            "summary": f"SafeHaven — {client_name}" if client_name else "SafeHaven Session",
            "description": (
                f"Client session ({session_min} min) + {buffer_min} min buffer. "
                f"Booked via SafeHaven bot.\n"
                f"Client: {client_name}\n"
                f"{contact_str}"
            ),
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end":   {"dateTime": end.isoformat(),   "timeZone": "UTC"},
        }
        created = (
            service.events()
            .insert(calendarId=sp["calendar_id"], body=event)
            .execute()
        )
        logger.info("Event created: %s specialist=%s", created.get("id"), specialist_id)
        return created.get("id")
    except Exception as exc:
        logger.error("Failed to create event for %s: %s", specialist_id, exc)
        return None
