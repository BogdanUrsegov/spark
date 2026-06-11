import html
import re
import logging
from aiogram import Bot, Router, F
from config import ADMIN_ID
from keyboards import cancel_edit, get_location_keyboard, get_gender_edit_keyboard, get_edit_profile_keyboard
from services import *
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from states import EditProfile
from storage import update_user_field
from utils import contains_forbidden_content, get_city_by_coords
from viewers import *

logger = logging.getLogger(__name__)

router = Router()


@router.message(EditProfile.location, F.text == "❌ Отмена")
async def cancel_edit_geo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} cancelled editing")
    
    await state.clear()
    
    await message.answer("❌ <b>Редактирование отменено</b>", reply_markup=ReplyKeyboardRemove())
    
    # Возвращаем меню редактирования профиля
    await message.answer(
        "<b>Что вы хотите отредактировать?</b>",
        reply_markup=get_edit_profile_keyboard()
    )

@router.callback_query(F.data.startswith("cancel_edit"))
async def process_cancel_edit(callback: CallbackQuery, state: FSMContext, bot):
    user_id = callback.from_user.id
    try:
        await callback.message.delete()
    except TelegramBadRequest as e:
        if "can't be deleted for everyone" in e.message:
            logger.warning(e.message)
    await callback.message.answer(
        "<b>Что вы хотите отредактировать?</b>",
        reply_markup=get_edit_profile_keyboard()
    )
    await callback.answer()
    
# --- Редактирование имени ---
@router.message(EditProfile.name)
async def handle_edit_name(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    name = message.text.strip()
    logger.info(f"Processing name update for user {user_id}: {name}")
    
    if not (2 <= len(name) <= 30):
        logger.warning(f"Invalid name format for user {user_id}: {name}")
        await message.answer("❌ <b>Имя должно быть от 2 до 30 символов. Попробуй ещё раз:</b>")
        return
    if not re.fullmatch(r"[а-яА-ЯёЁa-zA-Z\s]+", name):
        logger.warning(f"Name contains invalid characters for user {user_id}: {name}")
        await message.answer("❌ <b>Имя должно содержать только буквы и пробелы. Попробуй ещё раз:</b>")
        return
    if contains_forbidden_content(name):
        logger.warning(f"Name contains forbidden content for user {user_id}: {name}")
        await message.answer("❌ <b>Имя не должно содержать '@' или ссылки. Попробуй ещё раз:</b>")
        return

    success = await update_user_field(user_id, "name", html.escape(name))
    data = await state.get_data()
    await bot.edit_message_reply_markup(chat_id=user_id, message_id=data["message"], reply_markup=None)
    await state.clear()
    if success:
        logger.info(f"Name updated successfully for user {user_id}")
        await message.answer("✅ <b>Имя успешно обновлено!</b>")
        displayer = await ProfileDisplayer.create(bot, user_id, user_id)
        logger.debug(f"Profile found for user {user_id}, displaying")
        await displayer.with_stats().with_profile_keyboard().send_over(reply_to=message)
    else:
        logger.error(f"Failed to update name for user {user_id}")
        await message.answer("⚠️ <b>Не удалось сохранить имя. Попробуйте позже.</b>")


# --- Редактирование возраста ---
@router.message(EditProfile.age)
async def handle_edit_age(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    logger.info(f"Processing age update for user {user_id}")
    
    if not message.text.isdigit():
        logger.warning(f"Invalid age format from user {user_id}: {message.text}")
        await message.answer("❌ <b>Возраст должен быть числом. Попробуй снова:</b>")
        return
    age = int(message.text)
    if not (16 <= age <= 30):
        logger.warning(f"Age out of range for user {user_id}: {age}")
        await message.answer("❌ <b>Возраст должен быть от 16 до 30 лет. Попробуй снова:</b>")
        return

    success = await update_user_field(user_id, "age", age)
    
    data = await state.get_data()
    await bot.edit_message_reply_markup(chat_id=user_id, message_id=data["message"], reply_markup=None)
    
    await state.clear()
    if success:
        logger.info(f"Age updated successfully for user {user_id}: {age}")
        await message.answer("✅ <b>Возраст успешно обновлён!</b>")
        displayer = await ProfileDisplayer.create(bot, user_id, user_id)
        logger.debug(f"Profile found for user {user_id}, displaying")
        await displayer.with_stats().with_profile_keyboard().send_over(reply_to=message)
    else:
        logger.error(f"Failed to update age for user {user_id}")
        await message.answer("⚠️ <b>Не удалось сохранить возраст. Попробуйте позже.</b>")


# --- Редактирование описания ---
@router.message(EditProfile.description)
async def handle_edit_description(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    desc = message.text.strip()
    logger.info(f"Processing description update for user {user_id}")
    
    if len(desc) > 500:
        logger.warning(f"Description too long for user {user_id}: {len(desc)} chars")
        await message.answer("<b>❌ Описание должно быть не длиннее 500 символов. Попробуй снова:</b>")
        return
    if contains_forbidden_content(desc):
        logger.warning(f"Description contains forbidden content for user {user_id}")
        await message.answer(
            "❌ <b>Описание не должно содержать '@' или ссылки. Попробуй ещё раз:</b>"
        )
        return

    success = await update_user_field(user_id, "description", html.escape(desc))
    data = await state.get_data()
    await bot.edit_message_reply_markup(chat_id=user_id, message_id=data["message"], reply_markup=None)
    await state.clear()
    if success:
        logger.info(f"Description updated successfully for user {user_id}")
        await message.answer("✅ <b>Описание успешно обновлено!</b>")
        displayer = await ProfileDisplayer.create(bot, user_id, user_id)
        logger.debug(f"Profile found for user {user_id}, displaying")
        await displayer.with_stats().with_profile_keyboard().send_over(reply_to=message)
    else:
        logger.error(f"Failed to update description for user {user_id}")
        await message.answer("⚠️ <b>Не удалось сохранить описание. Попробуйте позже.</b>")


# --- Редактирование фото ---
@router.message(EditProfile.photo, F.photo)
async def handle_edit_photo(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    logger.info(f"Processing photo update for user {user_id}")
    
    success = await update_user_field(user_id, "photo_id", photo_id)
    data = await state.get_data()
    await bot.edit_message_reply_markup(chat_id=user_id, message_id=data["message"], reply_markup=None)
    await state.clear()
    if success:
        logger.info(f"Photo updated successfully for user {user_id}")
        await message.answer("✅ <b>Фото успешно обновлено!</b>")
        displayer = await ProfileDisplayer.create(bot, user_id, user_id)
        logger.debug(f"Profile found for user {user_id}, displaying")
        await displayer.with_stats().with_profile_keyboard().send_over(reply_to=message)
        displayer = await ProfileDisplayer.create(bot, ADMIN_ID, user_id)
        if displayer and displayer.profile:
            await displayer.with_data_for_admin().send_over()
    else:
        logger.error(f"Failed to update photo for user {user_id}")
        await message.answer("⚠️ <b>Не удалось сохранить фото. Попробуйте позже.</b>")


# --- Ошибка: прислали не фото ---
@router.message(EditProfile.photo)
async def handle_edit_photo_invalid(message: Message):
    user_id = message.from_user.id
    logger.warning(f"User {user_id} sent invalid photo (not an image)")
    await message.answer("❌ <b>Пожалуйста, отправьте именно фото (не файл и не текст).</b>")


@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started editing profile")
    
    await callback.message.edit_reply_markup(None)
    await callback.message.answer(
        "<b>Что вы хотите отредактировать?</b>",
        reply_markup=get_edit_profile_keyboard()
    )
    await callback.answer()


# --- Редактирование имени ---
@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started editing name")
    
    await callback.answer()
    await state.set_state(EditProfile.name)
    await state.update_data(message=callback.message.message_id)
    await callback.message.edit_text(
        "🔤 <b>Редактирование имени</b>\n\n"
        "Введите новое имя:",
        reply_markup=cancel_edit()
    )


# --- Редактирование возраста ---
@router.callback_query(F.data == "edit_age")
async def edit_age(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started editing age")
    
    await callback.answer()
    await state.set_state(EditProfile.age)
    await state.update_data(message=callback.message.message_id)
    await callback.message.edit_text(
        "🔢 <b>Редактирование возраста</b>\n\n"
        "Введите новый возраст:",
        reply_markup=cancel_edit()
    )


# --- Редактирование пола ---
@router.callback_query(F.data == "edit_gender")
async def edit_gender(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started editing gender")
    
    await callback.answer()
    await state.set_state(EditProfile.gender)
    
    await callback.message.edit_text(
        "👤 <b>Редактирование пола</b>\n\n"
        "Выберите ваш пол:",
        reply_markup=get_gender_edit_keyboard()
    )


# --- Редактирование описания ---
@router.callback_query(F.data == "edit_description")
async def edit_description(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started editing description")
    
    await callback.answer()
    await state.set_state(EditProfile.description)
    await state.update_data(message=callback.message.message_id)
    await callback.message.edit_text(
        "✍️ <b>Редактирование описания</b>\n\n"
        "Введите новое описание:",
        reply_markup=cancel_edit()
    )


# --- Редактирование фото ---
@router.callback_query(F.data == "edit_photo")
async def edit_photo(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started editing photo")
    
    await callback.answer()
    await state.set_state(EditProfile.photo)
    await state.update_data(message=callback.message.message_id)
    await callback.message.edit_text(
        "🖼️ <b>Редактирование фото</b>\n\n"
        "Отправьте новое фото:",
        reply_markup=cancel_edit()
    )


@router.callback_query(EditProfile.gender, F.data.startswith("gender:"))
async def process_edit_gender(callback: CallbackQuery, state: FSMContext, bot):
    user_id = callback.from_user.id
    gender = callback.data.split(":", 1)[1]
    logger.info(f"Processing gender update for user {user_id}: {gender}")
    
    success = await update_user_field(user_id, "gender", gender)
    await state.clear()
    await callback.answer()
    if success:
        logger.info(f"Gender updated successfully for user {user_id}")
        await callback.message.answer("✅ <b>Пол успешно обновлён!</b>")
    else:
        logger.error(f"Failed to update gender for user {user_id}")
        await callback.message.answer("⚠️ <b>Не удалось сохранить пол. Попробуйте позже.</b>")
    await handle_show_my_profile_request(bot, callback)

# --- Редактирование геопозиции (кнопка) ---
@router.callback_query(F.data == "edit_geo")
async def edit_geo(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started editing geo location")
    
    await callback.answer()
    await state.set_state(EditProfile.location)
    await state.update_data(message=callback.message.message_id)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Отправляем НОВОЕ сообщение с reply-клавиатурой (не редактируем!)
    await callback.message.answer(
        "📍 <b>Редактирование геопозиции</b>\n\n"
        "Нажми кнопку ниже, чтобы поделиться новым местоположением.",
        reply_markup=get_location_keyboard()
    )


# --- Обработка полученной геопозиции ---
@router.message(EditProfile.location, F.location)
async def handle_edit_geo(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    lat = message.location.latitude
    lon = message.location.longitude
    logger.info(f"Processing geo update for user {user_id}: {lat}, {lon}")
    
    # Убираем клавиатуру с кнопкой геопозиции
    await message.answer("🔄 Обновляю данные...", reply_markup=ReplyKeyboardRemove())
    
    # Определяем город (если есть функция)
    city = None
    try:
        city = await get_city_by_coords(lat, lon)
    except Exception as e:
        logger.warning(f"Failed to get city for user {user_id}: {e}")
    
    # Обновляем все три поля в БД
    success_lat = await update_user_field(user_id, "latitude", lat)
    success_lon = await update_user_field(user_id, "longitude", lon)
    if city:
        await update_user_field(user_id, "city", city)
    
    await state.clear()
    
    if success_lat and success_lon:
        logger.info(f"Geo updated successfully for user {user_id}")
        city_text = f"<i>🏙 Город: {city}</i>" if city else ""
        await message.answer(f"✅ <b>Геопозиция успешно обновлена!</b>\n\n{city_text}")
        
        # Показываем обновлённый профиль
        displayer = await ProfileDisplayer.create(bot, user_id, user_id)
        if displayer and displayer.profile:
            await displayer.with_stats().with_profile_keyboard().send_over(reply_to=message)
    else:
        logger.error(f"Failed to update geo for user {user_id}")
        await message.answer("⚠️ <b>Не удалось сохранить геопозицию. Попробуйте позже.</b>")

# --- Ошибка: прислали не геопозицию ---
@router.message(EditProfile.location)
async def handle_edit_geo_invalid(message: Message):
    user_id = message.from_user.id
    logger.warning(f"User {user_id} sent invalid data instead of location")
    await message.answer(
        "❌ <b>Пожалуйста, нажми на кнопку 📍 Поделиться геопозицией</b> на клавиатуре ниже.",
        reply_markup=get_location_keyboard()
    )