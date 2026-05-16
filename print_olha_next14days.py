"""
Local test script: print Olha Mazur's available slots for next 14 days.

Usage:
    /home/ralph/CCP/safehaven_bot/venv/bin/python3 print_olha_next14days.py

Reads SPREADSHEET_ID, SCHEDULE_SHEET_TAB, GOOGLE_SERVICE_ACCOUNT_JSON from .env
"""

import os
import sys

# Patch required vars so config.py does not raise before we use it
os.environ.setdefault("BOT_TOKEN", "dummy")
os.environ.setdefault("WEBHOOK_HOST", "https://dummy.example.com")
os.environ.setdefault("DATABASE_URL", "postgresql://dummy")

from datetime import date, timedelta  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.sheets_repository import get_specialist_slots  # noqa: E402

SPREADSHEET_ID = os.getenv(
    "SPREADSHEET_ID", "1JxwYMTyuPx4xGTIft_WkmeugqZ9803Lv5hqVEuqFQYk"
)
SCHEDULE_SHEET_TAB = os.getenv("SCHEDULE_SHEET_TAB", "5")
SPECIALIST_NAME = "Olha Mazur"

today = date.today()
date_to = today + timedelta(days=14)

print(f"Fetching slots for '{SPECIALIST_NAME}' from {today} to {date_to}")
print(f"Sheet: {SPREADSHEET_ID} / tab '{SCHEDULE_SHEET_TAB}'\n")

try:
    windows = get_specialist_slots(
        SPECIALIST_NAME, today, date_to, SPREADSHEET_ID, SCHEDULE_SHEET_TAB
    )
except Exception as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(1)

if not windows:
    print("No rows found.")
    sys.exit(0)

print(f"Found {len(windows)} window(s):\n")
for w in windows:
    loc = "online" if w.is_online else f"offline — {w.address}"
    print(
        f"  {w.date.isoformat()}  "
        f"{w.start.strftime('%H:%M')}–{w.end.strftime('%H:%M')}  "
        f"(display: –{w.display_end.strftime('%H:%M')})  "
        f"online={w.is_online}  "
        f"category={w.category!r}  "
        f"calendar_id={w.calendar_id!r}  "
        f"address={w.address!r}"
    )
