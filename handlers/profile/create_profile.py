import re
import logging
from aiogram import Bot, Router, F
from config import ADMIN_ID
from keyboards import get_back_home, get_gender_keyboard, get_location_keyboard
from services import *
from states import FillProfile
from aiogram.types import (
    CallbackQuery, Message, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from aiogram.fsm.context import FSMContext
from storage import add_new_profile
from utils import contains_forbidden_content
from utils import get_city_by_coords
from viewers import *

logger = logging.getLogger(__name__)

router = Router()


def _skip_description_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="⏭ Пропустить описание",
            callback_data="fill_profile_skip_description",
        )
    ]])


def _finish_media_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Готово",
            callback_data="finish_profile_media",
        )
    ]])


async def _ask_for_location(message: Message, state: FSMContext) -> None:
    await state.set_state(FillProfile.location)
    await message.answer(
        "📍 <b>Шаг 5/6: Твоя геопозиция</b>\n\n"
        "Нажми кнопку ниже, чтобы поделиться местоположением. "
        "Это поможет находить интересных людей рядом с тобой!",
        reply_markup=get_location_keyboard(False),
    )


async def _save_completed_profile(
    user_id: int,
    username: str | None,
    bot: Bot,
    state: FSMContext,
    reply_message: Message,
) -> None:
    data = await state.get_data()
    media_items = data.get("media", [])
    if not media_items:
        await reply_message.answer("❌ Сначала добавь хотя бы одно фото или видео.")
        return

    try:
        await add_new_profile(
            user_id=user_id,
            username=username,
            name=data["name"],
            age=data["age"],
            gender=data["gender"],
            description=data.get("description", ""),
            photo_id=media_items[0]["file_id"],
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            city=data.get("city"),
            media=media_items,
        )
        logger.info("Profile created successfully for user %s", user_id)
    except Exception as e:
        logger.exception("Error saving profile for user %s: %s", user_id, e)
        await reply_message.answer("❌ Произошла ошибка при сохранении профиля. Попробуйте позже.")
        return

    await state.clear()

    displayer = await ProfileDisplayer.create(bot, ADMIN_ID, user_id)
    if displayer and displayer.profile:
        await displayer.with_data_for_admin().send_over()

    await reply_message.answer(
        f"🎉 <b>Поздравляем, {data['name']}</b> 🎉\n\n"
        "✅ Твой профиль полностью заполнен!\n\n"
        "<b>Теперь ты можешь искать людей рядом с тобой 🚀</b>"
    )
    await reply_message.answer(
        "<i>Зайди в <b>главное меню</b> и начни искать новых друзей!</i> 👇",
        reply_markup=get_back_home(),
    )


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
    logger.info("Processing profile name for user %s.", user_id)
    
    if not (2 <= len(name) <= 30):
        logger.warning("Invalid profile name format for user %s.", user_id)
        await message.answer(
            "<b>❌ Имя должно содержать только буквы и быть от 2 до 30 символов.</b>\n\n"
            "Попробуй ещё раз:"
        )
        return

    if not re.fullmatch(r"[а-яА-ЯёЁa-zA-Z\s]+", name):
        logger.warning("Profile name contains invalid characters for user %s.", user_id)
        await message.answer("<b>❌ Имя должно содержать только буквы и пробелы.</b>\n\nПопробуй ещё раз:")
        return
    
    if contains_forbidden_content(name):
        logger.warning("Profile name contains forbidden content for user %s.", user_id)
        await message.answer(
            "<b>❌ Имя не должно содержать символ '@' или ссылки.</b>\n\n"
            "Попробуй ещё раз:"
        )
        return
    
    await state.update_data(name=name)
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
        "<b><i>Расскажи, чем увлекаешься, что ищешь — всё, что хочешь, чтобы узнали о тебе!</i></b>\n\n"
        "Можешь пропустить этот шаг кнопкой ниже.",
        parse_mode="HTML",
        reply_markup=_skip_description_keyboard(),
    )


@router.callback_query(FillProfile.description, F.data == "fill_profile_skip_description")
async def skip_profile_description(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description="")
    await callback.answer("Описание пропущено")
    await _ask_for_location(callback.message, state)


# --- Шаг 4: Описание (завершение) ---
@router.message(FillProfile.description)
async def process_description(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text is None:
        await message.answer("❌ Отправь описание текстом или пропусти этот шаг кнопкой ниже.")
        return
    description = message.text.strip()
    
    if len(description) > 500:
        await message.answer("<b>❌ Описание должно быть не длиннее 500 символов.</b>\n\nПопробуй снова:")
        return
    if contains_forbidden_content(description):
        await message.answer("<b>❌ Описание не должно содержать '@' или ссылки.</b>\n\nПопробуй ещё раз:")
        return
    
    await state.update_data(description=description)
    
    # Переход к геопозиции
    await _ask_for_location(message, state)


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
    await state.set_state(FillProfile.photo)
    await message.answer(
        "📸 <b>Шаг 6/6: Добавь фото или видео</b>\n\n"
        "Отправляй фото и/или видео по одному. Можно добавить до 3 файлов; "
        "длительность каждого видео — не больше 30 секунд.\n\n"
        "Когда закончишь, нажми «✅ Готово» ниже. Нужно добавить хотя бы один файл.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "После каждого файла появится кнопка «✅ Готово».",
        reply_markup=_finish_media_keyboard(),
    )


@router.message(FillProfile.location)
async def process_location_invalid(message: Message):
    await message.answer(
        "❌ Пожалуйста, нажми на кнопку <b>📍 Поделиться геопозицией</b> на клавиатуре ниже.",
        reply_markup=get_location_keyboard()
    )

# --- Шаг 6: Фото и видео (Финал) ---
@router.message(FillProfile.photo, F.photo | F.video)
async def process_profile_media(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.photo:
        item = {"type": "photo", "file_id": message.photo[-1].file_id}
    else:
        video = message.video
        if video.duration > 30:
            await message.answer(
                "❌ Видео должно длиться не больше 30 секунд. Отправь другое видео.",
                reply_markup=_finish_media_keyboard(),
            )
            return
        item = {"type": "video", "file_id": video.file_id}

    data = await state.get_data()
    media_items = list(data.get("media", []))
    if len(media_items) >= 3:
        await message.answer(
            "Лимит — 3 фото/видео. Нажми «✅ Готово», чтобы сохранить анкету.",
            reply_markup=_finish_media_keyboard(),
        )
        return

    media_items.append(item)
    await state.update_data(media=media_items)
    logger.info("Received profile media %s/3 for user %s", len(media_items), user_id)

    if len(media_items) == 3:
        response = "✅ Медиа добавлено (3/3). Лимит достигнут — нажми «✅ Готово»."
    else:
        response = (
            f"✅ Медиа добавлено ({len(media_items)}/3). "
            "Можешь отправить ещё или нажать «✅ Готово»."
        )
    await message.answer(response, reply_markup=_finish_media_keyboard())


@router.callback_query(FillProfile.photo, F.data == "finish_profile_media")
async def finish_profile_media(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not data.get("media"):
        await callback.answer("Сначала добавь хотя бы одно фото или видео.", show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        logger.debug("Could not remove media keyboard for user %s", callback.from_user.id)

    await _save_completed_profile(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        bot=bot,
        state=state,
        reply_message=callback.message,
    )


@router.message(FillProfile.photo)
async def process_profile_media_invalid(message: Message):
    await message.answer(
        "❌ Отправь фото или видео до 30 секунд. Можно добавить до трёх файлов."
    )
