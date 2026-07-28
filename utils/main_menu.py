import logging
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from storage import is_profile_complete, get_user_field
from keyboards import get_main_menu_keyboard, get_fill_profile_keyboard


async def send_main_menu(
    bot: Bot,
    user_id: int,
    state: FSMContext,
    message: Message | CallbackQuery = None
) -> None:
    """
    Отправляет приветственное сообщение в зависимости от статуса профиля.
    Может использоваться из команды /start и из коллбэков.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Sending main menu to user {user_id}")
    
    if isinstance(message, CallbackQuery):
        try:
            await message.message.delete()
        except TelegramBadRequest as e:
            if "can't be deleted for everyone" in e.message:
                logger.warning(e.message)
    if await is_profile_complete(user_id):
        name = await get_user_field(user_id, "name") or "друг"
        text = (
            f"<b>👋 С возвращением, {name}!</b>\n\n"
            "Хочешь найти новые знакомства?"
        )
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        logger.debug(f"Main menu sent to user {user_id}, profile is complete")
    else:
        text = (
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Найди новых друзей и интересных людей рядом с тобой\n\n"
            "<b><i>Создай профиль — и пусть начнётся знакомство! ✨</i></b>😉"
        )
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_fill_profile_keyboard()
        )
        logger.debug(f"Main menu sent to user {user_id}, profile is incomplete")