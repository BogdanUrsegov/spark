import logging
from aiogram import Bot, Router, F
from keyboards import get_active_keyboard
from services import *
from aiogram.types import CallbackQuery

from storage import get_user_field, update_user_field
from viewers import *

logger = logging.getLogger(__name__)


router = Router()

STATUS_SEARCH = {0: "Неактивный 🔴",
                 1: "Активный 🟢"}

STATUS_SEARCH_INFO = {0: "При неактивном статусе вашу анкету не видят другие пользователи при поиске",
                      1: "При активном статусе вашу анкету видят другие пользователи при поиске"}

@router.callback_query(F.data.startswith("is_active"))
async def handle_is_active(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    is_active = bool(await get_user_field(user_id, "is_active"))
    is_active_str = STATUS_SEARCH[is_active]
    is_active_notify = STATUS_SEARCH_INFO[is_active]
    await callback.message.delete_reply_markup()
    await callback.message.answer(f"<b>Ваш статус поиска: <i>{is_active_str}</i></b>\n\n<i>{is_active_notify}</i>", reply_markup=get_active_keyboard(user_id, is_active))


@router.callback_query(F.data == "on_active")
async def handle_on_active(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    success = await update_user_field(user_id, "is_active", 1)
    is_active = bool(await get_user_field(user_id, "is_active"))
    is_active_str = STATUS_SEARCH[is_active]
    is_active_notify = STATUS_SEARCH_INFO[is_active]
    if success:
        try:
            await callback.message.edit_text(f"<b>Ваш статус поиска: <i>{is_active_str}</i></b>\n\n<i>{is_active_notify}</i>", reply_markup=get_active_keyboard(user_id, is_active))
            await callback.answer(is_active_str)
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                logger.error(e)

@router.callback_query(F.data == "off_active")
async def handle_off_active(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    success = await update_user_field(user_id, "is_active", 0)
    is_active = bool(await get_user_field(user_id, "is_active"))
    is_active_str = STATUS_SEARCH[is_active]
    is_active_notify = STATUS_SEARCH_INFO[is_active]
    if success:
        try:
            await callback.message.edit_text(f"<b>Ваш статус поиска: <i>{is_active_str}</i></b>\n\n<i>{is_active_notify}</i>", reply_markup=get_active_keyboard(user_id, is_active))
            await callback.answer(is_active_str)
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                logger.error(e)
