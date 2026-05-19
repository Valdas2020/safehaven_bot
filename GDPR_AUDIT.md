# GDPR Data Audit — Reachable Bot

**Date:** 2026-05-19  
**Scope:** Full codebase audit of personal data storage, processing, and deletion.

---

## 1. Database

**YES — PostgreSQL** via asyncpg. Configured in `database.py:15–86`.

### Table `users` (`database.py:21–38`) — direct personal data

| Column | Type | Contents |
|--------|------|----------|
| `telegram_id` | BIGINT | Telegram user identifier |
| `name` | TEXT | First + last name (entered by client) |
| `email` | TEXT | Email address |
| `phone` | TEXT | Phone number |
| `age_cat` | TEXT | Age group (child / adult) |
| `age_years` | INT | Exact age in years |
| `contact_method` | TEXT | Preferred contact method |
| `language` | TEXT | Selected language |
| `gdpr_accepted` | BOOLEAN | Consent flag |

### Table `cases` (`database.py:52–62`) — **Article 9 GDPR special-category data**

| Column | Contents |
|--------|----------|
| `description` | Client's situation description — mental health data |
| `triage_level` | urgent / normal — crisis assessment |
| `category` | Service category selected |

### Table `bookings` (`database.py:63–74`) — indirect data

`user_id`, `specialist_id`, `start_time`, `end_time`, `calendar_event_id`

### Table `post_visit` (`database.py:75–85`) — specialist notes

`booking_id`, `status`, `type_of_work`, `note_short` (up to 200 chars — clinical note)

---

## 2. Files Written to Disk

**NO direct user data written to files.**

- `main.py:40–43`: `logging.basicConfig` has no `filename=` — output goes to **stdout only** (Render logs). No files created on disk.
- `get_calendar_token.py:34`: writes `token.json` — OAuth token, not user data.

### ⚠️ Warning — `handlers/fallback.py:32`

```python
logger.info("Fallback message | user_id=%s text=%s", message.from_user.id, message.text)
```

If a user sends a free-text message in an unhandled FSM state (e.g. types their name, phone number, or situation description), the **full message text is written to stdout logs**. Render retains logs for 7 days. This is a potential leak of Article 9 GDPR special-category data.

---

## 3. Google Sheets — Data Written

**YES — three tabs.** File: `services/reporting.py`, triggered by `sync_after_post_visit` called from `handlers/post_visit.py:93, 104, 200`.

### Tab `Sessions_Log` (`reporting.py:67–83`)

| Column | Contents | PII? |
|--------|----------|------|
| `Client_Hash` | SHA-256(`telegram_id`)[:10] | pseudonym — see note below |
| `Specialist` | `specialist_id` key string | no |
| `Note` | `note_short` — specialist's session note | ⚠️ potentially sensitive |
| `Date / Time / Status / Type_of_Work / Duration` | operational data | no |

### Tab `Intake_Stats` (`reporting.py:101–113`)

`date`, `language`, `age_cat`, `triage_level`, `category` — no direct identifiers.

### Tab `Monthly_Summary` (`reporting.py:86–98`)

Aggregated hours per specialist — no PII.

### ⚠️ Warning — `Client_Hash` is pseudonymisation, not anonymisation

`Client_Hash` = `SHA-256(str(telegram_id))[:10]`. Telegram user IDs are **public** (present in every update). Anyone with a user's Telegram ID can recompute the hash and link it to all session records in the sheet. Under GDPR this is **pseudonymised data**, not anonymous — it remains subject to erasure rights.

---

## 4. FSM State (in-memory)

**In-memory only** — `main.py:54`: `Dispatcher(storage=MemoryStorage())`.

During a session, FSM holds: `lang`, `name`, `email`, `phone`, `age_cat`, `age_years`, `contact_method`, `triage_description`, `windows`, `triage_category`, `db_user_id`.

**Data is lost on bot restart** (Render deploy). No Redis, no persistence.

---

## 5. `/deleteme` Command

**Partially works.** `handlers/privacy.py:30–31` → `database.py:174–195`.

### What IS deleted from the database (complete):

- `post_visit` records for the user's bookings
- `bookings` records for the user
- `cases` records for the user (including situation description)
- `users` record for the user

---

### 🔴 CRITICAL #1 — Google Calendar events are NOT deleted

`services/calendar.py:355–428` — on booking, an event is created in the specialist's Google Calendar with:

```
Client: {name}
Phone: {phone} ({contact_method})
Email: {email}
Telegram ID: {telegram_id}
```

After `/deleteme`, these events **remain in the specialist's calendar permanently**. GDPR Art. 17 right to erasure is not fulfilled for this data.

---

### 🔴 CRITICAL #2 — Google Sheets data is NOT deleted

`Sessions_Log` contains `Client_Hash` + `note_short`. After `/deleteme`, rows in the sheet **are not deleted or cleared**. Since the hash is recomputable from the public Telegram ID, this is pseudonymised but still subject-linked data.

---

## 6. Third-Party Services Receiving Personal Data

| Service | Data Received | File:Line |
|---------|--------------|-----------|
| **Google Calendar API** | name, phone, email, Telegram ID in event description | `calendar.py:392–407` |
| **SMTP (Gmail)** | name, email, age, situation description → specialist; name, email, booking time → client | `mailer.py:70–165, 167–252` |
| **Google Sheets API** (reporting sheet) | Client_Hash, specialist notes | `reporting.py:118–138` |
| **Telegram Bot API** | all bot messages pass through Telegram servers | everywhere |
| **Telegram (operators)** | full client data on callback request | `operator_notify.py:44–67` |

No direct calls to third-party HTTP APIs (`requests`, `httpx`, `aiohttp`) other than Google SDK and aiogram.

---

## Summary of Issues

| # | Issue | Severity |
|---|-------|----------|
| 1 | `/deleteme` does not delete events from specialists' Google Calendars | 🔴 CRITICAL |
| 2 | `/deleteme` does not delete rows from Google Sheets `Sessions_Log` | 🔴 CRITICAL |
| 3 | `Client_Hash` is pseudonymisation, not anonymisation (re-identifiable via Telegram ID) | 🟡 MEDIUM |
| 4 | `fallback.py:32` logs `message.text` — names, phones, mental health descriptions may appear in Render logs | 🟡 MEDIUM |
| 5 | Emails to specialists and Telegram messages to operators are not deleted on GDPR erasure request | 🟡 MEDIUM |
