import logging
import math

import aiosqlite

from config import PATH_DB

logger = logging.getLogger(__name__)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance while protecting against float rounding."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    a = min(1.0, max(0.0, a))
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


async def get_next_profile_for_user(
    user_id: int, max_radius_km: float = 2000.0
) -> int | None:
    """Return the nearest eligible profile within the configured search radius.

    Users under 18 are only shown other users under 18. The SQL filters by
    latitude and eligibility; precise distance is calculated in Python so the
    code does not depend on optional SQLite trigonometric extensions.
    """
    if max_radius_km < 0:
        raise ValueError("max_radius_km must be non-negative")

    async with aiosqlite.connect(PATH_DB) as db:
        cursor = await db.execute(
            "SELECT latitude, longitude, filter_gender, age FROM users WHERE user_id = ?",
            (user_id,),
        )
        user_data = await cursor.fetchone()

        if not user_data or user_data[0] is None or user_data[1] is None:
            logger.warning("User %s has no location data.", user_id)
            return None

        lat, lon, filter_gender, age = user_data
        delta_lat = max_radius_km / 111.0
        min_lat = max(-90.0, lat - delta_lat)
        max_lat = min(90.0, lat + delta_lat)

        # Deliberately do not exclude is_fake=1: admin-created seed profiles
        # participate in the same search eligibility rules as real profiles.
        query = """
            SELECT u.user_id, u.latitude, u.longitude
            FROM users AS u
            WHERE u.user_id != ?
              AND u.is_active = 1
              AND u.latitude IS NOT NULL
              AND u.longitude IS NOT NULL
              AND u.age BETWEEN 16 AND 30
              AND u.name IS NOT NULL AND TRIM(u.name) != ''
              AND u.gender IS NOT NULL AND TRIM(u.gender) != ''
              AND (u.is_fake = 1 OR (u.description IS NOT NULL AND TRIM(u.description) != ''))
              AND u.photo_id IS NOT NULL AND TRIM(u.photo_id) != ''
              AND u.latitude BETWEEN ? AND ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM likes AS l
                  WHERE l.liker_id = ? AND l.liked_id = u.user_id
              )
              AND (
                  ? = 0
                  OR (? = 1 AND u.gender IN ('Женский', 'женский', 'female', 'woman'))
                  OR (? = 2 AND u.gender IN ('Мужской', 'мужской', 'male', 'man'))
              )
              AND (
                  (? < 18 AND u.age < 18)
                  OR (? >= 18 AND u.age >= 18)
              )
        """
        params = (
            user_id,
            min_lat,
            max_lat,
            user_id,
            filter_gender,
            filter_gender,
            filter_gender,
            age,
            age,
        )
        cursor = await db.execute(query, params)
        candidates = await cursor.fetchall()

    closest_id = None
    closest_distance = max_radius_km
    for candidate_id, candidate_lat, candidate_lon in candidates:
        distance = _distance_km(lat, lon, candidate_lat, candidate_lon)
        if distance <= closest_distance:
            if closest_id is None or distance < closest_distance:
                closest_id = candidate_id
                closest_distance = distance

    if closest_id is not None:
        logger.debug(
            "Found eligible profile for viewer %s at %.1f km.",
            user_id,
            closest_distance,
        )
    return closest_id
