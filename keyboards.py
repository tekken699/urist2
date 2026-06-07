from math import ceil

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CLAIM_TYPES, MAX_EMPTY_PHOTOS, PARTNERS_PAGE_SIZE
from database import Partner, count_partners, list_partners

# Текст reply-кнопок главного меню. Используется и в keyboards.py, и в handlers/menu.py.
MAIN_BTN_NEW_CLAIM = "📝 Создать претензию"
MAIN_BTN_ADD_PARTNER = "➕ Добавить партнёра"
MAIN_BTN_HELP = "❓ Помощь"
MAIN_BTN_ADMIN = "🛠 Админ-панель"


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню — постоянная reply-клавиатура снизу экрана."""
    rows = [
        [KeyboardButton(text=MAIN_BTN_NEW_CLAIM)],
        [
            KeyboardButton(text=MAIN_BTN_ADD_PARTNER),
            KeyboardButton(text=MAIN_BTN_HELP),
        ],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=MAIN_BTN_ADMIN)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие…",
    )


def claim_types_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, title in CLAIM_TYPES.items():
        kb.button(text=title, callback_data=f"claim:{code}")
    kb.button(text="❌ Отмена", callback_data="claim:cancel")
    kb.adjust(1)
    return kb.as_markup()


async def partners_kb(
    claim_code: str,
    page: int = 0,
    query: str = "",
) -> InlineKeyboardMarkup:
    page_size = PARTNERS_PAGE_SIZE
    offset = page * page_size
    partners = await list_partners(query=query, limit=page_size, offset=offset)
    total = await count_partners(query=query)
    pages = max(1, ceil(total / page_size))

    kb = InlineKeyboardBuilder()
    for p in partners:
        kb.button(text=p.name, callback_data=f"pick:{claim_code}:{p.id}")
    kb.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="« Назад",
            callback_data=f"page:{claim_code}:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{pages}",
        callback_data="noop",
    ))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(
            text="Вперёд »",
            callback_data=f"page:{claim_code}:{page + 1}",
        ))
    kb.row(*nav)

    kb.row(InlineKeyboardButton(
        text="🔍 Поиск по фамилии/ИНН",
        callback_data=f"search:{claim_code}",
    ))
    kb.row(InlineKeyboardButton(text="❌ Отмена", callback_data="claim:cancel"))
    return kb.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить партнёра", callback_data="adm:add")
    kb.button(text="📋 Список / редактировать", callback_data="adm:list:0")
    kb.button(text="💾 Выгрузить базу", callback_data="adm:dump")
    kb.adjust(1)
    return kb.as_markup()


def admin_partners_kb(partners: list[Partner], page: int, pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in partners:
        kb.button(text=p.name, callback_data=f"adm:open:{p.id}")
    kb.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="« Назад", callback_data=f"adm:list:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{pages}", callback_data="noop",
    ))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(
            text="Вперёд »", callback_data=f"adm:list:{page + 1}",
        ))
    kb.row(*nav)
    kb.row(InlineKeyboardButton(text="« В меню админа", callback_data="adm:menu"))
    return kb.as_markup()


def partner_card_kb(partner_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать", callback_data=f"adm:edit:{partner_id}")
    kb.button(text="🗑 Удалить", callback_data=f"adm:del:{partner_id}")
    kb.button(text="« Назад к списку", callback_data="adm:list:0")
    kb.adjust(1)
    return kb.as_markup()


def edit_fields_kb(partner_id: int) -> InlineKeyboardMarkup:
    from database import PARTNER_FIELDS, PARTNER_FIELD_LABELS
    kb = InlineKeyboardBuilder()
    for field in PARTNER_FIELDS:
        kb.button(
            text=PARTNER_FIELD_LABELS[field].split("(")[0].strip(),
            callback_data=f"adm:editfield:{partner_id}:{field}",
        )
    kb.adjust(1)
    kb.row(InlineKeyboardButton(
        text="« Назад", callback_data=f"adm:open:{partner_id}",
    ))
    return kb.as_markup()


def photos_kb(uploaded: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    label = (
        f"✅ Готово ({uploaded}/{MAX_EMPTY_PHOTOS})"
        if uploaded
        else "⏭ Без фото"
    )
    kb.button(text=label, callback_data="photos:done")
    kb.button(text="❌ Отмена", callback_data="claim:cancel")
    kb.adjust(1)
    return kb.as_markup()


def confirm_delete_kb(partner_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"adm:delok:{partner_id}")
    kb.button(text="« Отмена", callback_data=f"adm:open:{partner_id}")
    kb.adjust(1)
    return kb.as_markup()
