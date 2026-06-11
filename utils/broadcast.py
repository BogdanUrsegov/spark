# utils/broadcast.py
import asyncio
import logging
from typing import List
from aiogram import Bot


logger = logging.getLogger(__name__)

async def send_message_safe(bot: Bot, user_id: int, text: str, parse_mode: str = "Markdown2", **kwargs) -> dict:
    """
    Безопасная отправка сообщения одному пользователю.
    Возвращает статус: {"ok": bool, "user_id": int, "error": str (опционально)}
    """
    try:
        await bot.send_message(user_id, text, parse_mode=parse_mode, **kwargs)
        return {"ok": True, "user_id": user_id}
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"❌ Не удалось отправить сообщение пользователю {user_id}: {error_msg}")
        return {"ok": False, "user_id": user_id, "error": error_msg}

async def broadcast(
    bot: Bot,
    user_ids: List[int],
    text: str,
    chunk_size: int = 25,        # не более ~25–28/сек
    delay_between_chunks: float = 1.0,
    **send_kwargs
) -> dict:
    """
    Рассылка сообщения списку пользователей с ограничением скорости.
    
    Возвращает: {"total": int, "success": int, "failed": int, "errors": List[str]}
    """
    total = len(user_ids)
    success = 0
    failed = 0
    errors = []

    # Разбиваем на чанки
    for i in range(0, total, chunk_size):
        chunk = user_ids[i:i + chunk_size]
        logger.info(f"📤 Отправляю чанк {i // chunk_size + 1} ({len(chunk)} получателей)...")

        # Параллельная отправка в пределах лимита
        tasks = [
            send_message_safe(bot, user_id, text, **send_kwargs)
            for user_id in chunk
        ]
        results = await asyncio.gather(*tasks)

        # Обработка результатов
        for res in results:
            if res["ok"]:
                success += 1
            else:
                failed += 1
                errors.append(res)

        # Пауза между чанками, чтобы не превысить лимит API
        if i + chunk_size < total:
            await asyncio.sleep(delay_between_chunks)

    logger.info(f"✅ Рассылка завершена: {success}/{total} успешно, {failed} ошибок.")
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "errors": errors
    }