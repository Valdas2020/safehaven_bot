from dataclasses import dataclass
from datetime import date, time
from typing import Optional

MONTH_NAMES: dict[str, list[str]] = {
    "EN": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "RU": [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ],
    "UA": [
        "січня",
        "лютого",
        "березня",
        "квітня",
        "травня",
        "червня",
        "липня",
        "серпня",
        "вересня",
        "жовтня",
        "листопада",
        "грудня",
    ],
    "CZ": [
        "ledna",
        "února",
        "března",
        "dubna",
        "května",
        "června",
        "července",
        "srpna",
        "září",
        "října",
        "listopadu",
        "prosince",
    ],
}

WEEKDAY_SHORT: dict[str, list[str]] = {
    "EN": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "RU": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    "UA": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
    "CZ": ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"],
}

WEEKDAY_FULL: dict[str, list[str]] = {
    "EN": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "RU": [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье",
    ],
    "UA": ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"],
    "CZ": ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"],
}


@dataclass
class BookingWindow:
    date: date
    start: time
    end: time  # start + 60 min (full booking window)
    display_end: time  # start + 45 min (shown to user)
    is_online: bool
    address: Optional[str]  # None if online
    category: str
    calendar_id: str
    specialist_name: str

    def label(self, lang: str = "EN") -> str:
        wd = WEEKDAY_SHORT.get(lang, WEEKDAY_SHORT["EN"])[self.date.weekday()]
        fmt = "💻" if self.is_online else "📍"
        return (
            f"{wd} {self.date.strftime('%d.%m')}  "
            f"{self.start.strftime('%H:%M')}–{self.display_end.strftime('%H:%M')} {fmt}"
        )

    def confirmation_text(self, lang: str = "EN") -> str:
        wd = WEEKDAY_FULL.get(lang, WEEKDAY_FULL["EN"])[self.date.weekday()]
        month = MONTH_NAMES.get(lang, MONTH_NAMES["EN"])[self.date.month - 1]
        date_str = f"{wd}, {self.date.day} {month} {self.date.year}"

        lines = [
            "✅ Booking confirmed!",
            "",
            f"📅 {date_str}",
            f"🕐 {self.start.strftime('%H:%M')}–{self.display_end.strftime('%H:%M')} (45-min session)",
            f"👤 {self.specialist_name} · {self.category}",
            "",
        ]
        if self.is_online:
            lines.append("💻 Format: Online session")
        else:
            lines.append("📍 Format: In-person")
            lines.append(f"🗺 Address: {self.address}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "type": "window",
            "date": self.date.isoformat(),
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "display_end": self.display_end.isoformat(),
            "is_online": self.is_online,
            "address": self.address,
            "category": self.category,
            "calendar_id": self.calendar_id,
            "specialist_name": self.specialist_name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BookingWindow":
        return cls(
            date=date.fromisoformat(d["date"]),
            start=time.fromisoformat(d["start"]),
            end=time.fromisoformat(d["end"]),
            display_end=time.fromisoformat(d["display_end"]),
            is_online=d["is_online"],
            address=d.get("address"),
            category=d["category"],
            calendar_id=d["calendar_id"],
            specialist_name=d["specialist_name"],
        )
