from aiogram import Bot
from config import MESSAGE_PROFILE_END
from keyboards import get_actions_keyboard, get_back_home
from storage import get_next_profile_for_user
from aiogram.types import CallbackQuery


async def show_profile(bot: Bot, chat_id: int, message = None):
    next_profile = await get_next_profile_for_user(chat_id)

    if next_profile:
        caption = (
        f"👤 <b>{next_profile['name']}, {next_profile['age']}</b>\n"
        f"{next_profile['gender']}\n\n"
        f"{next_profile['description']}"
        )
        if isinstance(message, CallbackQuery):
            await message.message.delete()
        await bot.send_photo(
            chat_id=chat_id,
            photo=next_profile['photo_id'],
            caption=caption,
            reply_markup=get_actions_keyboard(next_profile['user_id'])
        )
        
    else:
        await bot.send_message(chat_id, MESSAGE_PROFILE_END, reply_markup=get_back_home())

async def show_find_out_who(target_id: int, bot: Bot, message = None):
    next_profile = await get_next_profile_for_user(target_id)

    if next_profile:
        caption = (
        f"👤 <b>{next_profile['name']}, {next_profile['age']}</b>\n"
        f"{next_profile['gender']}\n\n"
        f"{next_profile['description']}"
        )
        if isinstance(message, CallbackQuery):
            await message.message.delete()
        await bot.send_photo(
            chat_id=target_id,
            photo=next_profile['photo_id'],
            caption=caption,
            reply_markup=get_actions_keyboard(next_profile['user_id'])
        )