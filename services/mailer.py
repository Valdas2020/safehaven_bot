"""
Email notifications to specialists after a booking is confirmed.

Requires env vars:
  SMTP_HOST  — default: smtp.gmail.com
  SMTP_PORT  — default: 587 (STARTTLS)
  SMTP_USER  — sender Gmail address (e.g. bot@safehaven.org)
  SMTP_PASS  — Gmail App Password (not the account password)
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo
from datetime import datetime

import aiosmtplib

from config import SMTP_HOST, SMTP_PORT, SMTP_PASS, SMTP_USER

logger = logging.getLogger(__name__)
PRAGUE_TZ = ZoneInfo("Europe/Prague")


async def send_client_confirmation(
    client_email: str,
    client_name: str,
    specialist_name: str,
    start: datetime,
    end: datetime,
    lang: str = "EN",
) -> bool:
    """
    Send booking confirmation to the client.
    Returns True on success, False on failure (non-fatal).
    """
    if not SMTP_USER or not SMTP_PASS:
        return False
    if not client_email:
        return False

    local_start = start.astimezone(PRAGUE_TZ)
    local_end   = end.astimezone(PRAGUE_TZ)
    date_str = local_start.strftime("%A, %d %B %Y")
    time_str = f"{local_start.strftime('%H:%M')}–{local_end.strftime('%H:%M')} (Prague)"

    subjects = {
        "UA": f"SafeHaven: Сесія заброньована — {date_str}",
        "RU": f"SafeHaven: Сессия забронирована — {date_str}",
        "CZ": f"SafeHaven: Termín zarezervován — {date_str}",
        "EN": f"SafeHaven: Session booked — {date_str}",
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

    body_html = f"""
<html><body style="font-family: Arial, sans-serif; color: #2C2C2C; max-width: 600px;">
  <h2 style="color: #5B7B5E;">✅ {body_line}</h2>
  <p>{greeting}</p>
  <table style="border-collapse: collapse; width: 100%;">
    <tr><td style="padding: 8px; font-weight: bold;">Specialist</td>
        <td style="padding: 8px;">{specialist_name}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Date</td>
        <td style="padding: 8px;">{date_str}</td></tr>
    <tr><td style="padding: 8px; font-weight: bold;">Time</td>
        <td style="padding: 8px;">{time_str}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Duration</td>
        <td style="padding: 8px;">45 min</td></tr>
  </table>
  <p style="margin-top: 24px; color: #888; font-size: 13px;">
    SafeHaven bot — automated notification.
  </p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"SafeHaven Bot <{SMTP_USER}>"
    msg["To"]      = client_email
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
) -> bool:
    """
    Send booking notification email to the specialist.
    Returns True on success, False on failure (non-fatal).
    """
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP not configured — skipping email notification")
        return False

    local_start = start.astimezone(PRAGUE_TZ)
    local_end   = end.astimezone(PRAGUE_TZ)
    date_str = local_start.strftime("%A, %d %B %Y")
    time_str = f"{local_start.strftime('%H:%M')}–{local_end.strftime('%H:%M')} (Prague)"

    subject = f"SafeHaven: New session booked — {date_str}"

    body_html = f"""
<html><body style="font-family: Arial, sans-serif; color: #2C2C2C; max-width: 600px;">
  <h2 style="color: #5B7B5E;">📅 New Session Booking</h2>
  <table style="border-collapse: collapse; width: 100%;">
    <tr><td style="padding: 8px; font-weight: bold;">Specialist</td>
        <td style="padding: 8px;">{specialist_name}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Client name</td>
        <td style="padding: 8px;">{client_name}</td></tr>
    <tr><td style="padding: 8px; font-weight: bold;">Date</td>
        <td style="padding: 8px;">{date_str}</td></tr>
    <tr style="background:#f5f5f5"><td style="padding: 8px; font-weight: bold;">Time</td>
        <td style="padding: 8px;">{time_str}</td></tr>
    <tr><td style="padding: 8px; font-weight: bold;">Session</td>
        <td style="padding: 8px;">45 min + 15 min buffer</td></tr>
  </table>

  <h3 style="color: #5B7B5E; margin-top: 24px;">Client's message</h3>
  <div style="background: #f9f9f9; border-left: 4px solid #5B7B5E;
              padding: 12px 16px; border-radius: 4px; white-space: pre-wrap;">{client_description}</div>

  <p style="margin-top: 24px; color: #888; font-size: 13px;">
    This notification was sent automatically by SafeHaven bot.<br>
    The event has been added to your Google Calendar.
  </p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"SafeHaven Bot <{SMTP_USER}>"
    msg["To"]      = specialist_email
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
