import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DB_PATH = BASE_DIR / "partners.sqlite"

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")

# Default admin — Telegram-ID владельца бота. /admin и админ-кнопка
# доступны только этим ID. Дополнительных админов можно добавить через
# переменную ADMIN_IDS="111,222" (через запятую).
_DEFAULT_ADMIN_IDS: set[int] = {798745530}
ADMIN_IDS: set[int] = _DEFAULT_ADMIN_IDS | {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

# How many days the partner has to remediate violations.
# We count calendar days (the contract clause 12.4.1 says "5 календарных дней"),
# but if the deadline lands on a weekend we push it to the next Monday so the
# notice can actually be delivered.
DEADLINE_DAYS = 5

# Pagination for the partner picker.
PARTNERS_PAGE_SIZE = 8

CLAIM_TYPES = {
    "oot": "ООТ (общая претензия)",
    "tech": "Технологическая проверка",
    "coffee": "Кофейный аудит",
    "empty": "Пустые витрины",
}

# Which docx template each claim type uses.
TEMPLATE_FOR_TYPE = {
    "oot": "oot.docx",
    "tech": "tech.docx",
    "coffee": "coffee.docx",
    "empty": "empty.docx",
}

# How many photos can be attached to the "Пустые витрины" claim.
MAX_EMPTY_PHOTOS = 4
