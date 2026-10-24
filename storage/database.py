# storage/database.py
import aiosqlite
from typing import Optional, Dict, Any
from config import PATH_DB
import logging
import json
from pathlib import Path


logger = logging.getLogger(__name__)

async def create_database() -> None:
    """
    Создает базу данных и таблицу пользователей при первом запуске.
    Вызывать один раз при инициализации бота.
    """
    logger.info("Initializing database")
    # Ensure the database directory exists for local and Docker deployments.
    Path(PATH_DB).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
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
        # Add a provenance flag to existing databases without losing user profiles.
        cursor = await db.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in await cursor.fetchall()}
        if "is_fake" not in user_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN is_fake INTEGER NOT NULL DEFAULT 0"
            )
        if "media_json" not in user_columns:
            await db.execute("ALTER TABLE users ADD COLUMN media_json TEXT")
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

        # Repair mutual flags and counters that may have drifted under the old logic.
        await db.execute("""
            UPDATE likes AS current
            SET is_mutual = CASE
                WHEN current.action IN ('like', 'like_with_message')
                 AND EXISTS (
                    SELECT 1 FROM likes AS reverse
                    WHERE reverse.liker_id = current.liked_id
                      AND reverse.liked_id = current.liker_id
                      AND reverse.action IN ('like', 'like_with_message')
                 )
                THEN 1 ELSE 0
            END
        """)
        await db.execute("""
            UPDATE users
            SET likes_given = (
                SELECT COUNT(*) FROM likes
                WHERE likes.liker_id = users.user_id
                  AND likes.action IN ('like', 'like_with_message')
            )
        """)
        await db.execute("""
            UPDATE users
            SET likes_received = (
                SELECT COUNT(*) FROM likes
                WHERE likes.liked_id = users.user_id
                  AND likes.action IN ('like', 'like_with_message')
            )
        """)
        await db.execute("""
            UPDATE users
            SET mutual_likes = (
                SELECT COUNT(*) FROM likes
                WHERE likes.liker_id = users.user_id AND likes.is_mutual = 1
            )
        """)

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
    city: Optional[str] = None,
    media: Optional[list[Dict[str, str]]] = None,
) -> None:
    media_items = media or [{"type": "photo", "file_id": photo_id}]
    if not 1 <= len(media_items) <= 3:
        raise ValueError("Добавьте от одного до трёх фото или видео.")
    if any(
        not isinstance(item, dict)
        or item.get("type") not in {"photo", "video"}
        or not isinstance(item.get("file_id"), str)
        or not item.get("file_id", "").strip()
        for item in media_items
    ):
        raise ValueError("Поддерживаются только фото и видео с корректными file_id.")

    # Keep photo_id populated for compatibility with existing queries and older clients.
    photo_id = media_items[0]["file_id"]
    media_json = json.dumps(media_items, ensure_ascii=False)

    async with aiosqlite.connect(PATH_DB) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (
                user_id, username, name, age, gender,
                description, photo_id, latitude, longitude, city,
                filter_gender, likes_given, likes_received, mutual_likes, media_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?)
        """, (
            user_id, username, name, age, gender, description, photo_id,
            latitude, longitude, city, media_json
        ))
        await db.commit()


async def is_profile_complete(user_id: int) -> bool:
    """
    Проверяет, заполнен ли профиль пользователя.
    Возвращает True, если все обязательные поля (name, age, gender, description, photo_id) заполнены.
    """
    logger.debug(f"Checking profile completeness for user {user_id}")
    async with aiosqlite.connect(PATH_DB) as db:
        cursor = await db.execute("""
            SELECT name, age, gender, description, photo_id, is_fake
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        
        row = await cursor.fetchone()
        if not row:
            logger.debug(f"Profile not found for user {user_id}")
            return False
        
        # Описание необязательно для реальных и созданных администратором анкет.
        name, age, gender, description, photo_id, is_fake = row
        description_valid = isinstance(description, str) and len(description) <= 500
        is_complete = all([
            name and isinstance(name, str) and len(name.strip()) > 0,
            isinstance(age, int) and 16 <= age <= 30,
            gender and isinstance(gender, str) and len(gender.strip()) > 0,
            description_valid,
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
        logger.debug("Retrieved field '%s' for user %s.", field_name, user_id)
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
    logger.info("Updating field '%s' for user %s.", field_name, user_id)
    
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
    """Delete a real user's profile and repair counters; fake profiles use their own helper."""
    if user_id <= 0:
        return False

    logger.info("Deleting real user profile %s.", user_id)
    async with aiosqlite.connect(PATH_DB) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "DELETE FROM likes WHERE liker_id = ? OR liked_id = ?",
            (user_id, user_id),
        )
        cursor = await db.execute(
            "DELETE FROM users WHERE user_id = ? AND user_id > 0",
            (user_id,),
        )
        deleted = cursor.rowcount > 0
        if deleted:
            # Recompute the counts for real and demo profiles affected by deleted likes.
            await db.execute(
                """
                UPDATE users
                SET likes_given = (
                    SELECT COUNT(*) FROM likes
                    WHERE likes.liker_id = users.user_id
                      AND likes.action IN ('like', 'like_with_message')
                )
                """
            )
            await db.execute(
                """
                UPDATE users
                SET likes_received = (
                    SELECT COUNT(*) FROM likes
                    WHERE likes.liked_id = users.user_id
                      AND likes.action IN ('like', 'like_with_message')
                )
                """
            )
            await db.execute(
                """
                UPDATE users
                SET mutual_likes = (
                    SELECT COUNT(*) FROM likes
                    WHERE likes.liker_id = users.user_id AND likes.is_mutual = 1
                )
                """
            )
        await db.commit()

    if deleted:
        logger.info("Profile deleted for user %s.", user_id)
    else:
        logger.warning("No real profile found to delete for user %s.", user_id)
    return deleted

async def create_fake_profile(
    name: str,
    age: int,
    gender: str,
    description: str,
    photo_id: str,
    latitude: float,
    longitude: float,
    city: Optional[str] = None,
    media: Optional[list[Dict[str, str]]] = None,
) -> int:
    """Create an admin-managed demo profile with up to three photo/video items."""
    if not 16 <= age <= 30:
        raise ValueError("Возраст анкеты должен быть от 16 до 30 лет.")
    if gender not in {"Мужской", "Женский"}:
        raise ValueError("Некорректный пол анкеты.")
    if not name.strip() or len(description.strip()) > 500 or not photo_id:
        raise ValueError("Имя и медиа обязательны; описание должно быть не длиннее 500 символов.")
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise ValueError("Координаты находятся вне допустимого диапазона.")

    media_items = media or [{"type": "photo", "file_id": photo_id}]
    if not 1 <= len(media_items) <= 3:
        raise ValueError("Добавьте от одного до трёх фото или видео.")
    if any(item.get("type") not in {"photo", "video"} or not item.get("file_id") for item in media_items):
        raise ValueError("Поддерживаются только фото и видео.")
    if media_items[0]["type"] != "photo":
        # Legacy photo_id column remains non-empty for compatibility with existing code.
        photo_id = media_items[0]["file_id"]

    media_json = json.dumps(media_items, ensure_ascii=False)
    async with aiosqlite.connect(PATH_DB) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT COALESCE(MIN(user_id), 0) FROM users WHERE user_id < 0"
        )
        current_min_id = (await cursor.fetchone())[0]
        fake_id = min(-1, current_min_id - 1)

        await db.execute(
            """
            INSERT INTO users (
                user_id, username, name, age, gender, description, photo_id,
                latitude, longitude, city, filter_gender, likes_given,
                likes_received, mutual_likes, is_active, is_fake, media_json
            ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 1, 1, ?)
            """,
            (
                fake_id, name.strip(), age, gender, description.strip(), photo_id,
                latitude, longitude, city.strip() if city else None, media_json
            ),
        )
        await db.commit()
    logger.info("Created admin demo profile with internal id %s.", fake_id)
    return fake_id

async def get_fake_profiles() -> list[Dict[str, Any]]:
    """Return demo profiles for the admin panel only."""
    async with aiosqlite.connect(PATH_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT user_id, name, age, gender, city, is_active,
                   likes_given, likes_received, mutual_likes
            FROM users
            WHERE is_fake = 1
            ORDER BY user_id ASC
            """
        )
        return [dict(row) for row in await cursor.fetchall()]


async def delete_fake_profile(fake_id: int) -> bool:
    """Delete a demo profile and its likes; never delete real users here."""
    if fake_id >= 0:
        return False

    async with aiosqlite.connect(PATH_DB) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ? AND is_fake = 1",
            (fake_id,),
        )
        if not await cursor.fetchone():
            await db.rollback()
            return False

        await db.execute(
            "DELETE FROM likes WHERE liker_id = ? OR liked_id = ?",
            (fake_id, fake_id),
        )
        cursor = await db.execute(
            "DELETE FROM users WHERE user_id = ? AND is_fake = 1",
            (fake_id,),
        )
        deleted = cursor.rowcount > 0

        # Repair real-user counters after removing their actions on this demo.
        await db.execute(
            """
            UPDATE users
            SET likes_given = (
                SELECT COUNT(*) FROM likes
                WHERE likes.liker_id = users.user_id
                  AND likes.action IN ('like', 'like_with_message')
            )
            WHERE user_id > 0
            """
        )
        await db.execute(
            """
            UPDATE users
            SET likes_received = (
                SELECT COUNT(*) FROM likes
                WHERE likes.liked_id = users.user_id
                  AND likes.action IN ('like', 'like_with_message')
            )
            WHERE user_id > 0
            """
        )
        await db.execute(
            """
            UPDATE users
            SET mutual_likes = (
                SELECT COUNT(*) FROM likes
                WHERE likes.liker_id = users.user_id AND likes.is_mutual = 1
            )
            WHERE user_id > 0
            """
        )
        await db.commit()
    return deleted
