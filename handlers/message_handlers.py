from aiogram import Bot, Router, F
from config import MESSAGE_PROFILE_END
from services import *
from states import LikeMessageStates
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from storage import get_next_profile_for_user, update_user_field
from utils import contains_forbidden_content
from viewers import *
import logging


logger = logging.getLogger(__name__)

router = Router()

@router.message(LikeMessageStates.message)
async def handle_like_message(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    data = await state.get_data()

    message_text = message.text
    if message_text:
        if len(message_text) > 2000:
            logger.warning(f"Message from user {user_id} is too long: {len(message_text)} chars")
            await message.answer(
            "<b><i>ℹ️ Сократи послание</i></b>"
        )
        else:
            if contains_forbidden_content(message_text):
                logger.warning(f"Message from user {user_id} contains forbidden content")
                await message.answer(
                "<b><i>ℹ️ Послание не должно содержать символ '@' или ссылки</i></b>"
            )
            else:
                message_id = data.get("message_id")

                if message_id:
                    try:
                        await bot.edit_message_reply_markup(
                            chat_id=message.chat.id,
                            message_id=message_id,
                            reply_markup=None
                        )
                    except Exception as e:
                        logger.exception(f"Ошибка при удалении клавиатуры при отправке сообщения от {user_id}: {e}")
                
                target_id = data.get("target_id")
                logger.info(f"User {user_id} sending message to {target_id}: {message_text}")
                await state.clear()

                is_mutual = await process_action(bot, user_id, target_id, "like_with_message", message_text)

                #TODO: не отправилось 'сообщение отправлено' при отправке сообщения, исправить
                if not is_mutual:
                    await message.answer("💌 <i><b>Сообщение отправлено</b></i>")
                    logger.info(f"Message sent from {user_id} to {target_id}")

                    success = await update_user_field(user_id, "is_active", 1)
                    next_profile = await get_next_profile_for_user(user_id)
                    displayer = await ProfileDisplayer.create(bot, user_id, next_profile)

                    if displayer and displayer.profile:
                        await displayer.with_actions_keyboard().send_over(
                            reply_to=message,
                            delete_previous=False,
                            remove_buttons_only=False,
                            is_reply=False
                        )
                    else:
                        logger.info(f"No more profiles available for user {user_id}")
                        await message.answer(MESSAGE_PROFILE_END)
    else:
        logger.warning(f"User {user_id} sent non-text message when text was expected")
        await message.answer("<b><i>ℹ️ Сообщение должно быть текстом</i></b>")