# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN, TELEGRAM_LOG_CHANNEL_ID
from handlers import global_error_handler
from storage import create_database
from handlers import router as handlers_router
from telegram_logger import TelegramLogHandler
from admin import router as admin_router
from middlewares import BlacklistMiddleware

# Настройка базового логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=BOT_TOKEN, default=default_properties)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.update.middleware(BlacklistMiddleware(bot=bot))

async def main():
    # Подключаем Telegram-логгер
    tg_handler = TelegramLogHandler(bot=bot, chat_id=TELEGRAM_LOG_CHANNEL_ID)
    tg_handler.setLevel(logging.WARN)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d\n%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    tg_handler.setFormatter(formatter)
    logging.getLogger().addHandler(tg_handler)

    dp.errors.register(global_error_handler)
    
    # Подключаем роутеры
    dp.include_router(handlers_router)
    dp.include_router(admin_router)

    # Запуск
    await bot.delete_webhook(drop_pending_updates=True)
    await create_database()
    logger.info("Бот запущен и готов к работе.")
    await bot.send_message(TELEGRAM_LOG_CHANNEL_ID, text="✅ Бот запущен и готов к работе")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
