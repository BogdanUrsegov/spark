import html
import re
import logging
from aiogram import Bot, Router, F
from config import ADMIN_ID
from keyboards import get_back_home, get_gender_keyboard, get_location_keyboard
from services import *
from states import FillProfile
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from storage import add_new_profile
from utils import contains_forbidden_content
from utils import get_city_by_coords
from viewers import *

logger = logging.getLogger(__name__)

router = Router()


# --- Шаг 0: Начало заполнения профиля ---
@router.callback_query(F.data == "fill_profile")
async def fill_profile(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} started filling profile")
    
    await callback.message.edit_reply_markup(None)
    await callback.message.answer("<b>Начнем заполнение профиля!</b>")
    await callback.answer("Заполнение профиля")
    await state.set_state(FillProfile.name)
    await callback.message.answer(
        "👤 <b>Шаг 1/6: Как тебя зовут?</b>\n\n"
        "Пожалуйста, введи своё имя\n\n"
        "Например: <code>Иван</code>"
    )


# --- Шаг 1: Имя ---
@router.message(FillProfile.name)
async def process_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    logger.info(f"Processing name for user {user_id}: {name}")
    
    if not (2 <= len(name) <= 30):
        logger.warning(f"Invalid name format for user {user_id}: {name}")
        await message.answer(
            "<b>❌ Имя должно содержать только буквы и быть от 2 до 30 символов.</b>\n\n"
            "Попробуй ещё раз:"
        )
        return

    if not re.fullmatch(r"[а-яА-ЯёЁa-zA-Z\s]+", name):
        logger.warning(f"Name contains invalid characters for user {user_id}: {name}")
        await message.answer("<b>❌ Имя должно содержать только буквы и пробелы.</b>\n\nПопробуй ещё раз:")
        return
    
    if contains_forbidden_content(name):
        logger.warning(f"Name contains forbidden content for user {user_id}: {name}")
        await message.answer(
            "<b>❌ Имя не должно содержать символ '@' или ссылки.</b>\n\n"
            "Попробуй ещё раз:"
        )
        return
    
    await state.update_data(name=html.escape(name))
    logger.info(f"Name validated and stored for user {user_id}")

    await state.set_state(FillProfile.age)
    await message.answer(
        "🔢 <b>Шаг 2/6: Сколько тебе лет?</b>\n\n"
        "Напиши свой возраст цифрами\n\n"
        "Например: <code>19</code>."
    )


# --- Шаг 2: Возраст ---
@router.message(FillProfile.age)
async def process_age(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not message.text.isdigit():
        logger.warning(f"Invalid age format from user {user_id}: {message.text}")
        await message.answer("<b>❌ Возраст должен быть числом.</b>\n\nПопробуй снова:")
        return

    age = int(message.text)
    if not (16 <= age <= 30):
        logger.warning(f"Age out of range for user {user_id}: {age}")
        await message.answer("<b>❌ Возраст должен быть от 16 до 30 лет.</b>\n\nПопробуй снова:")
        return

    await state.update_data(age=age)
    logger.info(f"Age validated and stored for user {user_id}: {age}")

    await state.set_state(FillProfile.gender)
    await message.answer(
        "👤 <b>Шаг 3/6: Укажи свой пол</b>\n\n"
        "Выбери из списка ниже 👇",
        reply_markup=get_gender_keyboard()
    )


# --- Шаг 3: Пол ---
@router.callback_query(FillProfile.gender, F.data.startswith("gender:"))
async def process_gender_selection(callback: CallbackQuery, state):
    user_id = callback.from_user.id
    gender = callback.data.split(":", 1)[1]
    logger.info(f"Gender selected for user {user_id}: {gender}")

    await state.update_data(gender=gender)
    await callback.answer()

    await callback.message.edit_text(
        f"👤 <b>Шаг 3/6: Укажи свой пол</b>\n\n"
        f"Вы выбрали: <b>{gender}</b>",
        parse_mode="HTML"
    )

    await state.set_state(FillProfile.description)
    await callback.message.answer(
        "💬 <b>Шаг 4/6: Расскажи о себе!</b>\n\n"
        "Напиши короткое описание (до 500 символов).\n\n"
        "<b><i>Расскажи, чем увлекаешься, что ищешь — всё, что хочешь, чтобы узнали о тебе!</i></b>",
        parse_mode="HTML"
    )


# --- Шаг 4: Описание (завершение) ---
@router.message(FillProfile.description)
async def process_description(message: Message, state: FSMContext):
    user_id = message.from_user.id
    description = message.text.strip()
    
    if len(description) > 500:
        await message.answer("<b>❌ Описание должно быть не длиннее 500 символов.</b>\n\nПопробуй снова:")
        return
    if contains_forbidden_content(description):
        await message.answer("<b>❌ Описание не должно содержать '@' или ссылки.</b>\n\nПопробуй ещё раз:")
        return
    
    await state.update_data(description=html.escape(description))
    
    # Переход к геопозиции
    await state.set_state(FillProfile.location)
    await message.answer(
        "📍 <b>Шаг 5/6: Твоя геопозиция</b>\n\n"
        "Нажми кнопку ниже, чтобы поделиться местоположением. "
        "Это поможет находить интересных людей рядом с тобой!",
        reply_markup=get_location_keyboard()
    )


# --- Шаг 5: Геопозиция ---
from aiogram.types import ReplyKeyboardRemove
# ... импортируй get_city_by_coords ...

@router.message(FillProfile.location, F.location)
async def process_location(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lat = message.location.latitude
    lon = message.location.longitude
    
    logger.info(f"Location received for user {user_id}: {lat}, {lon}")
    
    # 1. Показываем пользователю, что идет процесс (чтобы он не спамил)
    processing_msg = await message.answer("🔄 Определяю твой город по геопозиции...")
    
    # 2. Делаем запрос с автоматическими повторами
    city = await get_city_by_coords(lat, lon)
    
    # 3. Сохраняем данные
    await state.update_data(latitude=lat, longitude=lon, city=city)
    
    tmp_text = "✅ <b>Геопозиция получена!</b>\n\n"

    if city != "Неизвестно":
        tmp_text += f"🏙 <i>Твой город определен как: {city}</i>"

    await processing_msg.edit_text(tmp_text)

    # Убираем клавиатуру геопозиции, чтобы не мешала
    await message.answer(
        "📸 <b>Шаг 6/6: Прикрепи фото!</b>\n\n"
        "Отправь одно фото — оно будет отображаться в твоей анкете.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.set_state(FillProfile.photo)


@router.message(FillProfile.location)
async def process_location_invalid(message: Message):
    await message.answer(
        "❌ Пожалуйста, нажми на кнопку <b>📍 Поделиться геопозицией</b> на клавиатуре ниже.",
        reply_markup=get_location_keyboard()
    )

# --- Шаг 6: Фото (Финал) ---
@router.message(FillProfile.photo, F.photo)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id
    logger.info(f"Processing photo for user {user_id}")

    data = await state.get_data()
    
    try:
        await add_new_profile(
            user_id=user_id,
            username=message.from_user.username,
            name=data["name"],
            age=data["age"],
            gender=data["gender"],
            description=data["description"],
            photo_id=photo_id,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            city=data.get("city")
        )
        logger.info(f"Profile created successfully for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving profile for user {user_id}: {e}")
        await message.answer("❌ Произошла ошибка при сохранении профиля. Попробуйте позже.")
        return

    await state.clear()
    
    # Уведомление админу (опционально)
    displayer = await ProfileDisplayer.create(bot, ADMIN_ID, user_id)
    if displayer and displayer.profile:
        await displayer.with_data_for_admin().send_over()

    await message.answer(
        f"🎉 <b>Поздравляем, {data['name']}</b> 🎉\n\n"
        "✅ Твой профиль полностью заполнен!\n\n"
        "<b>Теперь ты можешь искать людей рядом с тобой 🚀</b>"
    )
    await message.answer(
        "<i>Зайди в <b>главное меню</b> и начни искать новых друзей!</i> 👇",
        reply_markup=get_back_home()
    )


@router.message(FillProfile.photo)
async def process_photo_invalid(message: Message):
    await message.answer("<b>❌ Пожалуйста, отправь именно фото (не файл, не текст).</b>")