import logging
from aiogram.types import CallbackQuery
from .get_format_caption import get_format_caption


logger = logging.getLogger(__name__)


async def show_dislike_response(callback: CallbackQuery):
    """
    Редактирует сообщение с анкетой: добавляет надпись "Вы выбрали: 👎"
    и убирает кнопки.
    """
    user_id = callback.from_user.id
    logger.info(f"Showing dislike response to user {user_id}")
    
    current_text = callback.message.caption or callback.message.text
    if not current_text:
        logger.warning("No profile text found for user %s", user_id)
        return

    current_caption = get_format_caption(current_text)
    if not current_caption:
        logger.warning(f"No caption found for message from user {user_id}")
        return

    new_caption = f"{current_caption}\n\n<b>Вы выбрали:</b> 👎"
    if callback.message.text is not None:
        await callback.message.edit_text(
            text=new_caption,
            reply_markup=None,
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_caption(
            caption=new_caption,
            reply_markup=None,
            parse_mode="HTML",
        )
    logger.debug(f"Dislike response shown to user {user_id}")