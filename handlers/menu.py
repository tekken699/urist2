"""Главное меню: reply-кнопки + команды /start, /cancel.

Этот роутер подключается первым в bot.py, поэтому нажатия кнопок
перехватываются даже посреди FSM-сценария — пользователь может
бросить любое действие и начать заново одной кнопкой.
"""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from config import ADMIN_IDS
from database import PARTNER_FIELD_LABELS
from keyboards import (
    MAIN_BTN_ADD_PARTNER,
    MAIN_BTN_ADMIN,
    MAIN_BTN_HELP,
    MAIN_BTN_NEW_CLAIM,
    admin_menu_kb,
    claim_types_kb,
    main_menu_kb,
)
from states import AddPartner

router = Router(name="menu")


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    admin = is_admin(message.from_user.id)
    greeting = (
        "👋 <b>Бот-генератор претензий «Хлебник Франчайзинг»</b>\n\n"
        "Выберите действие на клавиатуре снизу."
    )
    if admin:
        greeting += "\n\n✅ Вы вошли как администратор."
    await message.answer(greeting, reply_markup=main_menu_kb(admin))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=main_menu_kb(is_admin(message.from_user.id)),
    )


# ---- Reply-кнопки ------------------------------------------------------------

@router.message(F.text == MAIN_BTN_NEW_CLAIM)
async def btn_new_claim(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📝 Выберите тип претензии:",
        reply_markup=claim_types_kb(),
    )


@router.message(F.text == MAIN_BTN_ADD_PARTNER)
async def btn_add_partner(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddPartner.name)
    await message.answer(
        "➕ <b>Добавление партнёра в базу.</b>\n\n"
        "Я задам 9 вопросов — отвечайте на каждый обычным сообщением.\n"
        "Если ошиблись — нажмите /cancel или просто тапните любую кнопку меню.\n\n"
        f"1/9. {PARTNER_FIELD_LABELS['name']}:"
    )


@router.message(F.text == MAIN_BTN_HELP)
async def btn_help(message: Message) -> None:
    await message.answer(
        "<b>Как пользоваться ботом</b>\n\n"
        "📝 <b>Создать претензию</b> — пошаговый мастер: выбираете тип, "
        "партнёра из базы, вводите адрес пекарни, дату Акта и список нарушений. "
        "Для типа «Пустые витрины» — ещё попросит до 4 фото витрины. "
        "В итоге бот пришлёт готовый <b>.docx</b>-файл с подставленными "
        "реквизитами, который можно сразу распечатать.\n\n"
        "➕ <b>Добавить партнёра</b> — занести нового ИП в базу, чтобы при "
        "оформлении претензий не вводить его реквизиты каждый раз вручную.\n\n"
        "🛠 <b>Админ-панель</b> (только администратор) — редактирование "
        "и удаление карточек, выгрузка базы в виде <code>.sqlite</code>-файла "
        "для бэкапа.\n\n"
        "<b>Срок устранения</b> рассчитывается автоматически: текущая дата "
        "+ 5 дней. Если попадает на выходные — переносится на ближайший "
        "понедельник.\n\n"
        "Запутались — нажмите /start, всё начнётся сначала.",
        reply_markup=main_menu_kb(is_admin(message.from_user.id)),
    )


@router.message(F.text == MAIN_BTN_ADMIN)
async def btn_admin(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта кнопка доступна только администратору.")
        return
    await state.clear()
    await message.answer("🛠 Админ-панель:", reply_markup=admin_menu_kb())
