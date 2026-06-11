import logging
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


async def show_cancel_like_message_response(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"Showing cancel like message response to user {user_id}")
    
    current_text = callback.message.text
    if not current_text:
        logger.warning(f"No text found for message from user {user_id}")
        return

    new_text = f"<b><i>Вы отменили отправку сообщения</i></b> ❌"
    await callback.message.edit_text(
        text=new_text,
        reply_markup=None,
        parse_mode="HTML"
    )
    logger.debug(f"Cancel like message response shown to user {user_id}")