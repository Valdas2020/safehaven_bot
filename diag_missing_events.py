"""
Diagnostic: investigate missing calendar events for a specialist.

Usage:
    ./venv/bin/python3 diag_missing_events.py <calendar_id> [--db DSN]

Positional:
    calendar_id   — Google Calendar ID to inspect (from sheet "ID kalendáře" column)

Options:
    --db DSN      — PostgreSQL connection string (default: DATABASE_URL env var)

What it does:
  1. Lists all events (including deleted/cancelled) in two windows:
       2026-05-18..2026-05-20  and  2026-05-25..2026-05-27
  2. Queries the bookings table for matching rows and verifies each
     calendar_event_id via events.get().
  3. Reports status of each: active, cancelled, missing (404), or mismatched.
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

os.environ.setdefault("BOT_TOKEN", "dummy")
os.environ.setdefault("WEBHOOK_HOST", "https://dummy.example.com")

from dotenv import load_dotenv
load_dotenv()

PRAGUE_TZ = ZoneInfo("Europe/Prague")


# ── SECTION 1: Google Calendar API ────────────────────────────────────────────

def calendar_diag(calendar_id: str) -> None:
    """List events with showDeleted=true for the two affected windows."""
    from services.calendar import _build_service

    service = _build_service()

    windows = [
        ("2026-05-18", "2026-05-20", "2026-05-19 bookings"),
        ("2026-05-25", "2026-05-27", "2026-05-26 bookings"),
    ]

    for date_from, date_to, label in windows:
        tmin = datetime.fromisoformat(f"{date_from}T00:00:00").replace(tzinfo=PRAGUE_TZ).isoformat()
        tmax = datetime.fromisoformat(f"{date_to}T00:00:00").replace(tzinfo=PRAGUE_TZ).isoformat()

        print(f"\n{'='*70}")
        print(f"Window: {label}  ({date_from} → {date_to})")
        print(f"{'='*70}")

        try:
            events = service.events().list(
                calendarId=calendar_id,
                timeMin=tmin,
                timeMax=tmax,
                singleEvents=True,
                showDeleted=True,
                orderBy="startTime",
            ).execute()
        except Exception as exc:
            print(f"  ERROR querying calendar: {exc}")
            continue

        items = events.get("items", [])
        print(f"  Found {len(items)} event(s)\n")

        if not items:
            print("  (no events in this window)")
            continue

        for ev in items:
            status = ev.get("status", "?")
            marker = ""
            if status == "cancelled":
                marker = " [CANCELLED/DELETED]"
            elif status != "confirmed":
                marker = f" [status={status}]"

            print(f"  {status.upper()}{marker}")
            print(f"    id:         {ev.get('id')}")
            print(f"    summary:    {ev.get('summary', '(none)')}")
            start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
            end   = ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date", "")
            print(f"    start:      {start}")
            print(f"    end:        {end}")
            print(f"    updated:    {ev.get('updated')}")
            creator = ev.get("creator", {})
            print(f"    creator:    {creator.get('email', '(unknown)')}")
            org = ev.get("organizer", {})
            print(f"    organizer:  {org.get('email', '(unknown)')}")
            desc = (ev.get("description") or "")[:200]
            print(f"    desc:       {desc}")
            print()


# ── SECTION 2: Database forensics ──────────────────────────────────────────────

async def db_forensics(calendar_id: str, dsn: str) -> None:
    """Cross-reference bookings table with calendar state."""
    import asyncpg

    dsn = dsn.replace("postgres://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn)

    rows = await conn.fetch("""
        SELECT
            b.id AS booking_id,
            b.user_id,
            b.specialist_id AS cal_id_on_row,
            b.calendar_event_id,
            b.start_time,
            b.end_time,
            b.created_at,
            b.status,
            u.telegram_id,
            u.name AS client_name
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        WHERE b.specialist_id = $1
           OR b.start_time BETWEEN '2026-05-18' AND '2026-05-20'
           OR b.start_time BETWEEN '2026-05-25' AND '2026-05-27'
        ORDER BY b.start_time
    """, calendar_id)

    print(f"\n{'='*70}")
    print(f"DB Forensics — bookings matching calendar_id or date windows")
    print(f"{'='*70}")
    print(f"  Found {len(rows)} booking row(s)\n")

    if not rows:
        print("  No matching bookings in DB.")
        await conn.close()
        return

    # Integrity checks
    cal_mismatches = [r for r in rows if r["cal_id_on_row"] != calendar_id and r["start_time"]]
    dup_events: dict = {}
    for r in rows:
        eid = r["calendar_event_id"]
        if eid:
            dup_events.setdefault(eid, []).append(r["booking_id"])

    print("  --- Integrity Checks ---")
    if cal_mismatches:
        print(f"  WARNING: {len(cal_mismatches)} booking(s) have specialist_id != {calendar_id}:")
        for r in cal_mismatches:
            print(f"    booking_id={r['booking_id']} specialist_id={r['cal_id_on_row']} start={r['start_time']}")
    else:
        print("  OK: all bookings have consistent specialist_id.")

    dup_found = False
    for eid, bids in dup_events.items():
        if len(bids) > 1:
            print(f"  ALERT: calendar_event_id {eid} appears in {len(bids)} bookings: {bids}")
            dup_found = True
    if not dup_found:
        print("  OK: no duplicate calendar_event_id entries.")

    null_evt = [r for r in rows if not r["calendar_event_id"]]
    if null_evt:
        print(f"  WARNING: {len(null_evt)} booking(s) with NULL calendar_event_id:")
        for r in null_evt:
            print(f"    booking_id={r['booking_id']} start={r['start_time']} client={r['client_name']}")

    print("\n  --- Calendar Event Verification ---")
    from services.calendar import _build_service
    service = _build_service()

    verified = 0
    for r in rows:
        eid = r["calendar_event_id"]
        if not eid:
            continue
        bid = r["booking_id"]
        print(f"  booking_id={bid} event_id={eid} start={r['start_time']} client={r['client_name']} (tg={r['telegram_id']})")

        try:
            ev = service.events().get(calendarId=r["cal_id_on_row"], eventId=eid).execute()
            status = ev.get("status", "?")
            print(f"    → GET OK  status={status} summary={ev.get('summary','?')} updated={ev.get('updated')}")
            verified += 1
        except Exception as exc:
            # 404 → try listing with showDeleted
            err_str = str(exc)
            if "404" in err_str or "notFound" in err_str or "not found" in err_str.lower():
                print(f"    → GET 404 — searching in deleted events...")
                try:
                    tmin = r["start_time"].replace(tzinfo=PRAGUE_TZ).isoformat()
                    tmax = r["end_time"].replace(tzinfo=PRAGUE_TZ).isoformat()
                    events = service.events().list(
                        calendarId=r["cal_id_on_row"],
                        timeMin=tmin,
                        timeMax=tmax,
                        showDeleted=True,
                    ).execute()
                    found = False
                    for ev in events.get("items", []):
                        if ev.get("id") == eid:
                            print(f"    → FOUND DELETED: status={ev.get('status')} updated={ev.get('updated')}")
                            found = True
                            break
                    if not found:
                        print(f"    → NOT FOUND even in deleted. Event may have been permanently removed or cal_id mismatch.")
                except Exception as exc2:
                    print(f"    → Deleted-search failed: {exc2}")
            else:
                print(f"    → GET FAILED: {exc}")
        print()

    print(f"  Verified {verified}/{len(rows)} events.")

    await conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Diagnose missing calendar events")
    parser.add_argument("calendar_id", help="Google Calendar ID to inspect")
    parser.add_argument("--db", default=os.getenv("DATABASE_URL", ""), help="PostgreSQL DSN")
    args = parser.parse_args()

    if not args.calendar_id:
        print("ERROR: calendar_id is required")
        sys.exit(1)

    # 1. Calendar diag
    calendar_diag(args.calendar_id)

    # 2. DB forensics (if DB available)
    if args.db:
        await db_forensics(args.calendar_id, args.db)
    else:
        print("\n⚠️  Skipping DB forensics — no DATABASE_URL provided.")


if __name__ == "__main__":
    asyncio.run(main())
