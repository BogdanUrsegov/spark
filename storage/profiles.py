import aiosqlite
import logging
from config import PATH_DB

logger = logging.getLogger(__name__)


async def get_next_profile_for_user(user_id: int, max_radius_km: float = 2000.0) -> int | None:
    """
    Находит ближайшего доступного пользователя в заданном радиусе.
    Возвращает user_id или None, если подходящих анкет нет (или у пользователя нет координат).
    """
    logger.debug(f"Finding nearest profile for user {user_id}")
    
    async with aiosqlite.connect(PATH_DB) as db:
        # 1. Получаем координаты текущего пользователя
        cursor = await db.execute(
            "SELECT latitude, longitude FROM users WHERE user_id = ?",
            (user_id,)
        )
        user_coords = await cursor.fetchone()
        
        # Если у пользователя не указана геопозиция, вернуть None
        # (В хендлере бота нужно будет обработать это и попросить указать геопозицию)
        if not user_coords or user_coords[0] is None or user_coords[1] is None:
            logger.warning(f"User {user_id} has no location data. Cannot find nearest profile.")
            return None

        lat, lon = user_coords

        # 2. Оптимизация: Bounding Box (1 градус широты ≈ 111 км)
        # Создаём квадрат вокруг пользователя, чтобы отсеять 99% записей до сложного расчёта
        delta = max_radius_km / 111.0
        min_lat, max_lat = lat - delta, lat + delta
        min_lon, max_lon = lon - delta, lon + delta

        # 3. SQL-запрос с формулой Haversine (расстояние в км)
        query = """
            SELECT user_id,
                (6371 * acos(
                    cos(radians(?)) * cos(radians(latitude)) *
                    cos(radians(longitude) - radians(?)) +
                    sin(radians(?)) * sin(radians(latitude))
                )) AS distance
            FROM users
            WHERE user_id != ?
            AND user_id NOT IN (
                SELECT liked_id FROM likes WHERE liker_id = ?
            )
            AND latitude IS NOT NULL AND longitude IS NOT NULL
            AND is_active = 1
            -- Быстрый фильтр по квадрату (Bounding Box)
            AND latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            ORDER BY distance ASC
            LIMIT 1
        """
        
        params = (
            lat, lon, lat,          # Параметры для формулы Haversine
            user_id, user_id,       # Исключаем себя и уже оцененные анкеты
            min_lat, max_lat,       # Bounding Box (широта)
            min_lon, max_lon        # Bounding Box (долгота)
        )

        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        
        if row:
            target_id = row[0]
            distance = row[1]
            logger.debug(f"Found nearest profile for user {user_id}: {target_id} (distance: {distance:.1f} km)")
            return target_id
            
        logger.debug(f"No available profiles within {max_radius_km} km for user {user_id}")
        return None