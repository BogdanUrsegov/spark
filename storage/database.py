# storage/database.py
import aiosqlite
from typing import Optional, Dict, Any
from config import PATH_DB
import logging


logger = logging.getLogger(__name__)

async def create_database() -> None:
    """
    Создает базу данных и таблицу пользователей при первом запуске.
    Вызывать один раз при инициализации бота.
    """
    logger.info("Initializing database")
    async with aiosqlite.connect(PATH_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                description TEXT NOT NULL,
                photo_id TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                city TEXT,
                filter_gender INTEGER DEFAULT 0,  -- 0 - без фильтра, 1 - только девушки, 2 - только парни
                likes_given INTEGER DEFAULT 0,
                likes_received INTEGER DEFAULT 0,
                mutual_likes INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)
        logger.info("Users table created or already exists.")
        
        # Таблица лайков (основная для логики матчинга)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                liker_id INTEGER NOT NULL,
                liked_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('like', 'dislike', 'like_with_message')),
                message TEXT,
                is_mutual BOOLEAN DEFAULT 0,
                notified BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(liker_id, liked_id),
                FOREIGN KEY(liked_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(liker_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        logger.info("Likes table created or already exists.")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS blacklisted_users (
                user_id INTEGER PRIMARY KEY,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Blacklisted users table created or already exists.")

        await db.commit()
        logger.info("Database initialization completed")


async def add_new_profile(
    user_id: int,
    username: Optional[str],
    name: str,
    age: int,
    gender: str,
    description: str,
    photo_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None
) -> None:
    async with aiosqlite.connect(PATH_DB) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (
                user_id, username, name, age, gender, 
                description, photo_id, latitude, longitude, city,
                filter_gender, likes_given, likes_received, mutual_likes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
        """, (user_id, username, name, age, gender, description, photo_id, latitude, longitude, city))
        await db.commit()


async def is_profile_complete(user_id: int) -> bool:
    """
    Проверяет, заполнен ли профиль пользователя.
    Возвращает True, если все обязательные поля (name, age, gender, description, photo_id) заполнены.
    """
    logger.debug(f"Checking profile completeness for user {user_id}")
    async with aiosqlite.connect(PATH_DB) as db:
        cursor = await db.execute("""
            SELECT name, age, gender, description, photo_id
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        
        row = await cursor.fetchone()
        if not row:
            logger.debug(f"Profile not found for user {user_id}")
            return False
        
        # Проверяем, что все обязательные поля не NULL и не пустые
        name, age, gender, description, photo_id = row
        is_complete = all([
            name and isinstance(name, str) and len(name.strip()) > 0,
            isinstance(age, int) and 16 <= age <= 30,
            gender and isinstance(gender, str) and len(gender.strip()) > 0,
            description and isinstance(description, str) and len(description.strip()) > 0,
            photo_id and isinstance(photo_id, str) and len(photo_id.strip()) > 0
        ])
        
        logger.debug(f"Profile completeness for user {user_id}: {is_complete}")
        return is_complete


async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает полные данные профиля пользователя.
    Возвращает словарь с полями или None, если профиль не существует.
    """
    logger.debug(f"Retrieving profile for user {user_id}")
    async with aiosqlite.connect(PATH_DB) as db:
        db.row_factory = aiosqlite.Row  # Включаем доступ по именам колонок
        cursor = await db.execute("""
            SELECT * FROM users WHERE user_id = ?
        """, (user_id,))
        
        row = await cursor.fetchone()
        if not row:
            logger.debug(f"Profile not found for user {user_id}")
            return None
        
        profile = dict(row)
        logger.debug(f"Profile retrieved for user {user_id}")
        return profile


async def get_user_field(user_id: int, field_name: str) -> any:
    """
    Получает значение одного поля пользователя из таблицы `users`.
    
    :param user_id: ID пользователя (Telegram user_id)
    :param field_name: Название столбца в таблице (например: "name", "age", "gender")
    :return: Значение поля или None, если пользователь не найден / поле пустое
    
    ⚠️ Важно: field_name не экранируется — должен быть безопасным (из белого списка)!
    """
    logger.debug(f"Retrieving field '{field_name}' for user {user_id}")
    
    # Защита от SQL-инъекций: разрешаем только известные поля
    allowed_fields = {
        "user_id", "username", "name", "age", "gender",
        "description", "photo_id", "likes_given",
        "likes_received", "mutual_likes", "is_active",
        "latitude", "longitude", "city", "filter_gender"
    }
    
    if field_name not in allowed_fields:
        logger.error(f"Invalid field name requested: {field_name}")
        raise ValueError(f"Недопустимое имя поля: {field_name}")

    async with aiosqlite.connect(PATH_DB) as db:
        cursor = await db.execute(
            f"SELECT {field_name} FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        value = row[0] if row else None
        logger.debug(f"Retrieved field '{field_name}' for user {user_id}: {value}")
        return value


# Список разрешённых полей для редактирования (белый список)
ALLOWED_EDITABLE_FIELDS = {
    "name", "age", "gender", "description", "photo_id", 
    "city", "latitude", "longitude", "is_active", "filter_gender"
}


async def update_user_field(user_id: int, field_name: str, value) -> bool:
    """
    Обновляет одно поле профиля пользователя в таблице `users`.

    :param user_id: ID пользователя (Telegram user_id)
    :param field_name: Название поля (должно быть в ALLOWED_EDITABLE_FIELDS)
    :param value: Новое значение (строка, число и т.д.)
    :return: True, если обновление прошло успешно, иначе False

    ⚠️ Безопасность: field_name проверяется по белому списку,
    чтобы избежать SQL-инъекций (поля нельзя параметризовать в SQLite).
    """
    logger.info(f"Updating field '{field_name}' for user {user_id} with value '{value}'")
    
    if field_name not in ALLOWED_EDITABLE_FIELDS:
        logger.error(f"Attempt to edit forbidden field: {field_name}")
        raise ValueError(f"Запрещено редактировать поле: {field_name}")

    try:
        async with aiosqlite.connect(PATH_DB) as db:
            await db.execute(
                f"UPDATE users SET {field_name} = ? WHERE user_id = ?",
                (value, user_id)
            )
            await db.commit()
            # Проверяем, была ли затронута хотя бы одна строка
            updated = db.total_changes > 0
            if updated:
                logger.debug(f"Field '{field_name}' updated successfully for user {user_id}")
            else:
                logger.warning(f"No rows were updated when updating field '{field_name}' for user {user_id}")
            return updated
    except Exception as e:
        logger.error(f"Error updating field {field_name} for user_id={user_id}: {e}")
        return False


async def delete_user_profile(user_id: int) -> bool:
    logger.info(f"Deleting profile for user {user_id}")
    async with aiosqlite.connect(PATH_DB) as db:
        # Удаляем лайки, где пользователь — liker или liked
        await db.execute("DELETE FROM likes WHERE liker_id = ? OR liked_id = ?", (user_id, user_id))

        # Удаляем сам профиль
        cursor = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

        # cursor.rowcount — количество удалённых строк
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Profile deleted for user {user_id}")
        else:
            logger.warning(f"No profile found to delete for user {user_id}")
        return deleted