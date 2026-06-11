import aiosqlite
from typing import List, Tuple
from config import PATH_DB
import logging

logger = logging.getLogger(__name__)


async def is_user_blacklisted(user_id: int) -> bool:
    """
    Проверяет, находится ли пользователь в чёрном списке.
    """
    try:
        async with aiosqlite.connect(PATH_DB) as db:
            cursor = await db.execute(
                "SELECT 1 FROM blacklisted_users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row is not None
    except Exception as e:
        logger.error(f"Error checking blacklist for user {user_id}: {e}")
        return False


async def add_to_blacklist(user_id: int) -> bool:
    """
    Добавляет пользователя в черный список.
    Создает таблицу blacklisted_users, если её нет.
    """
    try:
        async with aiosqlite.connect(PATH_DB) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blacklisted_users (
                    user_id INTEGER PRIMARY KEY,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("INSERT OR IGNORE INTO blacklisted_users (user_id) VALUES (?)", (user_id,))
            await db.commit()
            logger.info(f"User {user_id} added to blacklist")
            return True
    except Exception as e:
        logger.error(f"Error adding user {user_id} to blacklist: {e}")
        return False


async def remove_from_blacklist(user_id: int) -> bool:
    """
    Удаляет пользователя из черного списка.
    """
    try:
        async with aiosqlite.connect(PATH_DB) as db:
            cursor = await db.execute("DELETE FROM blacklisted_users WHERE user_id = ?", (user_id,))
            await db.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"User {user_id} removed from blacklist")
            else:
                logger.info(f"User {user_id} was not in blacklist")
            return deleted
    except Exception as e:
        logger.error(f"Error removing user {user_id} from blacklist: {e}")
        return False


async def get_all_user_ids() -> List[int]:
    """
    Возвращает все user_id из таблицы users.
    """
    try:
        async with aiosqlite.connect(PATH_DB) as db:
            cursor = await db.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error getting all user IDs: {e}")
        return []


async def get_total_users_count() -> int:
    """
    Возвращает общее количество пользователей в базе.
    """
    try:
        async with aiosqlite.connect(PATH_DB) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            result = await cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting total users count: {e}")
        return 0


async def get_blacklisted_users_count() -> int:
    """
    Возвращает количество пользователей в черном списке.
    """
    try:
        async with aiosqlite.connect(PATH_DB) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM blacklisted_users")
            result = await cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting blacklisted users count: {e}")
        return 0


async def get_users_by_gender() -> List[Tuple[str, int]]:
    """
    Возвращает количество пользователей по полу.
    """
    try:
        async with aiosqlite.connect(PATH_DB) as db:
            cursor = await db.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender")
            return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting users count by gender: {e}")
        return []