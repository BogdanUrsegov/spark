import logging
from aiogram import Bot
import html
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from typing import Callable, Optional, Union, Dict, Any
from admin import commands as admins_commands
from config import ADMIN_ID
from storage import get_user_profile, is_profile_complete, get_next_profile_for_user
from keyboards import (
    get_actions_keyboard,
    get_profile_keyboard,
    get_edit_profile_keyboard,
    get_open_chat_keyboard
)
from storage.database import update_user_field

logger = logging.getLogger(__name__)


class ProfileDisplayer:
    def __init__(self, bot: Bot, user_id: int):
        self.bot = bot
        self.user_id = user_id
        self.profile = None
        self._caption_template = self._default_caption_template
        self._keyboard_factory: Callable[[Dict[str, Any]], InlineKeyboardMarkup] = (
            lambda profile: InlineKeyboardMarkup(inline_keyboard=[])
        )
        self._show_stats = False

    @classmethod
    async def create(cls, bot: Bot, user_id: int, target_id: int):
        """Фабричный метод для асинхронной инициализации"""
        logger.debug(f"Creating ProfileDisplayer for user {user_id} with target {target_id}")
        instance = cls(bot, user_id)
        await instance._load_profile(target_id)
        return instance

    @classmethod
    async def for_next_profile(cls, bot: Bot, viewer_id: int) -> Optional["ProfileDisplayer"]:
        """
        Создаёт экземпляр для отображения следующей чужой анкеты.
        Возвращает None, если подходящих анкет нет.
        """
        logger.debug(f"Creating ProfileDisplayer for next profile for user {viewer_id}")
        next_profile = await get_next_profile_for_user(viewer_id)
        if not next_profile:
            logger.debug(f"No next profile available for user {viewer_id}")
            return None
        return await cls.create(bot, viewer_id, target_id=next_profile)

    async def _load_profile(self, target_id: int) -> bool:
        """Загружает профиль ЦЕЛИ (не обязательно самого пользователя)"""
        logger.debug(f"Loading profile for target {target_id}")
        if not await is_profile_complete(target_id):
            logger.debug(f"Profile for target {target_id} is not complete")
            return False
        self.profile = await get_user_profile(target_id)
        if self.profile:
            logger.debug(f"Profile loaded successfully for target {target_id}")
        else:
            logger.debug(f"Profile not found for target {target_id}")
        return self.profile is not None

    # -------------------------------
    # СТРАТЕГИИ ФОРМАТИРОВАНИЯ CAPTION
    # -------------------------------

    @staticmethod
    def _get_gender_emoji(gender: str) -> str:
        """Возвращает эмодзи в зависимости от пола"""
        if gender == "Мужской":
            return "👦"
        elif gender == "Женский":
            return "👧"
        return "👤"

    @staticmethod
    def _format_location(city) -> str:
        """Форматирует строку с городом (если есть)"""
        if city and city.strip():
            return f"📍 {city}"
        return ""

    @staticmethod
    def _default_caption_template(profile: Dict[str, Any]) -> str:
        """Стандартная анкета без статистики"""
        name = html.escape(profile["name"])
        desc = html.escape(profile["description"])
        gender_emoji = ProfileDisplayer._get_gender_emoji(profile["gender"])
        location = ProfileDisplayer._format_location(profile.get("city"))
        
        return (
            f"{gender_emoji} <b>{name}, {profile['age']}</b>\n"
            f"{location}\n\n"
            f"<b>О себе:</b>\n"
            f"{desc}\n"
        )

    @staticmethod
    def _with_stats_caption_template(profile: Dict[str, Any]) -> str:
        """Анкета с отображением статистики лайков"""
        base = ProfileDisplayer._default_caption_template(profile)
        return (
            f"{base}\n"
            f"<b><i>❤️ Поставил лайков: {profile['likes_given']}</i></b>\n"
            f"<b><i>💌 Получил лайков: {profile['likes_received']}</i></b>\n"
            f"<b><i>🤝 Взаимных: {profile['mutual_likes']}</i></b>"
        )

    @staticmethod
    def _with_like_response_caption_template(profile: Dict[str, Any]) -> str:
        base = ProfileDisplayer._default_caption_template(profile)
        return f"{base}\n\n<b>Вы выбрали:</b> ❤️"

    @staticmethod
    def _with_like_message_response_caption_template(profile: Dict[str, Any]) -> str:
        base = ProfileDisplayer._default_caption_template(profile)
        return f"{base}\n\n<b>Вы выбрали:</b> 💬"

    @staticmethod
    def _with_dislike_response_caption_template(profile: Dict[str, Any]) -> str:
        base = ProfileDisplayer._default_caption_template(profile)
        return f"{base}\n\n<b>Вы выбрали:</b> 👎"

    @staticmethod
    def _compact_caption_template(profile: Dict[str, Any]) -> str:
        """Компактный вариант для списка"""
        import html
        name = html.escape(profile["name"])
        gender_emoji = ProfileDisplayer._get_gender_emoji(profile["gender"])
        city = profile.get("city")
        city_str = f" | 📍 {city}" if city else ""
        return f"{gender_emoji} <b>{name}</b>, {profile['age']}{city_str}"

    @staticmethod
    def _with_data_for_admin_template(profile: Dict[str, Any]) -> str:
        """Анкета с отображением данных для админа"""
        base = ProfileDisplayer._default_caption_template(profile)
        return (
            f"{base}\n"
            f"User ID: <code>{profile['user_id']}</code>\n"
            f"Username: @{profile['username'] if profile['username'] else ''}\n\n"
            f"Для быстрого бана: <code>/{admins_commands['ban_user']} {profile['user_id']}</code>"
        )
    
    # --------------------------------
    # НАСТРОЙКА ПОВЕДЕНИЯ ОТОБРАЖЕНИЯ 
    # --------------------------------

    def with_stats(self) -> "ProfileDisplayer":
        """Добавляет статистику лайков в caption"""
        self._caption_template = self._with_stats_caption_template
        self._show_stats = True
        return self

    def with_like_response(self) -> "ProfileDisplayer":
        """Добавляет надпись 'Вы выбрали: ❤️' и убирает клавиатуру."""
        self._caption_template = self._with_like_response_caption_template
        self._keyboard_factory = lambda _: InlineKeyboardMarkup(inline_keyboard=[])
        return self

    def with_like_message_response(self) -> "ProfileDisplayer":
        """Добавляет надпись 'Вы выбрали: 💬' и убирает клавиатуру."""
        self._caption_template = self._with_like_message_response_caption_template
        self._keyboard_factory = lambda _: InlineKeyboardMarkup(inline_keyboard=[])
        return self

    def with_dislike_response(self) -> "ProfileDisplayer":
        """Добавляет надпись 'Вы выбрали: 👎' и убирает клавиатуру."""
        self._caption_template = self._with_dislike_response_caption_template
        self._keyboard_factory = lambda _: InlineKeyboardMarkup(inline_keyboard=[])
        return self

    def as_compact(self) -> "ProfileDisplayer":
        """Использует компактный формат отображения"""
        self._caption_template = self._compact_caption_template
        return self
    
    def with_data_for_admin(self):
        if self.user_id == ADMIN_ID:
            self._caption_template = self._with_data_for_admin_template
        return self

    def with_keyboard(self, keyboard_factory: Callable[[Dict[str, Any]], InlineKeyboardMarkup]) -> "ProfileDisplayer":
        """
        Задаёт фабрику для генерации клавиатуры.
        keyboard_factory получает профиль и возвращает клавиатуру.
        """
        self._keyboard_factory = keyboard_factory
        return self

    # Предустановленные конфигурации клавиатур
    def with_actions_keyboard(self) -> "ProfileDisplayer":
        """Стандартные кнопки для просмотра анкет (❤️, ❌, 💬)"""
        self._keyboard_factory = lambda profile: get_actions_keyboard(profile["user_id"])
        return self
    
    def with_open_chat_keyboard(self, username) -> "ProfileDisplayer":
        self._keyboard_factory = lambda profile: get_open_chat_keyboard(profile["user_id"], username)
        return self

    def with_profile_keyboard(self) -> "ProfileDisplayer":
        """Кнопки для просмотра своего профиля"""
        self._keyboard_factory = lambda _: get_profile_keyboard()
        return self

    def with_edit_keyboard(self) -> "ProfileDisplayer":
        """Кнопки для редактирования профиля"""
        self._keyboard_factory = lambda _: get_edit_profile_keyboard()
        return self

    # --------------------
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ УПРАВЛЕНИЯ СООБЩЕНИЯМИ
    # --------------------

    async def _delete_message_safe(self, obj: Union[Message, CallbackQuery]) -> None:
        """Безопасно удаляет сообщение, игнорируя ошибки."""
        if isinstance(obj, CallbackQuery) and obj.message:
            try:
                await obj.message.delete()
            except Exception:
                pass
        elif isinstance(obj, Message):
            try:
                await obj.delete()
            except Exception:
                pass

    async def _remove_buttons_safe(self, obj: Union[Message, CallbackQuery]) -> None:
        """Безопасно убирает inline-кнопки с сообщения."""
        message = obj.message if isinstance(obj, CallbackQuery) else obj
        if message:
            try:
                await message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass

    # --------------------
    # ОСНОВНЫЕ МЕТОДЫ ОТПРАВКИ
    # --------------------

    async def send(self) -> bool:
        """
        Отправляет новое сообщение с профилем.
        Не взаимоействует с предыдущими сообщениями.
        :return: True если профиль существует и отправлен, иначе False.
        """
        if not self.profile:
            logger.warning(f"Cannot send profile - no profile loaded for user {self.user_id}")
            return False

        caption = self._caption_template(self.profile)
        keyboard = self._keyboard_factory(self.profile)

        await self.bot.send_photo(
            chat_id=self.user_id,
            photo=self.profile["photo_id"],
            caption=caption,
            reply_markup=keyboard,
        )
        logger.info(f"Profile sent to user {self.user_id}")
        return True

    async def send_over(
        self,
        reply_to: Union[Message, CallbackQuery, None] = None,
        delete_previous: bool = True,
        remove_buttons_only: bool = False,
        is_reply: bool = False
    ) -> bool:
        """
        Отправляет профиль, предварительно обработав предыдущее сообщение.
        
        Поведение:
        - Если delete_previous=True → удаляет всё сообщение.
        - Если delete_previous=False и remove_buttons_only=True → убирает только кнопки.
        - Если оба False → ничего не делает с предыдущим сообщением.
        
        :param reply_to: исходное сообщение или коллбэк для очистки
        :param delete_previous: удалять ли всё предыдущее сообщение
        :param remove_buttons_only: удалять ли только кнопки (если delete_previous=False)
        :return: True если профиль отправлен
        """
        logger.debug(f"Sending profile over to user {self.user_id}")
        reply_to_message_id = None
        if not self.profile:
            logger.warning(f"Cannot send profile over - no profile loaded for user {self.user_id}")
            return False

        # Удаление предыдущего сообщения (если указан)
        if isinstance(reply_to, CallbackQuery):
            if delete_previous:
                await self._delete_message_safe(reply_to)
            else:
                if remove_buttons_only:
                    await self._remove_buttons_safe(reply_to)
                if is_reply:
                    reply_to_message_id = reply_to.message.message_id if reply_to.message else None

        # Отправка нового сообщения
        caption = self._caption_template(self.profile)
        keyboard = self._keyboard_factory(self.profile)

        await self.bot.send_photo(
            chat_id=self.user_id,
            photo=self.profile["photo_id"],
            caption=caption,
            reply_markup=keyboard,
            reply_to_message_id=reply_to_message_id
        )
        logger.info(f"Profile sent over to user {self.user_id}")
        return True

    async def edit(
        self,
        message: Union[Message, CallbackQuery],
        update_caption: bool = True,
        update_keyboard: bool = True,
    ) -> bool:
        """
        Редактирует существующее сообщение с профилем, обновляя caption и/или клавиатуру.
        
        :param message: Объект Message или CallbackQuery, содержащий сообщение для редактирования.
        :param update_caption: Обновлять ли подпись сообщения.
        :param update_keyboard: Обновлять ли клавиатуру.
        :return: True, если редактирование прошло успешно; иначе False.
        """
        if not self.profile:
            logger.warning(f"Cannot edit profile - no profile loaded for user {self.user_id}")
            return False

        # Определяем целевое сообщение
        target_message = message.message if isinstance(message, CallbackQuery) else message
        if not target_message or not target_message.photo:
            logger.warning(f"Cannot edit message: it's not a photo message or missing")
            return False

        # Формируем обновления
        caption = self._caption_template(self.profile) if update_caption else target_message.caption
        keyboard = self._keyboard_factory(self.profile) if update_keyboard else target_message.reply_markup

        try:
            await self.bot.edit_message_caption(
                chat_id=target_message.chat.id,
                message_id=target_message.message_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"Profile edited for user {self.user_id} (message {target_message.message_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to edit profile message for user {self.user_id}: {e}")
            return False