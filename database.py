import aiosqlite
from dataclasses import dataclass
from typing import Optional

from config import DB_PATH


@dataclass
class Partner:
    id: int
    name: str
    full_fio: str
    inn: str
    ogrnip: str
    address: str
    email: str
    phone: str
    dkk_number: str
    dkk_date: str  # stored as DD.MM.YYYY string — used verbatim in templates


PARTNER_FIELDS = (
    "name", "full_fio", "inn", "ogrnip", "address",
    "email", "phone", "dkk_number", "dkk_date",
)

PARTNER_FIELD_LABELS = {
    "name": "Краткое название (напр. «ИП Хлебкин А.А.»)",
    "full_fio": "Полное ФИО в дательном падеже (напр. «Хлебкину Александру Александровичу»)",
    "inn": "ИНН",
    "ogrnip": "ОГРНИП",
    "address": "Юридический адрес",
    "email": "E-mail",
    "phone": "Телефон",
    "dkk_number": "Номер договора коммерческой концессии (напр. «24022024»)",
    "dkk_date": "Дата заключения ДКК в формате ДД.ММ.ГГГГ",
}


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS partners (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                full_fio     TEXT NOT NULL,
                inn          TEXT NOT NULL,
                ogrnip       TEXT NOT NULL,
                address      TEXT NOT NULL,
                email        TEXT NOT NULL,
                phone        TEXT NOT NULL,
                dkk_number   TEXT NOT NULL,
                dkk_date     TEXT NOT NULL
            )
            """
        )
        await db.commit()


def _row_to_partner(row) -> Partner:
    return Partner(**dict(row))


async def add_partner(data: dict) -> int:
    cols = ", ".join(PARTNER_FIELDS)
    placeholders = ", ".join("?" for _ in PARTNER_FIELDS)
    values = [data[f] for f in PARTNER_FIELDS]
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"INSERT INTO partners ({cols}) VALUES ({placeholders})", values
        )
        await db.commit()
        return cursor.lastrowid


async def update_partner(partner_id: int, field: str, value: str) -> None:
    if field not in PARTNER_FIELDS:
        raise ValueError(f"unknown field {field}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE partners SET {field} = ? WHERE id = ?",
            (value, partner_id),
        )
        await db.commit()


async def delete_partner(partner_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM partners WHERE id = ?", (partner_id,))
        await db.commit()


async def get_partner(partner_id: int) -> Optional[Partner]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM partners WHERE id = ?", (partner_id,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_partner(row) if row else None


async def list_partners(
    query: str = "",
    limit: int = 1000,
    offset: int = 0,
) -> list[Partner]:
    sql = "SELECT * FROM partners"
    params: list = []
    if query:
        sql += " WHERE name LIKE ? OR full_fio LIKE ? OR inn LIKE ?"
        like = f"%{query}%"
        params.extend([like, like, like])
    sql += " ORDER BY name LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cur:
            return [_row_to_partner(r) for r in await cur.fetchall()]


async def count_partners(query: str = "") -> int:
    sql = "SELECT COUNT(*) FROM partners"
    params: list = []
    if query:
        sql += " WHERE name LIKE ? OR full_fio LIKE ? OR inn LIKE ?"
        like = f"%{query}%"
        params.extend([like, like, like])
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, params) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0
