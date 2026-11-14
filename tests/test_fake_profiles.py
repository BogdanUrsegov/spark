import importlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

# The configuration module validates BOT_TOKEN during import; tests use a dummy token.
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("ADMIN_ID", "1")
os.environ.setdefault("TELEGRAM_LOG_CHANNEL_ID", "-1001234567890")

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from viewers.profile_displayer import ProfileDisplayer

database = importlib.import_module("storage.database")
likes_storage = importlib.import_module("storage.likes")
profiles_storage = importlib.import_module("storage.profiles")


class FakeProfileStorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.original_db_path = database.PATH_DB
        self.original_likes_db_path = likes_storage.PATH_DB
        self.original_profiles_db_path = profiles_storage.PATH_DB
        database.PATH_DB = self.db_path
        likes_storage.PATH_DB = self.db_path
        profiles_storage.PATH_DB = self.db_path
        await database.create_database()

    async def asyncTearDown(self):
        database.PATH_DB = self.original_db_path
        likes_storage.PATH_DB = self.original_likes_db_path
        profiles_storage.PATH_DB = self.original_profiles_db_path
        self.temp_dir.cleanup()

    async def _create_real_profile(self, user_id=10001):
        await database.add_new_profile(
            user_id=user_id,
            username="real_user",
            name="Real",
            age=24,
            gender="Мужской",
            description="Real account",
            photo_id="telegram-photo-id",
            latitude=55.75,
            longitude=37.61,
            city="Москва",
        )
        return user_id

    async def _create_fake_profile(self):
        return await database.create_fake_profile(
            name="Demo",
            age=22,
            gender="Женский",
            description="Clearly marked test profile",
            photo_id="demo-photo-id",
            latitude=55.76,
            longitude=37.62,
            city="Москва",
        )

    async def test_fake_profiles_receive_negative_ids_and_are_listed(self):
        fake_id = await self._create_fake_profile()

        self.assertLess(fake_id, 0)
        profile = await database.get_user_profile(fake_id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["is_fake"], 1)

        listed = await database.get_fake_profiles()
        self.assertEqual([item["user_id"] for item in listed], [fake_id])

    async def test_fake_profile_can_skip_description_and_store_one_media(self):
        media = [{"type": "photo", "file_id": "photo-1"}]
        fake_id = await database.create_fake_profile(
            name="Demo",
            age=22,
            gender="Женский",
            description="",
            photo_id="photo-1",
            latitude=55.76,
            longitude=37.62,
            city="Москва",
            media=media,
        )

        profile = await database.get_user_profile(fake_id)
        self.assertEqual(profile["description"], "")
        self.assertTrue(await database.is_profile_complete(fake_id))
        self.assertEqual(__import__("json").loads(profile["media_json"]), media)
        self.assertEqual(
            await profiles_storage.get_next_profile_for_user(await self._create_real_profile()),
            fake_id,
        )
        with self.assertRaises(ValueError):
            await database.create_fake_profile(
                name="Another",
                age=22,
                gender="Женский",
                description="",
                photo_id="photo-1",
                latitude=55.76,
                longitude=37.62,
                city="Москва",
                media=media + [{"type": "photo", "file_id": "photo-2"}],
            )

    async def test_real_profile_stores_one_media_and_rejects_multiple(self):
        viewer_id = await self._create_real_profile()
        await database.add_new_profile(
            user_id=10002,
            username="real_user_with_media",
            name="Real User",
            age=23,
            gender="Женский",
            description="",
            photo_id="real-photo-1",
            latitude=55.76,
            longitude=37.62,
            city="Москва",
            media=[{"type": "photo", "file_id": "real-photo-1"}],
        )

        profile = await database.get_user_profile(10002)
        self.assertEqual(__import__("json").loads(profile["media_json"]), [
            {"type": "photo", "file_id": "real-photo-1"}
        ])
        self.assertTrue(await database.is_profile_complete(10002))
        self.assertEqual(await profiles_storage.get_next_profile_for_user(viewer_id), 10002)
        with self.assertRaises(ValueError):
            await database.add_new_profile(
                user_id=10003,
                username="too_many_media",
                name="Too Many",
                age=23,
                gender="Женский",
                description="",
                photo_id="photo-1",
                media=[
                    {"type": "photo", "file_id": "photo-1"},
                    {"type": "photo", "file_id": "photo-2"},
                ],
            )

    async def test_profile_media_replacement_requires_one_item(self):
        user_id = await self._create_real_profile()
        self.assertTrue(await database.set_user_profile_media(
            user_id, [{"type": "video", "file_id": "new-video"}]
        ))
        profile = await database.get_user_profile(user_id)
        self.assertEqual(profile["photo_id"], "new-video")
        self.assertEqual(__import__("json").loads(profile["media_json"]), [
            {"type": "video", "file_id": "new-video"}
        ])
        with self.assertRaises(ValueError):
            await database.set_user_profile_media(user_id, [
                {"type": "photo", "file_id": "photo-1"},
                {"type": "video", "file_id": "video-1"},
            ])

    async def test_profile_displayer_attaches_keyboard_to_single_video(self):
        chat_id = 190001
        sent = SimpleNamespace(message_id=501)
        bot = SimpleNamespace(
            send_video=AsyncMock(return_value=sent),
            send_photo=AsyncMock(return_value=sent),
        )
        displayer = ProfileDisplayer(bot, chat_id)
        displayer.profile = {
            "user_id": chat_id,
            "photo_id": "video-1",
            "media_json": __import__("json").dumps([
                {"type": "video", "file_id": "video-1"}
            ]),
        }
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Мой профиль", callback_data="show_my_profile")
        ]])

        await displayer._send_profile_media("<b>Профиль</b>", keyboard)

        bot.send_video.assert_awaited_once_with(
            chat_id=chat_id,
            video="video-1",
            caption="<b>Профиль</b>",
            reply_markup=keyboard,
            reply_to_message_id=None,
        )
        bot.send_photo.assert_not_awaited()

    async def test_profile_displayer_uses_first_item_from_legacy_multi_media(self):
        chat_id = 190002
        sent = SimpleNamespace(message_id=502)
        bot = SimpleNamespace(
            send_photo=AsyncMock(return_value=sent),
            send_video=AsyncMock(return_value=sent),
        )
        displayer = ProfileDisplayer(bot, chat_id)
        displayer.profile = {
            "user_id": chat_id,
            "photo_id": "photo-1",
            "media_json": __import__("json").dumps([
                {"type": "photo", "file_id": "photo-1"},
                {"type": "video", "file_id": "video-1"},
                {"type": "photo", "file_id": "photo-2"},
            ]),
        }

        await displayer._send_profile_media("Профиль", InlineKeyboardMarkup(inline_keyboard=[]))

        bot.send_photo.assert_awaited_once()
        self.assertEqual(bot.send_photo.await_args.kwargs["photo"], "photo-1")
        bot.send_video.assert_not_awaited()

    async def test_fake_delete_cannot_delete_real_users(self):
        real_id = await self._create_real_profile()
        fake_id = await self._create_fake_profile()

        self.assertFalse(await database.delete_fake_profile(real_id))
        self.assertFalse(await database.delete_user_profile(fake_id))
        self.assertIsNotNone(await database.get_user_profile(real_id))

        self.assertTrue(await database.delete_fake_profile(fake_id))
        self.assertIsNone(await database.get_user_profile(fake_id))
        self.assertIsNotNone(await database.get_user_profile(real_id))

    async def test_fake_profiles_are_returned_by_the_normal_search(self):
        real_id = await self._create_real_profile()
        fake_id = await self._create_fake_profile()

        next_profile_id = await profiles_storage.get_next_profile_for_user(real_id)

        self.assertEqual(next_profile_id, fake_id)

    async def test_repeated_likes_do_not_inflate_counters(self):
        real_id = await self._create_real_profile()
        fake_id = await self._create_fake_profile()

        self.assertFalse(await likes_storage.save_action(real_id, fake_id, "like"))
        self.assertFalse(await likes_storage.save_action(real_id, fake_id, "like"))

        real = await database.get_user_profile(real_id)
        fake = await database.get_user_profile(fake_id)
        self.assertEqual(real["likes_given"], 1)
        self.assertEqual(fake["likes_received"], 1)

        self.assertFalse(await likes_storage.save_action(real_id, fake_id, "dislike"))
        real = await database.get_user_profile(real_id)
        fake = await database.get_user_profile(fake_id)
        self.assertEqual(real["likes_given"], 0)
        self.assertEqual(fake["likes_received"], 0)


if __name__ == "__main__":
    unittest.main()
