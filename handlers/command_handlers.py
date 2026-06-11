# handlers/command_handlers.py

from aiogram import Bot, Router, types
from aiogram.filters import Command
from services import handle_show_my_profile_request
from storage import delete_user_profile
from utils import send_main_menu
from aiogram.fsm.context import FSMContext


# Создаём отдельный роутер для ко манд 
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    """
    Обработчик команды /start.
    """
    await state.clear()
    if message.chat.type != "private":
        return  # Игнорируем команды в группах
   
    await send_main_menu(
        bot=bot,
        user_id=message.from_user.id,
        state=state,
        message=message
    )

@router.message(Command("profile"))
async def cmd_profile(message: types.Message, bot: Bot):
    await handle_show_my_profile_request(bot, message)

@router.message(Command("support"))
async def cmd_support(message: types.Message):
    await message.answer("🧑‍💻 <b>Обратитесь в поддержку @ulshpg</b>")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    Обработчик команды /help.
    """
    await message.answer(
        text="🛠️ <b>Доступные команды:</b>\n"
             "/start — начать диалог"
    )

@router.message(Command(""))
async def delete_my_profile(message: types.Message):
    deleted = await delete_user_profile(message.from_user.id)
    if deleted:
        await message.answer("✅ Ваш профиль удалён. Можете заполнить анкету заново!")
    else:
        await message.answer("⚠️ Профиль не найден.")