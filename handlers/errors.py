# handlers/errors.py
import logging
import os
from aiogram.types import ErrorEvent, User
from datetime import datetime

logger = logging.getLogger(__name__)

def extract_user_info(update) -> str:
    """Извлекает информацию о пользователе из апдейта."""
    user: User | None = None
    if update:
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        elif update.my_chat_member:
            user = update.my_chat_member.from_user
        # добавьте другие типы апдейтов при необходимости

    if user:
        username = f"@{user.username}" if user.username else ""
        return f"ID: {user.id} {username} ({user.full_name})"
    return "N/A"

async def global_error_handler(event: ErrorEvent):
    exc = event.exception
    tb = exc.__traceback__

    # Основная информация об ошибке
    filename = "unknown"
    lineno = 0
    funcname = "unknown"
    full_path = "unknown"

    if tb is not None:
        while tb.tb_next:
            tb = tb.tb_next
        full_path = tb.tb_frame.f_code.co_filename
        filename = os.path.basename(full_path)
        lineno = tb.tb_lineno
        funcname = tb.tb_frame.f_code.co_name

    # Доп. контекст
    update = event.update
    user_info = extract_user_info(update)
    update_type = "N/A"
    payload = ""

    if update:
        if update.message:
            update_type = "message"
            payload = f"text: {update.message.text!r}"
        elif update.callback_query:
            update_type = "callback"
            payload = f"data: {update.callback_query.data!r}"
        elif update.poll:
            update_type = "poll"
        # и т.д.

    # Собираем краткий, но насыщенный отчёт
    error_summary = (
        f"🔴 <b>{type(exc).__name__}</b>: {exc}\n\n"
        f"👤 Пользователь: {user_info}\n"
        f"📦 Апдейт: {update_type} | {payload[:3800]}\n"
        f"📁 Файл: {filename} (строка {lineno})\n"
        f"⚡ Функция: {funcname}\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        # Раскомментируйте, если нужно:
        f"\n📂 Полный путь: {full_path}"
    )

    # Логируем как ERROR → в консоль и в Telegram
    logger.error(error_summary)