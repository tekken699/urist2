import io
from datetime import date

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message, User
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from config import ADMIN_IDS, CLAIM_TYPES, MAX_EMPTY_PHOTOS, TEMPLATES_DIR, TEMPLATE_FOR_TYPE
from database import get_partner
from keyboards import claim_types_kb, main_menu_kb, partners_kb, photos_kb
from states import ClaimFlow
from utils import calc_deadline, format_ru_date, normalize_violations, parse_ru_date

router = Router(name="claims")


# ---- Выбор типа претензии ----------------------------------------------------

@router.callback_query(F.data == "claim:cancel")
async def cb_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("Отменено. /start — начать заново.")
    await cb.answer()


@router.callback_query(F.data.startswith("claim:"))
async def cb_pick_claim(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":", 1)[1]
    if code not in CLAIM_TYPES:
        await cb.answer("Неизвестный тип", show_alert=True)
        return
    await state.set_state(ClaimFlow.choosing_partner)
    await state.update_data(claim_code=code, query="")
    kb = await partners_kb(code, page=0)
    await cb.message.edit_text(
        f"Тип: <b>{CLAIM_TYPES[code]}</b>\nВыберите партнёра:",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(F.data.startswith("page:"))
async def cb_page(cb: CallbackQuery, state: FSMContext) -> None:
    _, code, page = cb.data.split(":")
    data = await state.get_data()
    kb = await partners_kb(code, page=int(page), query=data.get("query", ""))
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


# ---- Поиск партнёра ----------------------------------------------------------

@router.callback_query(F.data.startswith("search:"))
async def cb_search(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":", 1)[1]
    await state.update_data(claim_code=code)
    await state.set_state(ClaimFlow.searching_partner)
    await cb.message.edit_text(
        "Введите часть фамилии, ИНН или названия — найду в базе.\n"
        "/cancel — отмена."
    )
    await cb.answer()


@router.message(ClaimFlow.searching_partner)
async def msg_search(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    data = await state.get_data()
    code = data["claim_code"]
    await state.update_data(query=query)
    await state.set_state(ClaimFlow.choosing_partner)
    kb = await partners_kb(code, page=0, query=query)
    await message.answer(
        f"Результаты по запросу: <i>{query}</i>",
        reply_markup=kb,
    )


# ---- Выбран партнёр — спрашиваем динамические данные ------------------------

@router.callback_query(F.data.startswith("pick:"))
async def cb_pick_partner(cb: CallbackQuery, state: FSMContext) -> None:
    _, code, partner_id = cb.data.split(":")
    partner = await get_partner(int(partner_id))
    if not partner:
        await cb.answer("Партнёр не найден", show_alert=True)
        return
    await state.update_data(partner_id=partner.id, claim_code=code)
    await state.set_state(ClaimFlow.entering_bakery_address)
    await cb.message.edit_text(
        f"Партнёр: <b>{partner.name}</b>\n"
        f"Тип: <b>{CLAIM_TYPES[code]}</b>\n\n"
        "Введите <b>адрес пекарни</b>, где зафиксированы нарушения "
        "(например: «г. Санкт-Петербург, ул. Садовая, д. 36»):"
    )
    await cb.answer()


@router.message(ClaimFlow.entering_bakery_address)
async def msg_bakery_address(message: Message, state: FSMContext) -> None:
    await state.update_data(bakery_address=message.text.strip())
    await state.set_state(ClaimFlow.entering_act_date)
    await message.answer(
        "Введите <b>дату Акта фиксации нарушений / Отчёта по проверке</b>\n"
        "в формате ДД.ММ.ГГГГ (например: 21.12.2025):"
    )


@router.message(ClaimFlow.entering_act_date)
async def msg_act_date(message: Message, state: FSMContext) -> None:
    try:
        act_date = parse_ru_date(message.text)
    except ValueError as e:
        await message.answer(f"❗ {e}\nПовторите ввод даты в формате ДД.ММ.ГГГГ:")
        return
    await state.update_data(act_date=format_ru_date(act_date))
    await state.set_state(ClaimFlow.entering_violations)
    await message.answer(
        "Введите <b>список нарушений</b>. Каждое нарушение — с новой строки.\n"
        "Нумерацию проставит сам бот."
    )


@router.message(ClaimFlow.entering_violations)
async def msg_violations(message: Message, state: FSMContext) -> None:
    violations = normalize_violations(message.text or "")
    if not violations:
        await message.answer("❗ Список пустой. Введите хотя бы одно нарушение.")
        return

    data = await state.get_data()
    await state.update_data(violations=violations)

    # Для "Пустые витрины" — дополнительный шаг загрузки фото.
    if data["claim_code"] == "empty":
        await state.update_data(photos=[])
        await state.set_state(ClaimFlow.uploading_photos)
        await message.answer(
            f"Прикрепите до {MAX_EMPTY_PHOTOS} фото витрины "
            "(каждое отдельным сообщением).\n"
            "Когда закончите — нажмите «Готово».",
            reply_markup=photos_kb(0),
        )
        return

    await _render_and_send(
        message, state, message.bot, message.chat.id, message.from_user.id,
    )


# ---- Сбор фото для "Пустые витрины" -----------------------------------------

@router.message(ClaimFlow.uploading_photos, F.photo)
async def msg_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos: list[str] = data.get("photos", [])
    if len(photos) >= MAX_EMPTY_PHOTOS:
        await message.answer(
            f"Уже {MAX_EMPTY_PHOTOS} фото — этого достаточно. "
            "Нажмите «Готово»."
        )
        return
    # message.photo — список PhotoSize от меньшей к большей; берём самую большую.
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(
        f"📷 Загружено {len(photos)}/{MAX_EMPTY_PHOTOS}.",
        reply_markup=photos_kb(len(photos)),
    )


@router.message(ClaimFlow.uploading_photos)
async def msg_photo_wrong(message: Message) -> None:
    await message.answer(
        "Пришлите фото изображением (📎 → Photo). "
        "Документы/файлы не подойдут — Telegram сжимает их по-другому."
    )


@router.callback_query(F.data == "photos:done", ClaimFlow.uploading_photos)
async def cb_photos_done(cb: CallbackQuery, state: FSMContext) -> None:
    # Уберём клавиатуру у сообщения с кнопкой, чтобы не нажимали повторно.
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _render_and_send(
        cb.message, state, cb.bot, cb.message.chat.id, cb.from_user.id,
    )
    await cb.answer()


# ---- Сборка и отправка готового .docx ---------------------------------------

async def _render_and_send(
    message: Message,
    state: FSMContext,
    bot: Bot,
    chat_id: int,
    user_id: int,
) -> None:
    data = await state.get_data()
    partner = await get_partner(data["partner_id"])
    if not partner:
        await state.clear()
        await bot.send_message(chat_id, "Партнёр пропал из базы. /start — заново.")
        return

    today = date.today()
    deadline = calc_deadline(today)

    context = {
        "full_fio": partner.full_fio,
        "name": partner.name,
        "inn": partner.inn,
        "ogrnip": partner.ogrnip,
        "address": partner.address,
        "email": partner.email,
        "phone": partner.phone,
        "dkk_number": partner.dkk_number,
        "dkk_date": partner.dkk_date,
        "bakery_address": data["bakery_address"],
        "act_date": data["act_date"],
        "inspection_date": data["act_date"],
        "doc_date": format_ru_date(today),
        "deadline_date": format_ru_date(deadline),
        "violations": data["violations"],
    }

    code = data["claim_code"]
    tpl_path = TEMPLATES_DIR / TEMPLATE_FOR_TYPE[code]
    if not tpl_path.exists():
        await state.clear()
        await bot.send_message(
            chat_id,
            f"❗ Шаблон {tpl_path.name} не найден.\n"
            f"Запустите: python create_templates.py",
        )
        return

    tpl = DocxTemplate(str(tpl_path))

    # Для "Пустые витрины" подкачиваем фото из Telegram и вставляем их в шаблон.
    photos_uploaded = 0
    if code == "empty":
        photo_ids: list[str] = data.get("photos", [])
        photos_uploaded = len(photo_ids)
        for i in range(MAX_EMPTY_PHOTOS):
            key = f"photo{i + 1}"
            if i < photos_uploaded:
                buf = await bot.download(photo_ids[i])
                context[key] = InlineImage(tpl, buf, width=Mm(75))
            else:
                context[key] = ""

    tpl.render(context)
    out = io.BytesIO()
    tpl.save(out)
    out.seek(0)

    fname = (
        f"Претензия_{code}_{partner.name.replace(' ', '_')}_"
        f"{format_ru_date(today)}.docx"
    )
    caption = (
        f"✅ Готово.\n"
        f"Тип: <b>{CLAIM_TYPES[code]}</b>\n"
        f"Партнёр: <b>{partner.name}</b>\n"
        f"Дата документа: {format_ru_date(today)}\n"
        f"Срок устранения: <b>{format_ru_date(deadline)}</b>\n"
        f"Нарушений: {len(data['violations'])}"
    )
    if code == "empty":
        caption += f"\nФото: {photos_uploaded}/{MAX_EMPTY_PHOTOS}"

    await bot.send_document(
        chat_id,
        BufferedInputFile(out.read(), filename=fname),
        caption=caption,
    )
    await state.clear()
    await bot.send_message(
        chat_id,
        "Готово ✅ Выберите следующее действие на клавиатуре.",
        reply_markup=main_menu_kb(user_id in ADMIN_IDS),
    )
