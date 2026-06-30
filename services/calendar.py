"""
Google Calendar integration via OAuth2 (bot@amiga-migrant.cz account).

Setup:
  1. Run get_calendar_token.py once locally to obtain token.json
  2. Set GOOGLE_CALENDAR_TOKEN_JSON env var in Render to the token JSON content
  3. Each specialist must share their calendar with bot@amiga-migrant.cz
     (Access level: "Make changes to events")

Matching logic:
  - Filter by age_group (child / adult) from user intake
  - Filter by triage_level (urgent → only specialists who handle urgent)
  - Per-specialist AM/PM slot selection
  - Return up to 4 slots (2 normal + 2 crisis)
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from zoneinfo import ZoneInfo

from config import GOOGLE_CALENDAR_TOKEN_JSON
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
PRAGUE_TZ = ZoneInfo("Europe/Prague")

# ── Specialist registry ───────────────────────────────────────────────────────
# calendar_id must match the "ID kalendáře" column in the Google Sheet.
# email = specialist's personal email for booking notifications (fill in).
SPECIALISTS: dict[str, dict] = {
    "psych_children_ortynska": {
        "calendar_id": "c_191b2b58915d461cccf64d5cd8c36380de56be47fd10e3f66ea08a077d91e4b2@group.calendar.google.com",
        "email": "",  # fallback; real email read from sheet "E-mailová adresa" column
        "name": "Vladyslava Ortynska",
        "name_i18n": {
            "UA": "Владислава Ортинська",
            "RU": "Владислава Ортынская",
            "CZ": "Vladyslava Ortynska",
            "EN": "Vladyslava Ortynska",
        },
        "type": "psychologist",
        "age_group": ["child"],
        "triage_level": ["normal"],
    },
    "psych_adult_filchakova": {
        "calendar_id": "c_bfbf6e8ea617981b4458946ca2fc85e108480a3c94fe48f9f05488309476903a@group.calendar.google.com",
        "email": "",  # fallback; real email read from sheet
        "name": "Alisa Filchakova",
        "name_i18n": {
            "UA": "Аліса Філчакова",
            "RU": "Алиса Филчакова",
            "CZ": "Alisa Filchakova",
            "EN": "Alisa Filchakova",
        },
        "type": "psychologist",
        "age_group": ["adult"],
        "triage_level": ["normal"],
    },
    "ikp_zanegina": {
        "calendar_id": "c_c186d772a150106f195628619e265270d573ebec07c597818e6bb7c7e4fc2023@group.calendar.google.com",
        "email": "",  # fallback; real email read from sheet
        "name": "Natalia Zanegina",
        "name_i18n": {
            "UA": "Наталія Занєгіна",
            "RU": "Наталия Занегина",
            "CZ": "Natalia Zanegina",
            "EN": "Natalia Zanegina",
        },
        "type": "ikp",
        "age_group": ["adult", "child"],
        "triage_level": ["normal"],
    },
    "psych_adult_beigul": {
        "calendar_id": "c_59c184c527b2df5a02e61c2fdc900363e60f44d0c9206c78743f6c35243c546c@group.calendar.google.com",
        "email": "",  # fallback; real email read from sheet
        "name": "Yulia Beigul",
        "name_i18n": {
            "UA": "Юлія Бейгул",
            "RU": "Юлия Бейгул",
            "CZ": "Yulia Beigul",
            "EN": "Yulia Beigul",
        },
        "type": "psychologist",
        "age_group": ["adult"],
        "triage_level": ["normal"],
    },
}

# Fallback defaults (each specialist overrides via slot_minutes / display_minutes)
SLOT_DURATION = timedelta(minutes=60)
SLOT_DISPLAY = 50
LOOK_AHEAD_DAYS = 7
TOP_SLOTS = 4  # 2 regular + 2 crisis
MIN_LEAD_HOURS = 4  # first slot no sooner than 4h from now
WORK_START = 9  # first slot starts 09:00 Prague
WORK_END = 21  # last slot starts 20:00, ends 21:00 (displayed as 20:00–20:45)
AM_CUTOFF = 13  # slots before 13:00 Prague are "AM"


# ── Data types ────────────────────────────────────────────────────────────────


class Slot(NamedTuple):
    specialist_id: str
    start: datetime  # UTC
    end: datetime  # start + 60 min
    display_end: datetime  # start + 45 min (shown to user)

    def label(self, lang: str = "EN") -> str:
        weekdays = {
            "UA": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
            "RU": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "CZ": ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"],
            "EN": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        }.get(lang, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        local = self.start.astimezone(PRAGUE_TZ)
        local_end = self.display_end.astimezone(PRAGUE_TZ)
        wd = weekdays[local.weekday()]
        return f"{wd} {local.strftime('%d.%m')}  {local.strftime('%H:%M')}–{local_end.strftime('%H:%M')}"


# ── Matching ──────────────────────────────────────────────────────────────────


def match_specialists(
    age_cat: str, triage_level: str, sp_type: str | None = None
) -> list[str]:
    """Return specialist IDs matching age group, triage level, and optional type."""
    return [
        sp_id
        for sp_id, sp in SPECIALISTS.items()
        if age_cat in sp["age_group"]
        and triage_level in sp["triage_level"]
        and (sp_type is None or sp.get("type") == sp_type)
    ]


# ── Calendar helpers ──────────────────────────────────────────────────────────

_calendar_service = None


def _build_service():
    global _calendar_service
    if _calendar_service is not None:
        return _calendar_service
    if not GOOGLE_CALENDAR_TOKEN_JSON:
        raise RuntimeError("GOOGLE_CALENDAR_TOKEN_JSON env var not set")
    creds = Credentials.from_authorized_user_info(
        json.loads(GOOGLE_CALENDAR_TOKEN_JSON)
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    _calendar_service = build(
        "calendar", "v3", credentials=creds, cache_discovery=False
    )
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
        logger.warning(
            "No specialists match age_cat=%s triage=%s", age_cat, triage_level
        )
        return []

    try:
        service = _build_service()
    except Exception as exc:
        logger.error("Calendar service init failed: %s", exc)
        return []

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
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
        result = (
            service.freebusy()
            .query(
                body={
                    "timeMin": now.isoformat(),
                    "timeMax": time_max.isoformat(),
                    "timeZone": "UTC",
                    "items": items,
                }
            )
            .execute()
        )
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
        dur = timedelta(minutes=sp.get("slot_minutes", SLOT_DURATION.seconds // 60))
        display = sp.get("display_minutes", SLOT_DISPLAY)
        sp_cursor = cursor
        sp_slots: list[Slot] = []
        while sp_cursor < time_max:
            if _is_working_hour(sp_cursor):
                slot_end = sp_cursor + dur
                if not any(
                    b_start < slot_end and b_end > sp_cursor
                    for b_start, b_end in busy[sp_id]
                ):
                    sp_slots.append(
                        Slot(
                            specialist_id=sp_id,
                            start=sp_cursor,
                            end=slot_end,
                            display_end=sp_cursor + timedelta(minutes=display),
                        )
                    )
            sp_cursor += dur
        slots_per_sp[sp_id] = sp_slots

    # For each specialist pick 1 AM slot (< 13:00 Prague) + 1 PM slot (≥ 13:00 Prague)
    def _pick_am_pm(slots: list[Slot]) -> list[Slot]:
        am = next(
            (s for s in slots if s.start.astimezone(PRAGUE_TZ).hour < AM_CUTOFF), None
        )
        pm = next(
            (s for s in slots if s.start.astimezone(PRAGUE_TZ).hour >= AM_CUTOFF), None
        )
        return [s for s in [am, pm] if s is not None]

    # Separate normal vs urgent-capable specialists, pick AM/PM from each group
    normal_ids = [
        sp
        for sp in matched_ids
        if "normal" in SPECIALISTS[sp]["triage_level"]
        and "urgent" not in SPECIALISTS[sp]["triage_level"]
    ]
    crisis_ids = [
        sp for sp in matched_ids if "urgent" in SPECIALISTS[sp]["triage_level"]
    ]

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
    Create an event in specialist's calendar.
    Returns Google event ID or None on failure.
    NOTE: specialist must share their calendar with bot@amiga-migrant.cz.
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
        contact_lines.append(f"tg:{telegram_id}")  # structured marker for ownership verification
        contact_str = "\n".join(contact_lines)
        session_min = sp.get("display_minutes", SLOT_DISPLAY)
        buffer_min = sp.get("slot_minutes", SLOT_DURATION.seconds // 60) - session_min
        event = {
            "summary": f"Reachable — {client_name}"
            if client_name
            else "Reachable Session",
            "description": (
                f"Client session ({session_min} min) + {buffer_min} min buffer. "
                f"Booked via Reachable bot.\n"
                f"Client: {client_name}\n"
                f"{contact_str}"
            ),
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }
        created = (
            service.events().insert(calendarId=sp["calendar_id"], body=event).execute()
        )
        logger.info("Event created: %s specialist=%s", created.get("id"), specialist_id)
        return created.get("id")
    except Exception as exc:
        logger.error("Failed to create event for %s: %s", specialist_id, exc)
        return None


def create_event_from_window(
    window,  # models.BookingWindow — avoid circular import with type hint
    telegram_user_id: int,
    client_name: str = "",
    client_phone: str = "",
    client_email: str = "",
    contact_method: str = "",
    client_age: int | None = None,
    age_cat: str = "adult",
    child_first_name: str = "",
    child_last_name: str = "",
    situation_description: str = "",
) -> str | None:
    """
    Create a calendar event from a BookingWindow (sheets-based scheduling).
    Returns Google event ID or None on failure.
    NOTE: bot@amiga-migrant.cz must have 'Make changes to events' on the calendar.
    """
    try:
        service = _build_service()

        start_dt = datetime(
            window.date.year,
            window.date.month,
            window.date.day,
            window.start.hour,
            window.start.minute,
            tzinfo=PRAGUE_TZ,
        )
        end_dt = datetime(
            window.date.year,
            window.date.month,
            window.date.day,
            window.end.hour,
            window.end.minute,
            tzinfo=PRAGUE_TZ,
        )

        fmt_label = "Online session" if window.is_online else "Offline"
        location_line = window.address if not window.is_online else "Online session"

        contact_parts = []
        if client_phone:
            cm_label = f" ({contact_method})" if contact_method else ""
            contact_parts.append(f"Phone: {client_phone}{cm_label}")
        if client_email:
            contact_parts.append(f"Email: {client_email}")
        contact_parts.append(f"Telegram ID: {telegram_user_id}")
        contact_parts.append(f"tg:{telegram_user_id}")  # structured marker for ownership verification

        situation_line = f"{situation_description}\n\n" if situation_description else ""
        child_recorded_line = (
            f"Записал(а): {client_name}\n" if age_cat == "child" and client_name else ""
        )
        description = (
            situation_line
            + "Reachable Booking\n"
            "──────────────────\n"
            f"Specialist: {window.specialist_name}\n"
            f"Category: {window.category}\n"
            f"Format: {fmt_label}\n"
            f"Location: {location_line}\n"
            + child_recorded_line
            + "\n".join(contact_parts)
            + "\nBooked via: Reachable Bot"
        )

        if age_cat == "child" and child_first_name and child_last_name:
            age_str = f", {client_age}" if client_age is not None else ""
            name_part = f"{child_first_name} {child_last_name}{age_str} - Reachable-1"
        elif client_name:
            age_str = f", {client_age}" if client_age is not None else ""
            name_part = f"{client_name}{age_str} - Reachable-1"
        else:
            name_part = "Reachable-1"
        event = {
            "summary": name_part,
            "description": description,
            "location": window.address if not window.is_online else "",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Prague"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Prague"},
        }
        created = (
            service.events().insert(calendarId=window.calendar_id, body=event).execute()
        )
        logger.info(
            "Event created: %s calendar=%s", created.get("id"), window.calendar_id
        )
        return created.get("id")
    except Exception as exc:
        logger.error("Failed to create event for %s: %s", window.specialist_name, exc)
        return None


def _event_exists(cal_id: str, event_id: str) -> bool:
    """Return True if the calendar event still exists (not deleted)."""
    try:
        service = _build_service()
        service.events().get(calendarId=cal_id, eventId=event_id).execute()
        return True
    except HttpError as exc:
        if exc.resp.status in (404, 410):
            return False
        logger.error("Error checking event existence %s: %s", event_id, exc)
        return True  # on unexpected error, don't suppress reminder
    except Exception as exc:
        logger.error("Error checking event existence %s: %s", event_id, exc)
        return True


def _delete_calendar_event_sync(calendar_id: str, event_id: str) -> bool:
    """Delete a single Google Calendar event. Returns True if deleted."""
    try:
        service = _build_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info("Deleted calendar event %s from %s", event_id, calendar_id)
        return True
    except HttpError as exc:
        if exc.resp.status in (404, 410):
            logger.warning("Calendar event %s not found (already deleted)", event_id)
            return False
        logger.error("HttpError deleting event %s: %s", event_id, exc)
        return False
    except Exception as exc:
        logger.error("Failed to delete event %s: %s", event_id, exc)
        return False


def _verify_event_ownership(
    cal_id: str, event_id: str, telegram_id: int
) -> tuple[bool, str]:
    """
    Fetch a calendar event and verify it belongs to the given user.

    Returns (ok, reason).
      ok=True  → event matches telegram_id marker
      ok=False → mismatch or fetch error (reason explains why)
    """
    try:
        service = _build_service()
        ev = service.events().get(calendarId=cal_id, eventId=event_id).execute()
    except HttpError as exc:
        if exc.resp.status in (404, 410):
            return False, "event_not_found"
        return False, f"get_failed:{exc.resp.status}"
    except Exception as exc:
        return False, f"get_failed:{exc}"

    desc = ev.get("description") or ""
    # Check for structured marker (new) or legacy "Telegram ID: N" (old events)
    tg_marker = f"tg:{telegram_id}"
    legacy_marker = f"Telegram ID: {telegram_id}"
    if tg_marker in desc or legacy_marker in desc:
        return True, "ok"

    return False, "ownership_mismatch"


async def delete_user_calendar_events(
    bookings: list[dict], telegram_id: int, reason: str = "user_deleteme"
) -> int:
    """
    Delete all Google Calendar events for a user's bookings.

    Before each delete: fetch the event and verify the description contains
    the Telegram ID marker for this user.  Skips (with ERROR log + audit) if
    the event does not belong to this user.

    Returns the number of events successfully deleted.
    specialist_id in each booking row IS the Google Calendar ID.
    """
    import asyncio
    import database as db

    if not bookings:
        return 0

    count = 0
    for b in bookings:
        event_id = b.get("calendar_event_id")
        cal_id = b.get("specialist_id")
        booking_id = b.get("id")
        user_id = b.get("user_id")

        if not event_id or not cal_id:
            logger.warning(
                "Missing event_id or cal_id for booking %s — skipping",
                booking_id,
            )
            continue

        # Phase 4 guardrail — verify ownership before deleting
        ok, verify_reason = await asyncio.get_event_loop().run_in_executor(
            None, _verify_event_ownership, cal_id, event_id, telegram_id
        )

        if not ok:
            logger.error(
                "OWNERSHIP GUARD: refusing to delete event %s from %s "
                "for booking_id=%s telegram_id=%s — reason=%s",
                event_id, cal_id, booking_id, telegram_id, verify_reason,
            )
            await db.write_audit(
                action="delete_blocked",
                reason=f"ownership_guard:{verify_reason}",
                booking_id=booking_id,
                user_id=user_id,
                specialist_id=cal_id,
                calendar_id=cal_id,
                calendar_event_id=event_id,
                error_message=f"telegram_id={telegram_id} verify_reason={verify_reason}",
            )
            continue

        await db.write_audit(
            action="delete_attempt",
            reason=reason,
            booking_id=booking_id,
            user_id=user_id,
            specialist_id=cal_id,
            calendar_id=cal_id,
            calendar_event_id=event_id,
        )

        deleted = await asyncio.get_event_loop().run_in_executor(
            None, _delete_calendar_event_sync, cal_id, event_id
        )

        if deleted:
            await db.write_audit(
                action="delete_success",
                reason=reason,
                booking_id=booking_id,
                user_id=user_id,
                specialist_id=cal_id,
                calendar_id=cal_id,
                calendar_event_id=event_id,
            )
            count += 1
        else:
            await db.write_audit(
                action="delete_fail",
                reason=reason,
                booking_id=booking_id,
                user_id=user_id,
                specialist_id=cal_id,
                calendar_id=cal_id,
                calendar_event_id=event_id,
                error_message="delete returned False",
            )

    return count
