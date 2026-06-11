# services/profile_viewing.py
import logging
from config import MESSAGE_PROFILE_END
from keyboards import get_fill_profile_keyboard, get_back_home
from viewers import ProfileDisplayer

logger = logging.getLogger(__name__)


async def handle_view_profiles_request(bot, msg, delete_prev_msg=True, delete_prev_btn=False) -> None:
    """
    Обрабатывает запрос на просмотр анкет.
    Полностью инкапсулирует логику:
    - проверка профиля,
    - загрузка следующей анкеты,
    - отображение или сообщение об отсутствии анкет.
    """
    user_id = msg.from_user.id
    logger.info(f"User {user_id} requested to view profiles")
    
    displayer = await ProfileDisplayer.for_next_profile(bot, user_id)
    if displayer:
        logger.debug(f"Found next profile for user {user_id}")
        success = await (
            displayer
            .with_actions_keyboard()
            .send(delete_prev_msg=delete_prev_msg, delete_prev_btn=delete_prev_btn, reply_to=msg)
        )
    else:
        logger.info(f"No available profiles for user {user_id}")
        success = False

    if not success:
        logger.info(f"No profiles available for user {user_id}, sending message")
        await bot.send_message(
            chat_id=user_id,
            text=MESSAGE_PROFILE_END,
            reply_markup=get_back_home()
        )

async def handle_show_my_profile_request(bot, msg) -> None:
    user_id = msg.from_user.id
    logger.info(f"User {user_id} requested to view their own profile")
    
    displayer = await ProfileDisplayer.create(bot, user_id, target_id=user_id)
    if displayer and displayer.profile:
        logger.debug(f"Profile found for user {user_id}, displaying")
        await displayer.with_stats().with_profile_keyboard().send_over(
            reply_to=msg
            )

    else:
        logger.info(f"Profile not found for user {user_id}, prompting to create")
        await bot.send_message(
            chat_id=user_id,
            text="⚠️ <b>Ваш профиль не найден</b>\n\n<i>Пожалуйста, заполните анкету</i>",
            reply_markup=get_fill_profile_keyboard()
        )