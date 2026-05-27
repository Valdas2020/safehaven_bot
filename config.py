import os

from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "safehaven-secret")
WEBHOOK_HOST: str = os.getenv(
    "WEBHOOK_HOST", ""
)  # e.g. https://reachable-bot.onrender.com
WEBHOOK_PATH: str = "/webhook"
WEBHOOK_URL: str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Server
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", 8000))

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # postgresql+asyncpg://...

# Google Calendar — OAuth2 token for bot@amiga-migrant.cz
GOOGLE_CALENDAR_TOKEN_JSON: str = os.getenv("GOOGLE_CALENDAR_TOKEN_JSON", "")

# Google Sheets — Service Account (must have Editor access to the sheet)
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

# Google Sheets — reporting sheet
GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")

# Google Sheets — specialist schedule
SPREADSHEET_ID: str = os.getenv(
    "SPREADSHEET_ID", "1JxwYMTyuPx4xGTIft_WkmeugqZ9803Lv5hqVEuqFQYk"
)
SCHEDULE_SHEET_TAB: str = os.getenv("SCHEDULE_SHEET_TAB", "5")
SPECIALIST_NAME: str = os.getenv("SPECIALIST_NAME", "Olha Mazur")

# Specialist Telegram IDs for post-visit prompts
# Format: "specialist_id:telegram_id,specialist_id2:telegram_id2"
# Example: SPECIALIST_TG_IDS=psych_adult_1:123456789,psych_children:987654321
SPECIALIST_TG_IDS: dict[str, int] = {}
for _pair in os.getenv("SPECIALIST_TG_IDS", "").split(","):
    if ":" in _pair:
        _sp_id, _tg_id = _pair.strip().split(":", 1)
        if _tg_id.strip().lstrip("-").isdigit():
            SPECIALIST_TG_IDS[_sp_id.strip()] = int(_tg_id.strip())

# SMTP (for specialist email notifications)
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
SMTP_USER: str = os.getenv("SMTP_USER", "")  # sender address
SMTP_PASS: str = os.getenv("SMTP_PASS", "")  # app password

# Admin access (comma-separated Telegram user IDs)
ADMIN_IDS: set[int] = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

# Operator Telegram IDs for "call me back" notifications
OPERATOR_PSYCHOLOG_ID: int = int(os.getenv("OPERATOR_PSYCHOLOG_ID", "1075908059"))
OPERATOR_IKP_ID: int = int(os.getenv("OPERATOR_IKP_ID", "804451651"))

# Operator who receives all new booking notifications
OPERATOR_BOOKING_ID: int = int(os.getenv("OPERATOR_BOOKING_ID", "1075908059"))

# Organisation phone shown to client after callback request
ORG_PHONE: str = os.getenv("ORG_PHONE", "")

# GDPR auto-cleanup: set to "false" to disable scheduled deletion of inactive users
CLEANUP_ENABLED: bool = os.getenv("CLEANUP_ENABLED", "true").lower() not in ("false", "0", "no")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST is not set")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")
