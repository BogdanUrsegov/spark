from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from storage.database import get_user_field
from .buttons.cancel_edit_btn import cancel_edit_button


# ==================== CALLBACK CONSTANTS ====================
EDIT_PROFILE_CALL = "edit_profile"
FILTERS_CALL = "filters"
IS_ACTIVE_CALL = "is_active"
MAIN_MENU_CALL = "main_menu"

FILTER_GENDER_CALL = "filter_gender"
FILTER_MALE_GENDER_CALL = "filter_male_gender"
FILTER_ALL_GENDER_CALL = "filter_all_gender"
FILTER_FEMALE_GENDER_CALL = "filter_female_gender"

FILL_PROFILE_CALL = "fill_profile"
SHOW_MY_PROFILE_CALL = "show_my_profile"

EDIT_NAME_CALL = "edit_name"
EDIT_AGE_CALL = "edit_age"
EDIT_GENDER_CALL = "edit_gender"
EDIT_DESCRIPTION_CALL = "edit_description"
EDIT_PHOTO_CALL = "edit_photo"
EDIT_GEO_CALL = "edit_geo"

OFF_ACTIVE_CALL = "off_active"
ON_ACTIVE_CALL = "on_active"

GENDER_CALL_PREFIX = "gender:"

GENDERS = ["Мужской", "Женский"]


# ==================== KEYBOARDS ====================

def get_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Редактировать профиль", callback_data=EDIT_PROFILE_CALL)],
        [InlineKeyboardButton(text="⚙️ Фильтрация", callback_data=FILTERS_CALL)],
        [InlineKeyboardButton(text="🔎 Статус поиска", callback_data=IS_ACTIVE_CALL)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data=MAIN_MENU_CALL)]
    ])


async def get_filters_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пол", callback_data=FILTER_GENDER_CALL)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="show_my_profile")]
    ])


async def get_filter_gender_keyboard(user_id: int) -> InlineKeyboardMarkup:
    current = await get_user_field(user_id, "filter_gender") or 0
    
    # Галочки для выбранного значения
    genders = {0: "Всех 👥", 1: "Девушки 🙋‍♀️", 2: "Парни 🙋‍♂️"}
    all_g, female, male = [f"✅ {v}" if k == current else v for k, v in genders.items()]

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=male,   callback_data=FILTER_MALE_GENDER_CALL),
            InlineKeyboardButton(text=all_g,  callback_data=FILTER_ALL_GENDER_CALL),
            InlineKeyboardButton(text=female, callback_data=FILTER_FEMALE_GENDER_CALL),
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=FILTERS_CALL)]
    ])


def get_location_keyboard(is_cancel_button: bool = True) -> ReplyKeyboardMarkup:
    cancel_button = [KeyboardButton(text="❌ Отмена")] if is_cancel_button else []
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Поделиться геопозицией", request_location=True)],
            cancel_button
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_fill_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Заполнить анкету ✏️", callback_data=FILL_PROFILE_CALL)]
    ])


def get_gender_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=g, callback_data=f"{GENDER_CALL_PREFIX}{g}")
        for g in GENDERS
    ]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_gender_edit_keyboard():
    buttons = [
        InlineKeyboardButton(text=g, callback_data=f"{GENDER_CALL_PREFIX}{g}")
        for g in GENDERS
    ]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    keyboard.append(cancel_edit_button)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def show_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мой профиль 👤", callback_data=SHOW_MY_PROFILE_CALL)]
    ])


def get_edit_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔤 Имя", callback_data=EDIT_NAME_CALL),
            InlineKeyboardButton(text="🔢 Возраст", callback_data=EDIT_AGE_CALL)
        ],
        [
            InlineKeyboardButton(text="👤 Пол", callback_data=EDIT_GENDER_CALL),
            InlineKeyboardButton(text="✍️ О себе", callback_data=EDIT_DESCRIPTION_CALL)
        ],
        [
            InlineKeyboardButton(text="📸 Фото", callback_data=EDIT_PHOTO_CALL),
        ],
        [
            InlineKeyboardButton(text="📍 Местоположение", callback_data=EDIT_GEO_CALL),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=SHOW_MY_PROFILE_CALL)
        ]
    ])


def get_active_keyboard(user_id: int, is_active: bool):
    button = (
        InlineKeyboardButton(text="🤚 Остановить поиск", callback_data=OFF_ACTIVE_CALL)
        if is_active else
        InlineKeyboardButton(text="🔎 Снова искать", callback_data=ON_ACTIVE_CALL)
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [button],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=SHOW_MY_PROFILE_CALL)]
    ])


def cancel_edit():
    return InlineKeyboardMarkup(inline_keyboard=[cancel_edit_button])