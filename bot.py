import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import admin, claims, menu


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if BOT_TOKEN in ("", "PUT_YOUR_TOKEN_HERE"):
        raise RuntimeError(
            "BOT_TOKEN не задан. Установите переменную окружения BOT_TOKEN."
        )

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    # menu подключается первым — иначе reply-кнопки не будут перехватываться
    # в активных FSM-состояниях (admin/claims).
    dp.include_router(menu.router)
    dp.include_router(admin.router)
    dp.include_router(claims.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
