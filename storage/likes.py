import logging

import aiosqlite

from config import PATH_DB

logger = logging.getLogger(__name__)

LIKE_ACTIONS = {"like", "like_with_message"}
VALID_ACTIONS = LIKE_ACTIONS | {"dislike"}


async def save_action(
    liker_id: int,
    liked_id: int,
    action: str,
    message: str | None = None,
) -> bool:
    """Save a user's decision and keep directional/mutual counters consistent."""
    if liker_id == liked_id:
        logger.warning("Ignoring self-directed profile action.")
        return False
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported like action: {action}")

    new_is_like = action in LIKE_ACTIONS

    async with aiosqlite.connect(PATH_DB) as db:
        # Read both directions before changing the current decision.
        cursor = await db.execute(
            "SELECT action FROM likes WHERE liker_id = ? AND liked_id = ?",
            (liker_id, liked_id),
        )
        current = await cursor.fetchone()
        old_action = current[0] if current else None
        old_is_like = old_action in LIKE_ACTIONS

        cursor = await db.execute(
            "SELECT action FROM likes WHERE liker_id = ? AND liked_id = ?",
            (liked_id, liker_id),
        )
        reverse = await cursor.fetchone()
        reverse_is_like = bool(reverse and reverse[0] in LIKE_ACTIONS)

        mutual_before = old_is_like and reverse_is_like
        mutual_after = new_is_like and reverse_is_like

        await db.execute(
            """
            INSERT INTO likes (liker_id, liked_id, action, message, is_mutual)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(liker_id, liked_id) DO UPDATE SET
                action = excluded.action,
                message = excluded.message,
                is_mutual = excluded.is_mutual
            """,
            (liker_id, liked_id, action, message, int(mutual_after)),
        )

        # Count only transitions between non-like and like, not repeated taps
        # or switching from 'like' to 'like_with_message'.
        if old_is_like != new_is_like:
            delta = 1 if new_is_like else -1
            await db.execute(
                "UPDATE users SET likes_given = MAX(0, likes_given + ?) WHERE user_id = ?",
                (delta, liker_id),
            )
            await db.execute(
                "UPDATE users SET likes_received = MAX(0, likes_received + ?) WHERE user_id = ?",
                (delta, liked_id),
            )

        # Mutuality belongs to the relationship, so update both directions and
        # adjust both users' counters only when the relationship changes state.
        await db.execute(
            """
            UPDATE likes SET is_mutual = ?
            WHERE (liker_id = ? AND liked_id = ?)
               OR (liker_id = ? AND liked_id = ?)
            """,
            (int(mutual_after), liker_id, liked_id, liked_id, liker_id),
        )

        if mutual_before != mutual_after:
            delta = 1 if mutual_after else -1
            await db.execute(
                "UPDATE users SET mutual_likes = MAX(0, mutual_likes + ?) WHERE user_id = ?",
                (delta, liker_id),
            )
            await db.execute(
                "UPDATE users SET mutual_likes = MAX(0, mutual_likes + ?) WHERE user_id = ?",
                (delta, liked_id),
            )

        await db.commit()

    logger.info("Profile action saved (%s; mutual=%s).", action, mutual_after)
    return new_is_like and mutual_after
