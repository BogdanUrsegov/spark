import re
import json
import logging
from aiogram import Bot, Router, F
from config import ADMIN_ID
from keyboards import cancel_edit, get_location_keyboard, get_gender_edit_keyboard, get_edit_profile_keyboard
from services import *
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery, Message, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from aiogram.fsm.context import FSMContext
from states import EditProfile
from storage import update_user_field, get_user_profile, set_user_profile_media
from utils import contains_forbidden_content, get_city_by_coords
from viewers import *

logger = logging.getLogger(__name__)

router = Router()


def _finish_edit_media_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Готово", callback_data="finish_edit_profile_media")
    ]])


def _read_profile_media(profile: dict) -> list[dict[str, str]]:
    raw_media = profile.get("media_json")
    if raw_media:
        try:
            decoded = json.loads(raw_media)
            if isinstance(decoded, list):
                media = [
                    {"type": item["type"], "file_id": item["file_id"]}
                    for item in decoded
                    if isinstance(item, dict)
                    and item.get("type") in {"photo", "video"}
                    and isinstance(item.get("file_id"), str)
                    and item.get("file_id", "").strip()
                ]
                if media:
                    return media[:3]
        except (TypeError, KeyError, json.JSONDecodeError):
            logger.warning("Invalid media_json for profile %s; using legacy photo_id", profile.get("user_id"))
    photo_id = profile.get("photo_id")
    return [{"type": "photo", "file_id": photo_id}] if photo_id else []


async def _replace_edit_media_status(
    message: Message,
    state: FSMContext,
    text: str,
) -> None:
    data = await state.get_data()
    previous_id = data.get("media_status_message")
    if previous_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=previous_id)
        except Exception:
            pass
    has_added_media = len(data.get("media", [])) > data.get("initial_media_count", 0)
    status = await message.answer(
        text,
        reply_markup=_finish_edit_media_keyboard() if has_added_media else None,
    )
    await state.update_data(media_status_message=status.message_id)


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
    await state.clear()
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
    logger.info("Processing profile name update for user %s.", user_id)
    
    if not (2 <= len(name) <= 30):
        logger.warning("Invalid profile name format for user %s.", user_id)
        await message.answer("❌ <b>Имя должно быть от 2 до 30 символов. Попробуй ещё раз:</b>")
        return
    if not re.fullmatch(r"[а-яА-ЯёЁa-zA-Z\s]+", name):
        logger.warning("Profile name contains invalid characters for user %s.", user_id)
        await message.answer("❌ <b>Имя должно содержать только буквы и пробелы. Попробуй ещё раз:</b>")
        return
    if contains_forbidden_content(name):
        logger.warning("Profile name contains forbidden content for user %s.", user_id)
        await message.answer("❌ <b>Имя не должно содержать '@' или ссылки. Попробуй ещё раз:</b>")
        return

    success = await update_user_field(user_id, "name", name)
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

    success = await update_user_field(user_id, "description", desc)
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


# --- Добавление фото и видео в анкету ---
@router.message(EditProfile.photo, F.photo | F.video)
async def handle_edit_profile_media(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    data = await state.get_data()
    media_items = list(data.get("media", []))

    if message.photo:
        item = {"type": "photo", "file_id": message.photo[-1].file_id}
    else:
        video = message.video
        if video.duration > 30:
            await _replace_edit_media_status(
                message, state, "❌ Видео должно длиться не больше 30 секунд."
            )
            return
        item = {"type": "video", "file_id": video.file_id}

    if len(media_items) >= 3:
        await _replace_edit_media_status(
            message, state, "Лимит — 3 фото/видео. Новые файлы не добавлены."
        )
        return

    media_items.append(item)
    await state.update_data(media=media_items)
    await _replace_edit_media_status(message, state, f"✅ Добавлено ({len(media_items)}/3).")


@router.callback_query(F.data == "finish_edit_profile_media")
async def finish_edit_profile_media(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await state.get_state() != EditProfile.photo.state:
        await callback.answer("Этап редактирования уже завершён.")
        return

    data = await state.get_data()
    media_items = list(data.get("media", []))
    if len(media_items) <= data.get("initial_media_count", len(media_items)):
        await callback.answer("Сначала отправьте новое фото или видео.", show_alert=True)
        return

    try:
        success = await set_user_profile_media(callback.from_user.id, media_items)
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    if not success:
        await callback.answer("Не удалось сохранить медиа. Попробуйте ещё раз.", show_alert=True)
        return

    user_id = callback.from_user.id
    await callback.answer()
    await state.clear()

    displayer = await ProfileDisplayer.create(bot, user_id, user_id)
    profile_message_id = data.get("profile_message")
    if profile_message_id:
        await displayer.delete_profile_media(user_id, profile_message_id)

    for message_id in {data.get("message"), data.get("media_status_message")}:
        if message_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
            except Exception:
                pass

    await bot.send_message(user_id, "✅ Медиа анкеты обновлено.")
    if displayer and displayer.profile:
        await displayer.with_stats().with_profile_keyboard().send()
    else:
        await bot.send_message(user_id, "⚠️ Не удалось показать обновлённую анкету.")

    admin_displayer = await ProfileDisplayer.create(bot, ADMIN_ID, user_id)
    if admin_displayer and admin_displayer.profile:
        await admin_displayer.with_data_for_admin().send_over()


@router.message(EditProfile.photo)
async def handle_edit_profile_media_invalid(message: Message):
    await message.answer("❌ Отправьте фото или видео до 30 секунд.")


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
    profile = await get_user_profile(user_id)
    if not profile:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    prompt = await callback.message.answer(
        "📸 <b>Отправьте фото или видео до 30 секунд.</b>\n\n"
        "Можно добавить до 3 файлов. Новые файлы заменят прежние.",
        reply_markup=cancel_edit(),
    )
    await state.set_state(EditProfile.photo)
    # Editing media starts a fresh set: save will replace the previous media list.
    await state.update_data(
        message=prompt.message_id,
        profile_message=callback.message.message_id,
        media=[],
        initial_media_count=0,
        media_status_message=None,
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