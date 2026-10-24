import html
import logging

from aiogram import Bot

from keyboards import get_view_liker_keyboard, get_pre_open_chat_keyboard
from storage import save_action

logger = logging.getLogger(__name__)


async def process_action(
    bot: Bot,
    liker_id: int,
    liked_id: int,
    action: str = "like",
    message: str | None = None,
) -> bool:
    """Persist an action and notify users without forwarding private messages to logs."""
    if liker_id == liked_id:
        logger.warning("Ignoring self-directed profile action.")
        return False

    safe_message = html.escape(message) if message else None
    try:
        is_mutual = await save_action(liker_id, liked_id, action, safe_message)

        if action in ("like", "like_with_message"):
            if is_mutual:
                await _notify_mutual_like(bot, liker_id, liked_id, safe_message)
            else:
                await _notify_received_like(bot, liked_id, liker_id, safe_message)
            return is_mutual

        return False
    except Exception:
        # Do not log the message body: it may contain personal information.
        logger.exception("Could not process a profile action.")
        return False


async def _notify_mutual_like(
    bot: Bot, user_a: int, user_b: int, message: str | None = None
) -> None:
    message_text = f"💌 <b>Послание:</b>\n<i>{message}</i>\n\n" if message else ""
    try:
        await bot.send_message(
            user_a,
            "<b>У тебя взаимный лайк!</b>\n\n"
            "<b><i>Узнать кто это</i></b> 👇",
            reply_markup=get_pre_open_chat_keyboard(user_b),
        )
    except Exception:
        logger.warning("Could not send a mutual-like notification.")

    try:
        await bot.send_message(
            user_b,
            f"<b>У тебя взаимный лайк!</b>\n\n{message_text}"
            "<b><i>Узнать кто это</i></b> 👇",
            reply_markup=get_pre_open_chat_keyboard(user_a),
        )
    except Exception:
        logger.warning("Could not send a mutual-like notification.")


async def _notify_received_like(
    bot: Bot, target_id: int, liker_id: int, message: str | None = None
) -> None:
    message_text = f"💌 <b>Послание:</b>\n<i>{message}</i>\n\n" if message else ""
    try:
        await bot.send_message(
            chat_id=target_id,
            text=(
                "💕 <b>Кто-то поставил тебе лайк!</b>\n\n"
                f"{message_text}<i>Узнай кто это</i> 👇"
            ),
            reply_markup=get_view_liker_keyboard(liker_id),
            parse_mode="HTML",
        )
    except Exception:
        logger.warning("Could not send a like notification.")
