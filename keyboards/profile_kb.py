from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .buttons.cancel_edit_btn import cancel_edit_button


GENDERS = ["Мужской", "Женский"]


def get_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton(text="🔎 Статус поиска", callback_data="is_active")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def get_location_keyboard(is_cancel_button: bool = True) -> ReplyKeyboardMarkup:
    cancel_button = [KeyboardButton(text="❌ Отмена")] if is_cancel_button else []
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Поделиться геопозицией", request_location=True)],
            cancel_button
        ],
        resize_keyboard=True,
        one_time_keyboard=True  # Скроется после нажатия
    )

def get_fill_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Заполнить анкету ✏️", callback_data="fill_profile")]
    ])


def get_gender_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=g, callback_data=f"gender:{g}")
        for g in GENDERS
    ]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_gender_edit_keyboard():
    buttons = [
        InlineKeyboardButton(text=g, callback_data=f"gender:{g}")
        for g in GENDERS
    ]
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    keyboard.append(cancel_edit_button)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def show_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мой профиль 👤", callback_data="show_my_profile")]
    ])


def get_edit_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔤 Имя", callback_data="edit_name"),
            InlineKeyboardButton(text="🔢 Возраст", callback_data="edit_age")
        ],
        [
            InlineKeyboardButton(text="👤 Пол", callback_data="edit_gender"),
            InlineKeyboardButton(text="✍️ О себе", callback_data="edit_description")
        ],
        [
            InlineKeyboardButton(text="📸 Фото", callback_data="edit_photo"),
        ],
        [
            InlineKeyboardButton(text="📍 Местоположение", callback_data="edit_geo"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="show_my_profile")
        ]
    ])


def get_active_keyboard(user_id: int, is_active: bool):
    button = (
        InlineKeyboardButton(text="🤚 Остановить поиск", callback_data="off_active")
        if is_active else
        InlineKeyboardButton(text="🔎 Снова искать", callback_data="on_active")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [button],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="show_my_profile")]
    ])


def cancel_edit():
    return InlineKeyboardMarkup(inline_keyboard=[cancel_edit_button])