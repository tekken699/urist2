from math import ceil

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from config import ADMIN_IDS, DB_PATH, PARTNERS_PAGE_SIZE
from database import (
    PARTNER_FIELDS,
    PARTNER_FIELD_LABELS,
    add_partner,
    count_partners,
    delete_partner,
    get_partner,
    list_partners,
    update_partner,
)
from keyboards import (
    admin_menu_kb,
    admin_partners_kb,
    confirm_delete_kb,
    edit_fields_kb,
    main_menu_kb,
    partner_card_kb,
)
from states import AddPartner, EditPartner

router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещён.")
        return
    await state.clear()
    await message.answer("🛠 Админ-панель:", reply_markup=admin_menu_kb())




@router.callback_query(F.data == "adm:menu")
async def cb_menu(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    await cb.message.edit_text("🛠 Админ-панель:", reply_markup=admin_menu_kb())
    await cb.answer()


# ---- Список / просмотр карточки ----------------------------------------------

@router.callback_query(F.data.startswith("adm:list:"))
async def cb_list(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    page = int(cb.data.split(":")[2])
    total = await count_partners()
    pages = max(1, ceil(total / PARTNERS_PAGE_SIZE))
    partners = await list_partners(
        limit=PARTNERS_PAGE_SIZE, offset=page * PARTNERS_PAGE_SIZE,
    )
    await cb.message.edit_text(
        f"📋 Партнёров в базе: <b>{total}</b>\nВыберите карточку:",
        reply_markup=admin_partners_kb(partners, page, pages),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("adm:open:"))
async def cb_open(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    pid = int(cb.data.split(":")[2])
    p = await get_partner(pid)
    if not p:
        await cb.answer("Не найдено", show_alert=True)
        return
    text = (
        f"<b>{p.name}</b>\n\n"
        f"ФИО: {p.full_fio}\n"
        f"ИНН: <code>{p.inn}</code>\n"
        f"ОГРНИП: <code>{p.ogrnip}</code>\n"
        f"Адрес: {p.address}\n"
        f"E-mail: {p.email}\n"
        f"Тел.: {p.phone}\n"
        f"ДКК: №{p.dkk_number} от {p.dkk_date}"
    )
    await cb.message.edit_text(text, reply_markup=partner_card_kb(pid))
    await cb.answer()


# ---- Удаление ----------------------------------------------------------------

@router.callback_query(F.data.startswith("adm:del:"))
async def cb_del_confirm(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    pid = int(cb.data.split(":")[2])
    p = await get_partner(pid)
    if not p:
        await cb.answer("Не найдено", show_alert=True)
        return
    await cb.message.edit_text(
        f"Удалить <b>{p.name}</b>?",
        reply_markup=confirm_delete_kb(pid),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("adm:delok:"))
async def cb_del_ok(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    pid = int(cb.data.split(":")[2])
    await delete_partner(pid)
    await cb.message.edit_text(
        "✅ Удалено.", reply_markup=admin_menu_kb(),
    )
    await cb.answer()


# ---- Редактирование одного поля ---------------------------------------------

@router.callback_query(F.data.startswith("adm:edit:"))
async def cb_edit(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    pid = int(cb.data.split(":")[2])
    await cb.message.edit_text(
        "Выберите поле для редактирования:",
        reply_markup=edit_fields_kb(pid),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("adm:editfield:"))
async def cb_edit_field(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    _, _, pid, field = cb.data.split(":")
    await state.set_state(EditPartner.waiting_value)
    await state.update_data(partner_id=int(pid), field=field)
    await cb.message.edit_text(
        f"Введите новое значение поля «{PARTNER_FIELD_LABELS[field]}»:\n"
        "/cancel — отмена."
    )
    await cb.answer()


@router.message(EditPartner.waiting_value)
async def msg_edit_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await update_partner(data["partner_id"], data["field"], message.text.strip())
    await state.clear()
    p = await get_partner(data["partner_id"])
    await message.answer(
        f"✅ Поле обновлено.\n\n<b>{p.name}</b>",
        reply_markup=partner_card_kb(data["partner_id"]),
    )


# ---- Дамп БД ----------------------------------------------------------------

@router.callback_query(F.data == "adm:dump")
async def cb_dump(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    if not DB_PATH.exists():
        await cb.answer("База ещё пуста", show_alert=True)
        return
    await cb.message.answer_document(
        FSInputFile(DB_PATH, filename="partners.sqlite"),
        caption="📦 Бэкап базы данных.",
    )
    await cb.answer("Готово")


# ---- Пошаговое добавление партнёра ------------------------------------------

@router.callback_query(F.data == "adm:add")
async def cb_add(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    await state.set_state(AddPartner.name)
    await cb.message.edit_text(
        "Добавление партнёра.\n\n"
        f"1/9. {PARTNER_FIELD_LABELS['name']}:"
    )
    await cb.answer()


_ADD_ORDER = [
    (AddPartner.name, "name", AddPartner.full_fio),
    (AddPartner.full_fio, "full_fio", AddPartner.inn),
    (AddPartner.inn, "inn", AddPartner.ogrnip),
    (AddPartner.ogrnip, "ogrnip", AddPartner.address),
    (AddPartner.address, "address", AddPartner.email),
    (AddPartner.email, "email", AddPartner.phone),
    (AddPartner.phone, "phone", AddPartner.dkk_number),
    (AddPartner.dkk_number, "dkk_number", AddPartner.dkk_date),
    (AddPartner.dkk_date, "dkk_date", None),
]


def _next_prompt(idx: int) -> str:
    if idx >= len(_ADD_ORDER):
        return ""
    field = _ADD_ORDER[idx][1]
    return f"{idx + 1}/9. {PARTNER_FIELD_LABELS[field]}:"


async def _handle_add_step(
    message: Message,
    state: FSMContext,
    field: str,
    next_state,
    idx: int,
) -> None:
    await state.update_data(**{field: message.text.strip()})
    if next_state is None:
        data = await state.get_data()
        payload = {f: data[f] for f in PARTNER_FIELDS}
        pid = await add_partner(payload)
        await state.clear()
        await message.answer(
            f"✅ Партнёр <b>{payload['name']}</b> добавлен в базу (id={pid}).",
            reply_markup=main_menu_kb(is_admin(message.from_user.id)),
        )
        return
    await state.set_state(next_state)
    await message.answer(_next_prompt(idx + 1))


def _register_add_handlers() -> None:
    for idx, (state_cls, field, next_state) in enumerate(_ADD_ORDER):
        async def handler(
            message: Message,
            state: FSMContext,
            _field=field,
            _next=next_state,
            _idx=idx,
        ) -> None:
            await _handle_add_step(message, state, _field, _next, _idx)
        router.message.register(handler, state_cls)


_register_add_handlers()
