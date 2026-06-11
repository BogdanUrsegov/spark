"""
Модуль с обработчиками сообщений и команд бота.
"""

from aiogram import Router

from .command_handlers import router as command_router
from .callback_handlers import router as callback_router
from .profile.create_profile import router as create_profile_router
from .profile.edit_profile import router as edit_profile_router
from .message_handlers import router as message_router
from .errors import global_error_handler
from .status_search.callback_handlers import router as status_search_router

# Основной роутер, который будет включать в себя остальные
router = Router()

router.include_router(command_router)
router.include_router(callback_router)
router.include_router(create_profile_router)
router.include_router(edit_profile_router)
router.include_router(message_router)
router.include_router(status_search_router)


__all__ = [
    "router",
    "global_error_handler"
]