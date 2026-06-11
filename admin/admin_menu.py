# handlers/admin_menu.py
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
from states import AdminStates
from storage import (
    get_total_users_count,
    get_blacklisted_users_count,
    get_users_by_gender,
    get_all_user_ids,
    delete_user_profile,
    add_to_blacklist,
    remove_from_blacklist,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return str(user_id) == ADMIN_ID


def get_admin_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Общая статистика", callback_data="admin_total_info")
    kb.button(text="👤 Инфо о пользователе", callback_data="admin_get_user_info")
    kb.button(text="📥 Список всех ID", callback_data="admin_get_all_ids")
    kb.button(text="✉️ Рассылка", callback_data="admin_broadcast")
    kb.button(text="🔨 Забанить пользователя", callback_data="admin_ban_user")
    kb.button(text="🔓 Разбанить пользователя", callback_data="admin_unban_user")
    kb.adjust(1)
    return kb.as_markup()


def get_cancel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="admin_cancel")
    return kb.as_markup()


def get_broadcast_confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить рассылку", callback_data="broadcast_confirm")
    kb.button(text="❌ Отмена", callback_data="admin_cancel")
    kb.adjust(1)
    return kb.as_markup()


@router.message(F.text == "/admin_menu")
async def cmd_admin_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=get_admin_menu_kb())


# -----------------------
# Общая статистика
# -----------------------
@router.callback_query(F.data == "admin_total_info")
async def total_info_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        total_users = await get_total_users_count()
        blacklisted_users = await get_blacklisted_users_count()
        gender_counts = await get_users_by_gender()

        info_text = "📊 <b>Общая статистика:</b>\n\n"
        info_text += f"👥 Всего пользователей: {total_users}\n"
        info_text += f"🚫 В чёрном списке: {blacklisted_users}\n\n"
        info_text += "<b>Распределение по полу:</b>\n"
        for gender, count in gender_counts:
            info_text += f"{gender}: {count}\n"

        await callback.message.edit_text(info_text, reply_markup=get_admin_menu_kb())
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=get_admin_menu_kb())
    await callback.answer()


# -----------------------
# Запрос user_id + отмена
# -----------------------
async def request_user_id(callback: types.CallbackQuery, state: FSMContext, action: str):
    await state.update_data(action=action)
    await state.set_state(AdminStates.entering_user_id)
    await callback.message.edit_text(
        "✏️ Введите <b>user_id</b> пользователя:",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_get_user_info")
async def get_user_info_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await request_user_id(callback, state, "get_info")


@router.callback_query(F.data == "admin_ban_user")
async def ban_user_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await request_user_id(callback, state, "ban")


@router.callback_query(F.data == "admin_unban_user")
async def unban_user_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await request_user_id(callback, state, "unban")


@router.callback_query(F.data == "admin_cancel")
async def cancel_input(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=get_admin_menu_kb())
    await callback.answer()


# -----------------------
# Обработка ввода user_id
# -----------------------
@router.message(AdminStates.entering_user_id)
async def process_user_id_input(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text.isdigit():
        await message.answer(
            "❌ Неверный формат. Отправьте <b>число</b> (user_id).\n"
            "Или нажмите «❌ Отмена» выше.",
            reply_markup=get_cancel_kb()
        )
        return

    user_id = int(message.text.strip())
    data = await state.get_data()
    action = data.get("action")
    await state.clear()

    if action == "get_info":
        from viewers import ProfileDisplayer
        displayer = await ProfileDisplayer.create(bot, message.from_user.id, user_id)
        if displayer and displayer.profile:
            await displayer.with_stats().with_data_for_admin().send()
        else:
            await message.answer(f"❌ Профиль пользователя {user_id} не найден.")
        await message.answer("🛠 Админ-панель", reply_markup=get_admin_menu_kb())

    elif action == "ban":
        deleted = await delete_user_profile(user_id)
        added = await add_to_blacklist(user_id)

        if deleted and added:
            await message.answer(f"✅ Пользователь {user_id} забанен.")
            try:
                await bot.send_message(
                    user_id,
                    "❗️<b>Вы были заблокированы</b>\n\n"
                    "<i>Если считаете, что произошла ошибка, обратитесь в поддержку — /support</i>",
                )
            except:
                pass
        elif added:
            await message.answer(f"⚠️ Профиль не найден, но {user_id} добавлен в ЧС.")
        else:
            await message.answer(f"❌ Не удалось забанить {user_id}.")
        await message.answer("🛠 Админ-панель", reply_markup=get_admin_menu_kb())

    elif action == "unban":
        removed = await remove_from_blacklist(user_id)
        if removed:
            await message.answer(f"✅ Пользователь {user_id} разбанен.")
            try:
                await bot.send_message(user_id, "✅ <b>Вы разблокированы</b>\n\n<i>Можете снова заполнить анкету</i>")
            except:
                pass
        else:
            await message.answer(f"⚠️ Пользователь {user_id} не в чёрном списке.")
        await message.answer("🛠 Админ-панель", reply_markup=get_admin_menu_kb())


# -----------------------
# Список всех ID
# -----------------------
@router.callback_query(F.data == "admin_get_all_ids")
async def get_all_ids_callback(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    try:
        user_ids = await get_all_user_ids()
        ids_text = "\n".join(str(uid) for uid in user_ids)
        document = BufferedInputFile(
            file=ids_text.encode("utf-8"),
            filename="all_user_ids.txt"
        )
        await bot.send_document(
            chat_id=callback.message.chat.id,
            document=document,
            caption=f"📋 Все ID ({len(user_ids)} шт.)"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")
        await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        "✉️ Отправьте текст для рассылки:\n(Поддерживается HTML-разметка)",
        reply_markup=get_cancel_kb()
    )
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        await message.answer("❌ Отправьте текстовое сообщение.", reply_markup=get_cancel_kb())
        return

    await state.update_data(broadcast_text=message.html_text)
    await state.set_state(AdminStates.broadcast_confirm)

    await message.answer(
        "🔍 <b>Превью рассылки:</b>\n\n" + message.html_text,
        parse_mode="HTML"
    )
    await message.answer(
        "❓ Вы действительно хотите отправить это <b>всем пользователям</b>?",
        reply_markup=get_broadcast_confirm_kb()
    )


@router.callback_query(F.data == "broadcast_confirm", AdminStates.broadcast_confirm)
async def confirm_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    text = data.get("broadcast_text")
    if not text:
        await callback.message.answer("❌ Текст рассылки утерян. Начните заново.", reply_markup=get_admin_menu_kb())
        await state.clear()
        return

    await state.clear()
    user_ids = await get_all_user_ids()

    if not user_ids:
        await callback.message.answer("📭 Нет активных пользователей для рассылки.", reply_markup=get_admin_menu_kb())
        return

    await callback.message.edit_text("⏳ Рассылка запущена... Это может занять время.")

    from utils.broadcast import broadcast

    result = await broadcast(
        bot,
        user_ids,
        text,
        chunk_size=25,
        delay_between_chunks=1.0,
        parse_mode="HTML"
    )

    report = (
        f"📤 <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно: {result['success']}\n"
        f"❌ Ошибок: {result['failed']}\n"
        f"👥 Всего: {result['total']}"
    )
    await callback.message.answer(report, reply_markup=get_admin_menu_kb())
    await callback.answer()