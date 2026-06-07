# Bot-генератор претензий «Хлебник Франчайзинг»

Telegram-бот на Aiogram 3.x для юристов франчайзинговой сети. Хранит данные
партнёров в локальном SQLite, генерирует претензии в формате `.docx` из
шаблонов docxtpl и отдаёт файл сразу в чат.

## Быстрый старт

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Создаём docx-шаблоны (с тегами Jinja2 для docxtpl)
python create_templates.py

# 2. Запускаем бота
export BOT_TOKEN="123456:AA..."
export ADMIN_IDS="111111111,222222222"
python bot.py
```

## Структура

```
.
├── bot.py                 — точка входа, Dispatcher + роутеры
├── config.py              — токен, ADMIN_IDS, пути, дедлайн
├── database.py            — aiosqlite, CRUD по партнёрам
├── keyboards.py           — inline-клавиатуры + пагинация
├── states.py              — FSM-состояния
├── utils.py               — даты, расчёт срока устранения
├── create_templates.py    — воссоздаёт три .docx шаблона из PDF-образцов
├── handlers/
│   ├── start.py           — /start, /cancel
│   ├── claims.py          — мастер генерации претензии
│   └── admin.py           — /admin: CRUD по партнёрам, дамп БД
└── templates/             — oot.docx, tech.docx, coffee.docx
```

## Логика дедлайна

`utils.calc_deadline` прибавляет 5 календарных дней к дате документа.
Если последний день — суббота или воскресенье, дедлайн переносится
на ближайший понедельник.

## Типы претензий

| Код      | Шаблон       | Назначение                          |
|----------|--------------|-------------------------------------|
| `oot`    | `oot.docx`   | Общая претензия по выездной проверке |
| `tech`   | `tech.docx`  | Технологическая проверка             |
| `coffee` | `coffee.docx`| Кофейный аудит (уведомление)         |
| `empty`  | `oot.docx`   | «Пустые витрины» — использует базовый шаблон ООТ |

## Переменные шаблонов

Каждый docx содержит теги Jinja2, которые подставляет docxtpl:

| Переменная        | Источник                          |
|-------------------|-----------------------------------|
| `full_fio`        | БД (поле партнёра)                |
| `inn`, `ogrnip`   | БД                                |
| `address`         | БД (юр. адрес ИП)                 |
| `email`, `phone`  | БД                                |
| `dkk_number`      | БД                                |
| `dkk_date`        | БД                                |
| `bakery_address`  | Ввод юриста (адрес пекарни)       |
| `act_date`        | Ввод юриста (дата Акта/Отчёта)    |
| `inspection_date` | = `act_date`                      |
| `doc_date`        | Текущая дата                      |
| `deadline_date`   | Рассчитывается (5 дней + перенос с выходных) |
| `violations`      | Список строк, рендерится в цикле  |
```
