from datetime import date, timedelta

from config import DEADLINE_DAYS

RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def parse_ru_date(s: str) -> date:
    """Parse DD.MM.YYYY (the format юристы actually type)."""
    s = s.strip().replace("/", ".").replace("-", ".")
    parts = s.split(".")
    if len(parts) != 3:
        raise ValueError("Дата должна быть в формате ДД.ММ.ГГГГ")
    d, m, y = (int(p) for p in parts)
    return date(y, m, d)


def format_ru_date(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def calc_deadline(start: date, days: int = DEADLINE_DAYS) -> date:
    """Add N calendar days; if the result lands on Sat/Sun push to Mon.

    The contract говорит «5 календарных дней», но если последний день — выходной,
    юристы переносят дедлайн на ближайший рабочий день, чтобы партнёр успел
    физически отреагировать.
    """
    deadline = start + timedelta(days=days)
    while deadline.weekday() >= 5:  # 5=Sat, 6=Sun
        deadline += timedelta(days=1)
    return deadline


def normalize_violations(raw: str) -> list[str]:
    """Split a free-text violation list into clean numbered items."""
    items: list[str] = []
    for line in raw.splitlines():
        line = line.strip(" \t-—•*0123456789).")
        if line:
            items.append(line)
    return items
