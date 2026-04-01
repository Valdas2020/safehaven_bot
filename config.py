import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "safehaven-secret")
WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "")  # e.g. https://safehaven-bot.onrender.com
WEBHOOK_PATH: str = "/webhook"
WEBHOOK_URL: str = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Server
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", 8000))

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # postgresql+asyncpg://...

# Google Calendar
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

# SMTP (for specialist email notifications)
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
SMTP_USER: str = os.getenv("SMTP_USER", "")   # sender address
SMTP_PASS: str = os.getenv("SMTP_PASS", "")   # app password

# Admin access (comma-separated Telegram user IDs)
ADMIN_IDS: set[int] = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST is not set")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")
