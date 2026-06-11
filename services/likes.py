import html
from aiogram import Bot
from storage import save_action
from keyboards import get_view_liker_keyboard, get_pre_open_chat_keyboard
import logging
from config import TELEGRAM_LOG_CHANNEL_ID


logger = logging.getLogger(__name__)


async def process_action(bot: Bot, liker_id: int, liked_id: int, action: str = "like", message: str | None = None) -> bool:
    """
    Основная бизнес-логика лайка:
    - сохранение,
    - проверка взаимности,
    - отправка уведомлений.
    Возвращает True, если лайк взаимный.
    """
    logger.info(f"Processing {action} from user {liker_id} to user {liked_id}")
    await bot.send_message(TELEGRAM_LOG_CHANNEL_ID, f"Пользователь {liker_id} отправил {action} для {liked_id}\n\nСообщение: {message}")
    message = html.escape(message) if message else ""
    try:
        is_mutual = await save_action(liker_id, liked_id, action, message)
        logger.debug(f"Like action {action} saved from {liker_id} to {liked_id}")
        
        if action in ("like", "like_with_message"):
            logger.info(f"Mutual like check result for {liker_id} and {liked_id}: {is_mutual}")

            if is_mutual:
                logger.info(f"Mutual like detected between {liker_id} and {liked_id}")
                await _notify_mutual_like(bot, liker_id, liked_id, message)
            else:
                logger.info(f"Like from {liker_id} to {liked_id} is not mutual")
                await _notify_received_like(bot, liked_id, liker_id, message)

            return is_mutual
        return False
    except Exception as e:
        logger.exception(f"Ошибка при обработке лайка от {liker_id} к {liked_id}: {e}")
        return False


async def _notify_mutual_like(bot: Bot, user_a: int, user_b: int, message: str | None = None):
    """
    Отправляет уведомление о взаимном лайке от user_a к user_b.
    """
    logger.info(f"Sending mutual like notifications between {user_a} and {user_b}")
    message_text = f"💌 <b>Послание:</b>\n<i>{message}</i>\n\n" if message else ""
    try:
        await bot.send_message(user_a, f"<b>У тебя взаимный лайк!</b>\n\n<b><i>Узнать кто это</i></b> 👇", reply_markup=get_pre_open_chat_keyboard(user_b))
        logger.debug(f"Mutual like notification sent to user {user_a}")
    except Exception as e:
        logger.error(f"Failed to send mutual like notification to user {user_a}: {e}")
    
    try:
        await bot.send_message(user_b, f"<b>У тебя взаимный лайк!</b>\n\n{message_text}<b><i>Узнать кто это</i></b> 👇", reply_markup=get_pre_open_chat_keyboard(user_a))
        logger.debug(f"Mutual like notification sent to user {user_b}")
    except Exception as e:
        logger.error(f"Failed to send mutual like notification to user {user_b}: {e}")



async def _notify_received_like(bot: Bot, target_id: int, liker_id: int, message: str | None = None):
    logger.info(f"Sending like notification from {liker_id} to {target_id}")
    message_text = f"💌 <b>Послание:</b>\n<i>{message}</i>\n\n" if message else ""
    try:
        await bot.send_message(
            chat_id=target_id,
            text=f"💕 <b>Кто-то поставил тебе лайк!</b>\n\n{message_text}<i>Узнай кто это</i> 👇",
            reply_markup=get_view_liker_keyboard(liker_id),
            parse_mode="HTML"
        )
        logger.debug(f"Like notification sent from {liker_id} to {target_id}")
    except Exception as e:
        logger.error(f"Failed to send like notification from {liker_id} to {target_id}: {e}")