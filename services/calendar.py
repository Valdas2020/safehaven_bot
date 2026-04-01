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
        "calendar_id": "ralph.drogheda@gmail.com",          # ← must share with service account
        "email": "ralph.drogheda@gmail.com",                # ← booking notification address
        "name": "Psychologist (Adults)",
        "type": "psychologist",
        "age_group": ["adult"],
        "triage_level": ["normal"],
        "lang": ["EN", "CZ", "UA", "RU"],
    },
    "psych_adult_crisis": {
        "calendar_id": "timbookedtwo2@gmail.com",           # ← must share with service account
        "email": "timbookedtwo2@gmail.com",                 # ← booking notification address
        "name": "Psychologist (Adults — Crisis)",
        "type": "psychologist",
        "age_group": ["adult"],
        "triage_level": ["normal", "urgent"],
        "lang": ["EN", "CZ", "UA", "RU"],
    },
    "psych_children": {
        "calendar_id": "yurkevichirina@gmail.com",          # ← must share with service account
        "email": "yurkevichirina@gmail.com",                # ← booking notification address
        "name": "Psychologist (Children)",
        "type": "psychologist",
        "age_group": ["child"],
        "triage_level": ["normal"],
        "lang": ["EN", "CZ", "UA", "RU"],
    },
}

SLOT_DURATION  = timedelta(minutes=60)  # booked in calendar
SLOT_DISPLAY   = 45                     # minutes shown to user
LOOK_AHEAD_DAYS = 7
TOP_SLOTS = 3
WORK_START = 9   # 09:00 Prague
WORK_END   = 18  # 18:00 Prague


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

def _build_service():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var not set")
    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _is_working_hour(dt: datetime) -> bool:
    """True if dt falls within Mon–Fri 09:00–18:00 Europe/Prague."""
    local = dt.astimezone(PRAGUE_TZ)
    return local.weekday() < 5 and WORK_START <= local.hour < WORK_END


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

    # Round-robin slot generation across matched specialists
    # Walk in 60-min steps; cycle through specialists for even distribution
    slots_per_sp: dict[str, list[Slot]] = {sp_id: [] for sp_id in matched_ids}

    cursor = now
    while cursor < time_max:
        if _is_working_hour(cursor):
            slot_end = cursor + SLOT_DURATION
            for sp_id in matched_ids:
                if not any(b_start < slot_end and b_end > cursor for b_start, b_end in busy[sp_id]):
                    slots_per_sp[sp_id].append(Slot(
                        specialist_id=sp_id,
                        start=cursor,
                        end=slot_end,
                        display_end=cursor + timedelta(minutes=SLOT_DISPLAY),
                    ))
        cursor += SLOT_DURATION

    # Interleave slots round-robin: sp1[0], sp2[0], sp3[0], sp1[1], ...
    all_slots: list[Slot] = []
    max_len = max((len(v) for v in slots_per_sp.values()), default=0)
    for i in range(max_len):
        for sp_id in matched_ids:
            if i < len(slots_per_sp[sp_id]):
                all_slots.append(slots_per_sp[sp_id][i])
        if len(all_slots) >= TOP_SLOTS:
            break

    all_slots.sort(key=lambda s: s.start)
    return all_slots[:TOP_SLOTS]


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
        event = {
            "summary": f"SafeHaven — {client_name}" if client_name else "SafeHaven Session",
            "description": (
                f"Client session (45 min) + 15 min buffer. Booked via SafeHaven bot.\n"
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
