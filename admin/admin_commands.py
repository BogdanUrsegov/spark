from aiogram import Bot, Router, types
from aiogram.filters import Command
from config import ADMIN_ID, PATH_DB
from storage import (
    delete_user_profile,
    add_to_blacklist,
    get_all_user_ids,
    get_total_users_count,
    get_blacklisted_users_count,
    get_users_by_gender,
    remove_from_blacklist
)
from aiogram.types import BufferedInputFile

router = Router()

@router.message(Command("ban_user"))
async def ban_user(message: types.Message, bot: Bot):
    """
    Команда для администратора: бан пользователя.
    Получает аргументом ид человека и удаляет профиль с помощью await delete_user_profile(user_id)
    и добавляет в черный список в базе данных.
    """
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора для выполнения этой команды.")
        return
    
    try:
        command_args = message.text.split()
        if len(command_args) != 2:
            await message.answer("❌ Неверный формат команды. Используйте: /ban_user <user_id>")
            return
        
        user_id = int(command_args[1])
        
        deleted = await delete_user_profile(user_id)
        added_to_blacklist = await add_to_blacklist(user_id)
        
        if deleted and added_to_blacklist:
            await message.answer(f"✅ Пользователь {user_id} забанен: профиль удален и добавлен в черный список.")
            await bot.send_message(
                user_id,
                "❗️<b>Вы были заблокированы</b>\n\n"
                "<i>Если считаете, что произошла ошибка, то обратитесь в поддержку 🧑‍💻 - /support</i>"
            )
        elif added_to_blacklist:
            await message.answer(f"⚠️ Профиль пользователя {user_id} не найден, но он был добавлен в черный список.")
        else:
            await message.answer(f"❌ Ошибка при добавлении пользователя {user_id} в черный список.")
            
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Ожидается число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при бане пользователя: {str(e)}")


@router.message(Command("get_all_id"))
async def get_all_id(message: types.Message, bot: Bot):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора для выполнения этой команды.")
        return
    
    try:
        user_ids = await get_all_user_ids()
        ids_text = "\n".join(str(user_id) for user_id in user_ids)
        
        document = BufferedInputFile(
            file=ids_text.encode('utf-8'),
            filename="all_user_ids.txt"
        )
        
        await bot.send_document(
            chat_id=message.chat.id,
            document=document,
            caption=f"📋 Все ID пользователей ({len(user_ids)} шт.):"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении ID пользователей: {str(e)}")


@router.message(Command("get_info_user"))
async def get_info_user(message: types.Message, bot: Bot):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора для выполнения этой команды.")
        return
    
    try:
        command_args = message.text.split()
        if len(command_args) != 2:
            await message.answer("❌ Неверный формат команды. Используйте: /get_info_user <user_id>")
            return
        
        user_id = int(command_args[1])
        
        from viewers import ProfileDisplayer
        displayer = await ProfileDisplayer.create(bot, int(ADMIN_ID), user_id)
        
        if displayer and displayer.profile:
            await displayer.with_stats().with_data_for_admin().send()
        else:
            await message.answer(f"❌ Профиль пользователя {user_id} не найден.")
            
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Ожидается число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении информации о пользователе: {str(e)}")


@router.message(Command("total_info"))
async def total_info(message: types.Message):
    """
    Команда для администратора: пишет кол-во людей в базе, количество людей в чс,
    кол-во людей по каждому полу.
    """
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора для выполнения этой команды.")
        return
    
    try:
        total_users = await get_total_users_count()
        blacklisted_users = await get_blacklisted_users_count()
        gender_counts = await get_users_by_gender()
        
        info_text = f"📊 <b>Общая статистика:</b>\n\n"
        info_text += f"👥 Всего пользователей: {total_users}\n"
        info_text += f"🚫 В черном списке: {blacklisted_users}\n\n"
        info_text += f"<b>Распределение по полу:</b>\n"
        
        for gender, count in gender_counts:
            info_text += f"{gender}: {count}\n"
        
        await message.answer(info_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении общей информации: {str(e)}")


@router.message(Command("unban_user"))
async def unban_user(message: types.Message, bot: Bot):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора для выполнения этой команды.")
        return
    
    try:
        command_args = message.text.split()
        if len(command_args) != 2:
            await message.answer("❌ Неверный формат команды. Используйте: /unban_user <user_id>")
            return
        
        user_id = int(command_args[1])
        
        removed_from_blacklist = await remove_from_blacklist(user_id)
        
        if removed_from_blacklist:
            await message.answer(f"✅ Пользователь {user_id} разбанен: удален из черного списка.")
            await bot.send_message(
                user_id,
                "✅ <b>Вы разблокированы</b>\n\n"
                "<i>Можете снова заполнить анкету</i>"
            )
        else:
            await message.answer(f"⚠️ Пользователь {user_id} не найден в черном списке.")
            
    except ValueError:
        await message.answer("❌ Неверный формат user_id. Ожидается число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при разбане пользователя: {str(e)}")