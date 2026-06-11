import logging
from aiogram import Bot, Router, F
from config import MESSAGE_PROFILE_END
from keyboards import get_fill_profile_keyboard, get_cancel_like_msg, get_back_home, get_main_menu_keyboard, get_active_keyboard
from services import *
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from states import LikeMessageStates

from storage import get_next_profile_for_user, update_user_field
from utils import send_main_menu
from viewers import *

logger = logging.getLogger(__name__)


router = Router()

@router.callback_query(F.data == "main_menu")
async def back_to_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} requested main menu")
    await callback.answer()
    await send_main_menu(
        bot=bot,
        user_id=callback.from_user.id,
        state=state,
        message=callback
    )

@router.callback_query(F.data == "show_my_profile")
async def show_my_profile(callback: CallbackQuery, bot):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} requested to view their profile")
    await callback.answer("Моя анкета")
    displayer = await ProfileDisplayer.create(bot, user_id, user_id)
    if displayer and displayer.profile:
        logger.debug(f"Profile found for user {user_id}, displaying")
        await displayer.with_stats().with_profile_keyboard().send_over(
            reply_to=callback
            )

    else:
        logger.info(f"Profile not found for user {user_id}, prompting to create")
        await bot.send_message(
            chat_id=user_id,
            text="⚠️ <b>Ваш профиль не найден</b>\n\n<i>Пожалуйста, заполните анкету</i>",
            reply_markup=get_fill_profile_keyboard()
        )

@router.callback_query(F.data == "view_profiles")
async def handle_view_profiles(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} requested to view profiles")
    await callback.answer("Загрузка анкеты...")
    # await handle_view_profiles_request(bot, callback)
    await update_user_field(user_id, "is_active", 1)
    next_profile = await get_next_profile_for_user(user_id)
    displayer = await ProfileDisplayer.create(bot, callback.from_user.id, next_profile)

    if displayer and displayer.profile:
        logger.debug(f"Found profile for user {user_id} to view")
        await displayer.with_actions_keyboard().send_over(
            reply_to=callback
        )
    else:
        logger.info(f"No profiles available for user {user_id} to view")
        await bot.send_message(
            chat_id=user_id,
            text=MESSAGE_PROFILE_END,
            reply_markup=get_back_home()
        )
    
@router.callback_query(F.data.startswith("like:"))
async def handle_like(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])
    logger.info(f"User {user_id} liked profile {target_id}")

    # Подтверждение нажатия
    await callback.answer("Вы выбрали: ❤️")

    # Редактирование текущего сообщения
    await show_like_response(callback)

    # Обработка бизнес-логики лайка
    is_mutual = await process_action(bot, user_id, target_id)
    if not is_mutual:
        logger.debug(f"Like from {user_id} to {target_id} is not mutual, showing next profile")
        success = await update_user_field(user_id, "is_active", 1)
        next_profile = await get_next_profile_for_user(user_id)
        displayer = await ProfileDisplayer.create(bot, callback.from_user.id, next_profile)

        if displayer and displayer.profile:
            await displayer.with_actions_keyboard().send_over(
                reply_to=callback,
                delete_previous=False,
                remove_buttons_only=True,
                is_reply=False
            )
        else:
            logger.info(f"No more profiles available for user {user_id}")
            await bot.send_message(
                chat_id=user_id,
                text=MESSAGE_PROFILE_END,
                reply_markup=get_back_home()
            )
    else:
        logger.info(f"Mutual like detected between {user_id} and {target_id}")

@router.callback_query(F.data.startswith("like_msg:"))
async def handle_like_msg(callback: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])
    logger.info(f"User {user_id} wants to send a message to {target_id}")
    
    await callback.answer("Вы выбрали: 💬")

    await state.set_state(LikeMessageStates.message)
    await state.update_data(target_id=target_id)
    
    await show_like_message_response(callback)

    message = await callback.message.answer(
        "💌 <i><b>Отправь <u>текстовое</u> послание человеку</b></i>",
        reply_markup=get_cancel_like_msg(target_id)
    )

    await state.update_data(message_id=message.message_id)

@router.callback_query(F.data.startswith("cancel_like_msg"))
async def handle_cancel_like_msg(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])
    await callback.answer("Отмена отправки сообщения")
    await show_cancel_like_message_response(callback)
    is_mutual = await process_action(bot, user_id, target_id)

    if not is_mutual:
        user_id = callback.from_user.id

        success = await update_user_field(user_id, "is_active", 1)
        next_profile = await get_next_profile_for_user(user_id)
        displayer = await ProfileDisplayer.create(bot, callback.from_user.id, next_profile)

        if displayer and displayer.profile:
            await displayer.with_actions_keyboard().send_over(
                reply_to=callback,
                delete_previous=False,
                remove_buttons_only=True,
                is_reply=False
            )
        else:
            await bot.send_message( 
                chat_id=user_id,
                text=MESSAGE_PROFILE_END,
                reply_markup=get_back_home()
            )

@router.callback_query(F.data.startswith("dislike:"))
async def handle_dislike(callback: CallbackQuery, bot: Bot):
    await callback.answer("Вы выбрали: 👎")
    target_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    await show_dislike_response(callback)
    await process_action(bot, user_id, target_id, "dislike")

    success = await update_user_field(user_id, "is_active", 1)
    next_profile = await get_next_profile_for_user(user_id)
    displayer = await ProfileDisplayer.create(bot, callback.from_user.id, next_profile)

    if displayer and displayer.profile:
        await displayer.with_actions_keyboard().send_over(
            reply_to=callback,
            delete_previous=False,
            remove_buttons_only=True,
            is_reply=False
        )
    else:
        await bot.send_message( 
            chat_id=user_id,
            text=MESSAGE_PROFILE_END,
            reply_markup=get_back_home()
        )

@router.callback_query(F.data.startswith("view_liker"))
async def handle_find_out_who(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    _, liker_id = callback.data.split(":")
    logger.info(f"User {user_id} wants to see who liked them: {liker_id}")
    
    await callback.answer("Лайк получен!")

    displayer = await ProfileDisplayer.create(bot, callback.from_user.id, int(liker_id))

    if displayer and displayer.profile:
        logger.debug(f"Showing liker profile {liker_id} to user {user_id}")
        await displayer.with_actions_keyboard().send_over(
            reply_to=callback,
            delete_previous=False,
            remove_buttons_only=True,
            is_reply=True
        )
    else:
        logger.warning(f"Liker profile {liker_id} not available for user {user_id}")
        await callback.message.answer("<b>Анкета недоступна.</b>")

@router.callback_query(F.data.startswith("open_chat"))
async def handle_open_chat(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    _, liker_id = callback.data.split(":")
    logger.info(f"User {user_id} opened chat with mutual like user {liker_id}")
    
    await callback.answer("Взаимный лайк!")

    username = (await bot.get_chat(int(liker_id))).username
    if not username:
        await bot.send_message(liker_id, "<b><u>Важно</u></b>\n\nПожалуйста, укажите свой <b>юзернейм</b> в настройках <u>Telegram</u>.\n\n<i>Это позволит пользователям, которым вы поставили лайк, написать <b>вам</b></i> 💬")
    displayer = await ProfileDisplayer.create(bot, callback.from_user.id, int(liker_id))

    if displayer and displayer.profile:
        logger.debug(f"Showing mutual like profile {liker_id} to user {user_id}")
        await displayer.with_open_chat_keyboard(username).send_over(
            reply_to=callback,
            delete_previous=False,
            remove_buttons_only=False,
            is_reply=True
        )
    else:
        logger.warning(f"Mutual like profile {liker_id} not available for user {user_id}")
        await callback.message.answer("<b>Анкета недоступна.</b>")

    await callback.message.answer("👀 <b>Готов продолжить смотреть анкеты?</b>", reply_markup=get_main_menu_keyboard())

@router.callback_query(F.data.startswith("update_username:"))
async def handle_update_username(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])
    logger.info(f"User {user_id} requested to update profile for {target_id}")
    username = (await bot.get_chat(target_id)).username
    print(f"Юзернйем: {username}")
    if username:
        await callback.answer("Обновление анкеты")
        displayer = await ProfileDisplayer.create(bot, callback.from_user.id, target_id)

        if displayer and displayer.profile:
            await displayer.with_open_chat_keyboard(username).edit(
                callback,
                update_caption=False,
                update_keyboard=True
            )

    else:
        await callback.answer(
            "⚠️ Юзернейм не найден\n"
            "Пользователь не указал юзернейм в Telegram.\n"
            "🔄 Попробуйте позже — данные могут обновиться!",
            show_alert=True
        )
        
"""
@router.callback_query(F.data == "view_profiles")
async def handle_view_profiles(callback: CallbackQuery, bot: Bot):
    await callback.answer("Загрузка анкеты")  # чтобы убрать "часики" на кнопке
        user_id = callback.from_user.id

        if not await is_profile_complete(user_id):
            await callback.message.answer(
                "❗ Сначала заполни свою анкету",
                reply_markup=get_fill_profile_keyboard()
            )
            return
        
        await show_profile(bot, user_id, callback)
"""