# telegram_logger.py
import logging
import asyncio
from aiogram import Bot

class TelegramLogHandler(logging.Handler):
    def __init__(self, bot: Bot, chat_id: int):
        super().__init__()
        self.bot = bot
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        # Обрезаем, если слишком длинное сообщение
        if len(log_entry) > 4096:
            log_entry = log_entry[:4093] + "..."
        # Отправляем в фоне
        try:
            asyncio.create_task(self._safe_send(log_entry))
        except RuntimeError:
            # Если цикл событий не запущен — просто игнорируем
            pass

    async def _safe_send(self, text: str):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            # Не логгируем ошибку в тот же канал — иначе рекурсия
            print(f"[TelegramLogHandler ERROR]: {e}")