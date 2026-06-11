import logging
from aiogram.types import CallbackQuery
from .get_format_caption import get_format_caption


logger = logging.getLogger(__name__)


async def show_like_message_response(callback: CallbackQuery):
    """
    Редактирует сообщение с анкетой: добавляет надпись "Вы выбрали: 💬"
    и убирает кнопки.
    """
    user_id = callback.from_user.id
    logger.info(f"Showing like message response to user {user_id}")
    
    current_caption = get_format_caption(callback.message.caption)
    if not current_caption:
        logger.warning(f"No caption found for message from user {user_id}")
        return

    new_caption = f"{current_caption}\n\n<b>Вы выбрали:</b> 💬"
    await callback.message.edit_caption(
        caption=new_caption,
        reply_markup=None,
        parse_mode="HTML"
    )
    logger.debug(f"Like message response shown to user {user_id}")