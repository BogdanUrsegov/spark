import aiosqlite
import logging
from config import PATH_DB

logger = logging.getLogger(__name__)

async def save_action(liker_id: int, liked_id: int, action: str, message: str | None = None) -> bool:
    logger.info(f"Saving action: {action} from {liker_id} to {liked_id}")

    is_like = action in ("like", "like_with_message")
    mutual_before = False
    mutual_after = False

    async with aiosqlite.connect(PATH_DB) as db:
        # --- 1. Сохраняем/обновляем запись ---
        await db.execute("""
            INSERT INTO likes (liker_id, liked_id, action, message)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(liker_id, liked_id) DO UPDATE SET
                action = excluded.action,
                message = excluded.message
        """, (liker_id, liked_id, action, message))

        # --- 2. Обновляем счётчики лайков (только для лайков) ---
        if is_like:
            await db.execute("UPDATE users SET likes_given = likes_given + 1 WHERE user_id = ?", (liker_id,))
            await db.execute("UPDATE users SET likes_received = likes_received + 1 WHERE user_id = ?", (liked_id,))

        # --- 3. Проверяем взаимность ДО и ПОСЛЕ ---
        # Проверяем, была ли взаимность до этого действия
        cursor = await db.execute("""
            SELECT is_mutual FROM likes
            WHERE (liker_id = ? AND liked_id = ?)
        """, (liker_id, liked_id))
        row = await cursor.fetchone()
        mutual_before = bool(row and row[0]) if row else False

        # Определяем, есть ли взаимность СЕЙЧАС
        if is_like:
            cursor = await db.execute("""
                SELECT 1 FROM likes
                WHERE liker_id = ? AND liked_id = ?
                  AND action IN ('like', 'like_with_message')
            """, (liked_id, liker_id))
            mutual_after = (await cursor.fetchone()) is not None
        else:
            mutual_after = False

        # --- 4. Обновляем is_mutual в обеих записях ---
        await db.execute("""
            UPDATE likes
            SET is_mutual = ?
            WHERE (liker_id = ? AND liked_id = ?)
               OR (liker_id = ? AND liked_id = ?)
        """, (int(mutual_after), liker_id, liked_id, liked_id, liker_id))

        # --- 5. Обновляем mutual_likes в users, если состояние изменилось ---
        if mutual_before != mutual_after:
            delta = 1 if mutual_after else -1
            # Обновляем счётчик у обоих пользователей
            await db.execute("UPDATE users SET mutual_likes = mutual_likes + ? WHERE user_id = ?", (delta, liker_id))
            await db.execute("UPDATE users SET mutual_likes = mutual_likes + ? WHERE user_id = ?", (delta, liked_id))
            logger.debug(f"mutual_likes adjusted by {delta} for {liker_id} and {liked_id}")

        await db.commit()
        logger.info(f"Action {action} from {liker_id} to {liked_id} saved. Mutual = {mutual_after}")
    
    return is_like and mutual_after