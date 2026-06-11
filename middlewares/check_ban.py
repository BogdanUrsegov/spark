from aiogram import BaseMiddleware, Bot
from aiogram.types import Update, Message, CallbackQuery, InlineQuery, ChatMemberUpdated
from typing import Callable, Dict, Any, Awaitable
from storage import is_user_blacklisted
import logging


logger = logging.getLogger(__name__)


class BlacklistMiddleware(BaseMiddleware):
    """
    Middleware, блокирующая пользователей из чёрного списка
    и отправляющая им уведомление при попытке взаимодействия.
    """
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        chat_id = None

        # Извлекаем пользователя и chat_id (если доступен)
        if event.message:
            user = event.message.from_user
            chat_id = event.message.chat.id
        elif event.callback_query:
            user = event.callback_query.from_user
            chat_id = event.callback_query.message.chat.id if event.callback_query.message else None
        elif event.inline_query:
            user = event.inline_query.from_user
        elif event.my_chat_member:
            user = event.my_chat_member.from_user
            chat_id = event.my_chat_member.chat.id
        elif event.chat_member:
            user = event.chat_member.from_user
            chat_id = event.chat_member.chat.id

        if user and await is_user_blacklisted(user.id):
            logger.warning(f"Blocked user {user.id} tried to interact with the bot.")

            # Отправляем уведомление, если есть chat_id (например, в ЛС или группе)
            if chat_id:
                try:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text="❌ Вы заблокированы и не можете взаимодействовать с этим ботом."
                    )
                except Exception as e:
                    logger.debug(f"Could not send blacklist notice to user {user.id}: {e}")

            # Для inline-запросов отдельный ответ
            if event.inline_query:
                try:
                    await self.bot.answer_inline_query(
                        inline_query_id=event.inline_query.id,
                        results=[],
                        switch_pm_text="❌ Вы заблокированы",
                        switch_pm_parameter="blacklisted"
                    )
                except Exception as e:
                    logger.debug(f"Could not answer inline query for blacklisted user {user.id}: {e}")

            # Прекращаем обработку
            return

        # Продолжаем обработку, если пользователь не в чёрном списке
        return await handler(event, data)