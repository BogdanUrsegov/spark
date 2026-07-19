import aiosqlite
import logging
from config import PATH_DB

logger = logging.getLogger(__name__)

async def get_next_profile_for_user(user_id: int, max_radius_km: float = 2000.0) -> int | None:
    async with aiosqlite.connect(PATH_DB) as db:
        # 1. Получаем координаты и фильтр текущего пользователя
        cursor = await db.execute(
            "SELECT latitude, longitude, filter_gender FROM users WHERE user_id = ?",
            (user_id,)
        )
        user_data = await cursor.fetchone()
        
        if not user_data or user_data[0] is None or user_data[1] is None:
            logger.warning(f"User {user_id} has no location data.")
            return None

        lat, lon, filter_gender = user_data
        delta = max_radius_km / 111.0
        min_lat, max_lat = lat - delta, lat + delta
        min_lon, max_lon = lon - delta, lon + delta

        # 2. SQL с фильтром по полу и оптимизацией NOT EXISTS
        # Примечание: замените 'female'/'male' на актуальные строковые значения из вашей БД
        query = """
            SELECT u.user_id,
                (6371 * acos(
                    cos(radians(?)) * cos(radians(u.latitude)) *
                    cos(radians(u.longitude) - radians(?)) +
                    sin(radians(?)) * sin(radians(u.latitude))
                )) AS distance
            FROM users u
            WHERE u.user_id != ?
            AND u.is_active = 1
            AND u.latitude IS NOT NULL AND u.longitude IS NOT NULL
            -- Быстрый фильтр по квадрату (Bounding Box)
            AND u.latitude BETWEEN ? AND ?
            AND u.longitude BETWEEN ? AND ?
            -- Исключаем уже оцененных (NOT EXISTS быстрее, чем NOT IN)
            AND NOT EXISTS (
                SELECT 1 FROM likes l WHERE l.liker_id = ? AND l.liked_id = u.user_id
            )
            -- Фильтр по полу
            AND (
                ? = 0 OR 
                (? = 1 AND u.gender IN ('female', 'woman')) OR 
                (? = 2 AND u.gender IN ('male', 'man'))
            )
            ORDER BY distance ASC
            LIMIT 1
        """
        
        params = (
            lat, lon, lat,          # Haversine
            user_id,                # Исключаем себя
            min_lat, max_lat,       # Bounding Box (широта)
            min_lon, max_lon,       # Bounding Box (долгота)
            user_id,                # NOT EXISTS (liker_id)
            filter_gender,          # Фильтр (0 - любой)
            filter_gender,          # Фильтр (1 - девушки)
            filter_gender           # Фильтр (2 - парни)
        )

        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        
        if row:
            logger.debug(f"Found profile {row[0]} for {user_id} (dist: {row[1]:.1f} km)")
            return row[0]
            
        return None