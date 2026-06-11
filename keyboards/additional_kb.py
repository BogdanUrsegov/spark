from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .buttons.back_home_btn import back_home_btn


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает инлайн-кнопки для поиска и показа профиля.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔍 Смотреть анкеты",
                callback_data="view_profiles"
            )
        ],
        [
            InlineKeyboardButton(
                text="👤 Мой профиль",
                callback_data="show_my_profile"
            )
        ]
    ])
    return keyboard

def get_back_home():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            back_home_btn
        ]
    ])
    return keyboard

def get_empty_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton()
        ]
    ])
    return keyboard

def get_cancel_like_msg(target_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Отменить отправку ❌",
                callback_data=f"cancel_like_msg:{target_id}"
            )
        ]
    ])
    return keyboard