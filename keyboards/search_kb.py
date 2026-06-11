from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .buttons.back_home_btn import back_home_btn


def get_search_profiles_button() -> InlineKeyboardMarkup:
    """
    Возвращает инлайн-кнопку для перехода к просмотру анкет.
    """
    keyboard = InlineKeyboardMarkup(
            InlineKeyboardButton(
                text="👥 Смотреть анкеты",
                callback_data="view_profiles"
            )
        )
    return keyboard

def get_actions_keyboard(user_id) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️", callback_data=f"like:{user_id}"),
            InlineKeyboardButton(text="💬", callback_data=f"like_msg:{user_id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike:{user_id}")
        ],
        [
            back_home_btn
        ]

    ])

    return keyboard

def get_view_liker_keyboard(target_id) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Посмотреть анкету 👀",
                callback_data=f"view_liker:{target_id}"
            )
        ]
    ])
    return keyboard

def get_pre_open_chat_keyboard(target_id) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Посмотреть анкету 👀",
                callback_data=f"open_chat:{target_id}"
            )
        ]
    ])
    return keyboard

def get_open_chat_keyboard(target_id, username) -> InlineKeyboardMarkup:
    if username:
        button_open = InlineKeyboardButton(
                text="Написать человеку 💬",
                url=f"https://t.me/{username}"
            )
    else:
        button_open = InlineKeyboardButton(
                text="Профиль закрыт 🔓",
                callback_data=f"update_username:{target_id}"
            )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # [
        #     InlineKeyboardButton(
        #         text="Обновить данные 🔄",
        #         callback_data=f"update_profile:{target_id}"
        #     )
        # ],
        [
            button_open
        ]
    ])
    return keyboard