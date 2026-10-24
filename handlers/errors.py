import logging
import os
from datetime import datetime

from aiogram.types import ErrorEvent, User

logger = logging.getLogger(__name__)


def extract_user_info(update) -> str:
    """Extract minimal user metadata for debugging."""
    user: User | None = None
    if update:
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        elif update.my_chat_member:
            user = update.my_chat_member.from_user

    if user:
        username = f"@{user.username}" if user.username else ""
        return f"ID: {user.id} {username} ({user.full_name})"
    return "N/A"


async def global_error_handler(event: ErrorEvent):
    exc = event.exception
    tb = exc.__traceback__

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

    update = event.update
    user_info = extract_user_info(update)
    update_type = "N/A"
    payload_summary = ""

    # Avoid copying message bodies or full callback payloads into the log channel.
    if update:
        if update.message:
            update_type = "message"
            text_value = update.message.text or update.message.caption or ""
            payload_summary = f"text/caption length: {len(text_value)}"
        elif update.callback_query:
            update_type = "callback"
            callback_data = update.callback_query.data or ""
            payload_summary = f"callback action: {callback_data.partition(':')[0][:80]}"
        elif update.poll:
            update_type = "poll"

    error_summary = (
        f"🔴 <b>{type(exc).__name__}</b>: {type(exc).__name__}\n\n"
        f"👤 Пользователь: {user_info}\n"
        f"📦 Апдейт: {update_type} | {payload_summary}\n"
        f"📁 Файл: {filename} (строка {lineno})\n"
        f"⚡ Функция: {funcname}\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📂 Путь: {full_path}"
    )
    logger.error(error_summary)
