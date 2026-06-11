from aiogram import Router
from .all_command import commands
from .admin_commands import router as admin_commands_router
from .admin_menu import router as admin_menu_router


router = Router()

router.include_router(admin_commands_router)
router.include_router(admin_menu_router)


__all__ = [
    "commands",
    "router"
]