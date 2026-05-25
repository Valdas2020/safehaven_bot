"""
Diagnostic: trace slot search step by step for a given category.

Usage:
    ./venv/bin/python3 debug_slots.py [category] [days]

    category  — sheet Kategorie value, default: Psycholog
    days      — look-ahead days, default: 14

Shows every row from the sheet, why rows are skipped, freebusy results, final list.
"""

import os, sys, re
os.environ.setdefault("BOT_TOKEN", "dummy")
os.environ.setdefault("WEBHOOK_HOST", "https://dummy.example.com")
os.environ.setdefault("DATABASE_URL", "postgresql://dummy")

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv()

PRAGUE_TZ = ZoneInfo("Europe/Prague")
CATEGORY = sys.argv[1] if len(sys.argv) > 1 else "Psycholog"
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 14

from config import SPREADSHEET_ID, SCHEDULE_SHEET_TAB
from services.sheets_repository import load_rows

today = date.today()
date_to = today + timedelta(days=DAYS)
min_start_utc = datetime.now(timezone.utc) + timedelta(hours=6)

print(f"=== Slot debug: category={CATEGORY!r}  {today} → {date_to} ===")
print(f"Sheet: {SPREADSHEET_ID} / tab {SCHEDULE_SHEET_TAB!r}")
print(f"Min start UTC (6h from now): {min_start_utc.strftime('%Y-%m-%d %H:%M')}\n")

# ── 1. Load raw rows ──────────────────────────────────────────────────────────
try:
    rows = load_rows(SPREADSHEET_ID, SCHEDULE_SHEET_TAB)
except Exception as exc:
    print(f"FATAL: cannot load sheet rows: {exc}")
    sys.exit(1)

print(f"Total rows in sheet: {len(rows)}")

# Collect unique Kategorie values to help spot mismatches
cats = sorted({str(r.get("Kategorie","")).strip() for r in rows} - {""})
print(f"Unique Kategorie values: {cats}\n")

# ── 2. Walk every row and explain what happens ────────────────────────────────
_SLOT_RE = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")

passed = []
skipped_cat = 0
skipped_date = 0
skipped_slot = 0
skipped_no_cal = 0

for i, row in enumerate(rows):
    row_cat = str(row.get("Kategorie", "")).strip()
    sp_name = str(row.get("Jméno a příjmení", "")).strip()
    raw_date = str(row.get("Data", "")).strip()
    raw_slot = str(row.get("Otevírací doba", "")).strip()
    cal_id   = str(row.get("ID kalendáře", "")).strip()
    sp_email = str(row.get("E-mailová adresa", "")).strip()
    cal_id   = cal_id or sp_email

    # category filter
    if row_cat.lower() != CATEGORY.lower():
        skipped_cat += 1
        continue

    # date filter
    d = None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(raw_date, fmt).date()
            break
        except ValueError:
            pass
    if d is None:
        print(f"  ROW {i}: {sp_name!r} date={raw_date!r} → SKIP: unparseable date")
        skipped_date += 1
        continue
    if not (today <= d <= date_to):
        skipped_date += 1
        continue

    # slot filter — show raw bytes to catch en-dash issues
    cleaned = re.sub(r"\s+", "", raw_slot)
    # also replace common dash variants
    raw_bytes = " ".join(f"U+{ord(c):04X}" for c in cleaned if not c.isdigit() and c != ":")
    m = _SLOT_RE.match(cleaned)
    if not m:
        print(f"  ROW {i}: {sp_name!r}  {d}  slot={raw_slot!r}")
        print(f"          cleaned={cleaned!r}  non-digit/colon chars: {raw_bytes or '(none)'}")
        print(f"          → SKIP: slot regex no match")
        skipped_slot += 1
        continue

    h1,m1,h2,m2 = map(int, m.groups())
    start_t = time(h1,m1)
    end_t   = time(h2,m2)

    if not cal_id:
        print(f"  ROW {i}: {sp_name!r}  {d}  {start_t}–{end_t}  → SKIP: no calendar_id")
        skipped_no_cal += 1
        continue

    passed.append((d, start_t, end_t, sp_name, cal_id, row))
    print(f"  ROW {i}: {sp_name!r}  {d}  {start_t.strftime('%H:%M')}–{end_t.strftime('%H:%M')}  cal={cal_id!r}  ✓ passes sheet filter")

print(f"\nSheet filter summary: "
      f"{len(passed)} passed, "
      f"{skipped_cat} wrong-category, "
      f"{skipped_date} wrong-date, "
      f"{skipped_slot} bad-slot-format, "
      f"{skipped_no_cal} no-cal-id")

if not passed:
    print("\n⚠️  No rows passed sheet filter — nothing to freebusy-check.")
    print("Likely cause: sheet has no rows for this category+daterange,")
    print("OR Kategorie value doesn't match (see unique values above),")
    print("OR time format is not HH:MM-HH:MM (check non-digit chars above).")
    sys.exit(0)

# ── 3. Freebusy check ─────────────────────────────────────────────────────────
print("\n=== Freebusy check ===")

# 6h lead-time filter
future = [(d,s,e,n,c,r) for d,s,e,n,c,r in passed
          if datetime.combine(d,s).replace(tzinfo=PRAGUE_TZ).astimezone(timezone.utc) >= min_start_utc]
dropped_past = len(passed) - len(future)
if dropped_past:
    print(f"Dropped {dropped_past} slot(s) — too soon (<6h from now)")

if not future:
    print("⚠️  All slots are within 6h — none available.")
    sys.exit(0)

cal_ids = list({c for _,_,_,_,c,_ in future})
time_min = datetime.combine(today, time.min).replace(tzinfo=PRAGUE_TZ)
time_max = datetime.combine(date_to, time(23,59,59)).replace(tzinfo=PRAGUE_TZ)

from services.calendar import _build_service
try:
    service = _build_service()
    result = service.freebusy().query(body={
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "timeZone": "UTC",
        "items": [{"id": c} for c in cal_ids],
    }).execute()
    print("Freebusy query OK")
    for cal_id in cal_ids:
        periods = result.get("calendars",{}).get(cal_id,{}).get("busy",[])
        print(f"  {cal_id}: {len(periods)} busy period(s)")
        for p in periods:
            print(f"    {p['start']} → {p['end']}")
except Exception as exc:
    print(f"Freebusy query FAILED: {exc}")
    print("(Slots would be returned unfiltered in production)")
    result = {"calendars": {}}

# ── 4. Final availability ─────────────────────────────────────────────────────
print("\n=== Available slots (final) ===")
available = []
for d,s,e,n,c,_ in future:
    start_utc = datetime.combine(d,s).replace(tzinfo=PRAGUE_TZ).astimezone(timezone.utc)
    end_utc   = datetime.combine(d,e).replace(tzinfo=PRAGUE_TZ).astimezone(timezone.utc)
    busy_ranges = [
        (datetime.fromisoformat(b["start"]).replace(tzinfo=timezone.utc),
         datetime.fromisoformat(b["end"]).replace(tzinfo=timezone.utc))
        for b in result.get("calendars",{}).get(c,{}).get("busy",[])
    ]
    overlap = any(bs < end_utc and be > start_utc for bs,be in busy_ranges)
    status = "BUSY (freebusy overlap)" if overlap else "FREE ✓"
    print(f"  {n!r}  {d}  {s.strftime('%H:%M')}–{e.strftime('%H:%M')}  {status}")
    if not overlap:
        available.append((d,s,e,n,c))

print(f"\nResult: {len(available)} available slot(s) out of {len(future)} candidates")
if not available:
    print("⚠️  All slots are marked busy in Google Calendar.")
