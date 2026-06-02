"""
Email notifications to specialists after a booking is confirmed.

Requires env vars:
  SMTP_HOST  — default: smtp.gmail.com
  SMTP_PORT  — default: 587 (STARTTLS)
  SMTP_USER  — sender Gmail address (e.g. bot@reachable.org)
  SMTP_PASS  — Gmail App Password (not the account password)
"""

import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import aiosmtplib
from config import SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER
from models import MONTH_NAMES, WEEKDAY_FULL

logger = logging.getLogger(__name__)
PRAGUE_TZ = ZoneInfo("Europe/Prague")

_EMAIL_LABELS: dict[str, dict[str, str]] = {
    "UA": {
        "specialist": "Спеціаліст",
        "date": "Дата",
        "time": "Час",
        "duration": "Тривалість",
        "address": "Адреса",
        "format_online": "💻 Онлайн",
        "format_in_person": "📍 Особисто",
    },
    "RU": {
        "specialist": "Специалист",
        "date": "Дата",
        "time": "Время",
        "duration": "Длительность",
        "address": "Адрес",
        "format_online": "💻 Онлайн",
        "format_in_person": "📍 Лично",
    },
    "CZ": {
        "specialist": "Specialista",
        "date": "Datum",
        "time": "Čas",
        "duration": "Délka",
        "address": "Adresa",
        "format_online": "💻 Online",
        "format_in_person": "📍 Osobně",
    },
    "EN": {
        "specialist": "Specialist",
        "date": "Date",
        "time": "Time",
        "duration": "Duration",
        "address": "Address",
        "format_online": "💻 Online",
        "format_in_person": "📍 In-person",
    },
}


def _localized_date(dt: datetime, lang: str) -> str:
    wd = WEEKDAY_FULL.get(lang, WEEKDAY_FULL["EN"])[dt.weekday()]
    month = MONTH_NAMES.get(lang, MONTH_NAMES["EN"])[dt.month - 1]
    return f"{wd}, {dt.day} {month} {dt.year}"


async def send_client_confirmation(
    client_email: str,
    client_name: str,
    specialist_name: str,
    start: datetime,
    end: datetime,
    lang: str = "EN",
    address: str = "",
    is_online: bool = False,
) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        return False
    if not client_email:
        return False

    lbl = _EMAIL_LABELS.get(lang, _EMAIL_LABELS["EN"])
    local_start = start.astimezone(PRAGUE_TZ)
    local_end = end.astimezone(PRAGUE_TZ)
    date_str = _localized_date(local_start, lang)
    time_str = f"{local_start.strftime('%H:%M')}–{local_end.strftime('%H:%M')} (Prague)"

    subjects = {
        "UA": f"Reachable: Сесія заброньована — {date_str}",
        "RU": f"Reachable: Сессия забронирована — {date_str}",
        "CZ": f"Reachable: Termín zarezervován — {date_str}",
        "EN": f"Reachable: Session booked — {date_str}",
    }
    greetings = {
        "UA": f"Вітаємо, {client_name}!",
        "RU": f"Здравствуйте, {client_name}!",
        "CZ": f"Dobrý den, {client_name}!",
        "EN": f"Hello, {client_name}!",
    }
    bodies = {
        "UA": "Ваша сесія успішно заброньована.",
        "RU": "Ваша сессия успешно забронирована.",
        "CZ": "Váš termín byl úspěšně zarezervován.",
        "EN": "Your session has been successfully booked.",
    }
    subject = subjects.get(lang, subjects["EN"])
    greeting = greetings.get(lang, greetings["EN"])
    body_line = bodies.get(lang, bodies["EN"])

    if is_online:
        location_row = f"""
    <tr><td style="padding: 8px; font-weight: bold;">{lbl["address"]}</td>
        <td style="padding: 8px;">{lbl["format_online"]}</td></tr>"""
    elif address:
        location_row = f"""
    <tr><td style="padding: 8px; font-weight: bold;">{lbl["address"]}</td>
        <td style="padding: 8px;">{lbl["format_in_person"]}<br>{address}</td></tr>"""
    else:
        location_row = ""

    body_html = f"""
<html><body style="font-family: Arial, sans-serif; color: #2C2C2C; max-width: 600px;">
  <h2 style="color: #5B7B5E;">✅ {body_line}</h2>
  <p>{greeting}</p>
  <table style="border-collapse: collapse; width: 100%;">
    <tr><td style="padding: 8px; font-weight: bold;">{lbl["specialist"]}</td>
        <td style="padding: 8px;">{specialist_name}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">{lbl["date"]}</td>
        <td style="padding: 8px;">{date_str}</td></tr>
    <tr><td style="padding: 8px; font-weight: bold;">{lbl["time"]}</td>
        <td style="padding: 8px;">{time_str}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">{lbl["duration"]}</td>
        <td style="padding: 8px;">50 min</td></tr>{location_row}
  </table>
  <p style="margin-top: 24px; color: #888; font-size: 13px;">
    Reachable bot — automated notification.
  </p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Reachable Bot <{SMTP_USER}>"
    msg["To"] = client_email
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            start_tls=True,
        )
        logger.info("Client confirmation sent to %s", client_email)
        return True
    except Exception as exc:
        logger.error("Failed to send client confirmation to %s: %s", client_email, exc)
        return False


async def notify_specialist(
    specialist_email: str,
    specialist_name: str,
    client_name: str,
    client_description: str,
    start: datetime,
    end: datetime,
    address: str = "",
    is_online: bool = False,
    client_age: str = "",
) -> bool:
    # Disabled per GDPR simplification — calendar is source of truth
    return False
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP not configured — skipping email notification")
        return False
    if not specialist_email:
        logger.warning(
            "No specialist email — skipping notification for %s", specialist_name
        )
        return False
    if "@" not in specialist_email or specialist_email.endswith(".google.com"):
        logger.error(
            "Invalid specialist email '%s' for %s (looks like a calendar ID, not an email)",
            specialist_email,
            specialist_name,
        )
        return False

    local_start = start.astimezone(PRAGUE_TZ)
    local_end = end.astimezone(PRAGUE_TZ)
    date_str = local_start.strftime("%A, %d %B %Y")
    time_str = f"{local_start.strftime('%H:%M')}–{local_end.strftime('%H:%M')} (Prague)"

    if is_online:
        location_display = "💻 Online"
    elif address:
        location_display = f"📍 {address}"
    else:
        location_display = "—"

    subject = f"Reachable: New session booked — {date_str}"

    body_html = f"""
<html><body style="font-family: Arial, sans-serif; color: #2C2C2C; max-width: 600px;">
  <h2 style="color: #5B7B5E;">📅 New Session Booking</h2>
  <table style="border-collapse: collapse; width: 100%;">
    <tr><td style="padding: 8px; font-weight: bold;">Specialist</td>
        <td style="padding: 8px;">{specialist_name}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Client name</td>
        <td style="padding: 8px;">{client_name}</td></tr>
    <tr><td style="padding: 8px; font-weight: bold;">Age</td>
        <td style="padding: 8px;">{client_age if client_age else "—"}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Date</td>
        <td style="padding: 8px;">{date_str}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Time</td>
        <td style="padding: 8px;">{time_str}</td></tr>
    <tr><td style="padding: 8px; font-weight: bold;">Session</td>
        <td style="padding: 8px;">45 min + 15 min buffer</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Location</td>
        <td style="padding: 8px;">{location_display}</td></tr>
  </table>

  <h3 style="color: #5B7B5E; margin-top: 24px;">Client's message</h3>
  <div style="background: #f9f9f9; border-left: 4px solid #5B7B5E;
              padding: 12px 16px; border-radius: 4px; white-space: pre-wrap;">{client_description}</div>

  <p style="margin-top: 24px; color: #888; font-size: 13px;">
    This notification was sent automatically by Reachable bot.<br>
    The event has been added to your Google Calendar.
  </p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Reachable Bot <{SMTP_USER}>"
    msg["To"] = specialist_email
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            start_tls=True,
        )
        logger.info("Email sent to %s for session %s", specialist_email, local_start)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", specialist_email, exc)
        return False
