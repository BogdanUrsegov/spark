import html
import logging
import re

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from states import AdminStates
from keyboards import get_location_keyboard
from storage import create_fake_profile, delete_fake_profile, get_fake_profiles
from utils import contains_forbidden_content, get_city_by_coords

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return bool(ADMIN_ID) and str(user_id) == str(ADMIN_ID)


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ])


def _gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужской", callback_data="admin_fake_gender:Мужской"),
            InlineKeyboardButton(text="👩 Женский", callback_data="admin_fake_gender:Женский"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")],
    ])


FAKE_PROFILES_PER_PAGE = 10


def _fake_profiles_keyboard(
    profiles: list[dict], *, page: int = 0
) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(profiles) + FAKE_PROFILES_PER_PAGE - 1) // FAKE_PROFILES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * FAKE_PROFILES_PER_PAGE
    page_profiles = profiles[start:start + FAKE_PROFILES_PER_PAGE]

    rows = [
        [InlineKeyboardButton(text="➕ Создать тестовую анкету", callback_data="admin_fake_create")]
    ]
    for profile in page_profiles:
        name = profile["name"]
        label = f"{name[:22]} ({profile['age']})"
        fake_id = profile["user_id"]
        rows.append([
            InlineKeyboardButton(text=f"👤 {label}", callback_data=f"admin_fake_view:{fake_id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"admin_fake_delete_prompt:{fake_id}"),
        ])

    if total_pages > 1:
        navigation = []
        if page > 0:
            navigation.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_fake_profiles:{page - 1}"))
        navigation.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=f"admin_fake_profiles:{page}"))
        if page < total_pages - 1:
            navigation.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"admin_fake_profiles:{page + 1}"))
        rows.append(navigation)

    rows.append([InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _fake_profile_actions_keyboard(fake_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить тестовую анкету", callback_data=f"admin_fake_delete_prompt:{fake_id}")],
        [InlineKeyboardButton(text="⬅️ К списку анкет", callback_data="admin_fake_profiles")],
    ])


def _delete_confirmation_keyboard(fake_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin_fake_delete_confirm:{fake_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_fake_profiles")],
    ])


async def _show_fake_profiles(message: Message, *, edit: bool = False, page: int = 0) -> None:
    profiles = await get_fake_profiles()
    total_pages = max(1, (len(profiles) + FAKE_PROFILES_PER_PAGE - 1) // FAKE_PROFILES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    if profiles:
        text = (
            "🎭 <b>Тестовые анкеты</b>\n\n"
            f"Создано: <b>{len(profiles)}</b>\n"
            "Такие анкеты помогают заполнять результаты обычного поиска."
        )
    else:
        text = (
            "🎭 <b>Тестовые анкеты</b>\n\n"
            "Пока нет ни одной тестовой анкеты.\n"
            "Нажмите «Создать», чтобы вручную заполнить профиль."
        )

    if total_pages > 1:
        text += f"\nСтраница: <b>{page + 1}/{total_pages}</b>"

    if edit:
        await message.edit_text(text, reply_markup=_fake_profiles_keyboard(profiles, page=page))
    else:
        await message.answer(text, reply_markup=_fake_profiles_keyboard(profiles, page=page))


@router.callback_query(F.data == "admin_fake_profiles")
async def fake_profiles_list(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return
    await state.clear()
    await _show_fake_profiles(callback.message, edit=not bool(callback.message.photo))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_fake_profiles:"))
async def fake_profiles_page(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Некорректная страница", show_alert=True)
        return
    await state.clear()
    await _show_fake_profiles(callback.message, edit=True, page=page)
    await callback.answer()


@router.callback_query(F.data == "admin_fake_create")
async def fake_profile_create_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminStates.fake_profile_name)
    await callback.message.edit_text(
        "➕ <b>Создание тестовой анкеты — шаг 1/6</b>\n\n"
        "Введите имя (2–30 символов).\n"
        "Профиль будет участвовать в обычном поиске наравне с реальными анкетами.",
        reply_markup=_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.fake_profile_name)
async def fake_profile_name(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    name = (message.text or "").strip()
    if (
        not 2 <= len(name) <= 30
        or not re.fullmatch(r"[а-яА-ЯёЁa-zA-Z ]+", name)
        or contains_forbidden_content(name)
    ):
        await message.answer("❌ Имя должно быть длиной 2–30 символов, без ссылок и @. Попробуйте ещё раз.")
        return
    await state.update_data(fake_name=name)
    await state.set_state(AdminStates.fake_profile_age)
    await message.answer("🔢 <b>Шаг 2/6.</b> Введите возраст (16–30).", reply_markup=_cancel_keyboard())


@router.message(AdminStates.fake_profile_age)
async def fake_profile_age(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    raw_age = (message.text or "").strip()
    if not raw_age.isdigit() or not 16 <= int(raw_age) <= 30:
        await message.answer("❌ Возраст должен быть целым числом от 16 до 30. Попробуйте ещё раз.")
        return
    await state.update_data(fake_age=int(raw_age))
    await state.set_state(AdminStates.fake_profile_gender)
    await message.answer("👤 <b>Шаг 3/6.</b> Выберите пол:", reply_markup=_gender_keyboard())


@router.callback_query(AdminStates.fake_profile_gender, F.data.startswith("admin_fake_gender:"))
async def fake_profile_gender(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return
    gender = callback.data.split(":", 1)[1]
    if gender not in {"Мужской", "Женский"}:
        await callback.answer("❌ Некорректный вариант", show_alert=True)
        return
    await state.update_data(fake_gender=gender)
    await state.set_state(AdminStates.fake_profile_description)
    await callback.message.edit_text(
        f"Выбрано: <b>{gender}</b>\n\n"
        "💬 <b>Шаг 4/6.</b> Введите описание анкеты (до 500 символов).",
        reply_markup=_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.fake_profile_description)
async def fake_profile_description(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    description = (message.text or "").strip()
    if not description or len(description) > 500 or contains_forbidden_content(description):
        await message.answer("❌ Описание должно содержать 1–500 символов, без ссылок и @. Попробуйте ещё раз.")
        return
    await state.update_data(fake_description=description)
    await state.set_state(AdminStates.fake_profile_location)
    await message.answer(
        "📍 <b>Шаг 5/6.</b> Поделитесь геопозицией кнопкой ниже — как при обычном заполнении анкеты.\n"
        "Город определится автоматически по координатам.",
        reply_markup=get_location_keyboard(False),
    )


@router.message(AdminStates.fake_profile_location, F.location)
async def fake_profile_location(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return

    latitude = message.location.latitude
    longitude = message.location.longitude
    processing_message = await message.answer("🔄 Определяю город по геопозиции…")
    city = await get_city_by_coords(latitude, longitude)
    await state.update_data(
        fake_latitude=latitude,
        fake_longitude=longitude,
        fake_city=city if city != "Неизвестно" else None,
    )
    city_text = f"🏙 Город определён: <b>{html.escape(city)}</b>\n\n" if city != "Неизвестно" else ""
    await processing_message.edit_text(
        "✅ <b>Геопозиция получена.</b>\n\n"
        f"{city_text}"
        "📸 <b>Шаг 6/6.</b> Отправьте фотографию для тестовой анкеты как обычное фото (не файлом).",
    )
    await state.set_state(AdminStates.fake_profile_photo)
    await message.answer(
        "После сохранения анкета будет участвовать в обычном поиске с учётом пола, возраста и расстояния. "
        "Анкета будет участвовать в обычном поиске с учётом фильтров.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AdminStates.fake_profile_location)
async def fake_profile_location_invalid(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        await message.answer("Создание тестовой анкеты отменено.", reply_markup=ReplyKeyboardRemove())
        await message.answer("🎭 <b>Управление тестовыми анкетами</b>", reply_markup=_fake_profiles_keyboard(await get_fake_profiles()))
        return
    await message.answer(
        "❌ Нажмите кнопку «📍 Поделиться геопозицией» и отправьте своё местоположение.",
        reply_markup=get_location_keyboard(False),
    )


@router.message(AdminStates.fake_profile_photo, F.photo)
async def fake_profile_photo(message: Message, state: FSMContext, bot: Bot):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    try:
        fake_id = await create_fake_profile(
            name=data["fake_name"],
            age=data["fake_age"],
            gender=data["fake_gender"],
            description=data["fake_description"],
            photo_id=photo_id,
            latitude=data["fake_latitude"],
            longitude=data["fake_longitude"],
            city=data.get("fake_city"),
        )
    except (KeyError, ValueError) as exc:
        logger.warning("Admin demo profile validation failed: %s", type(exc).__name__)
        await message.answer(f"❌ Не удалось создать анкету: {html.escape(str(exc))}")
        await state.clear()
        return
    except Exception:
        logger.exception("Could not save an admin demo profile.")
        await message.answer("❌ Ошибка сохранения. Проверьте логи и попробуйте снова.")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        f"✅ <b>Тестовая анкета создана.</b>\n\n"
        f"Внутренний ID: <code>{fake_id}</code>\n"
        f"Имя: <b>{html.escape(data['fake_name'])}</b>\n"
    )

    # Show the saved profile to the administrator with dedicated management buttons.
    from viewers import ProfileDisplayer
    displayer = await ProfileDisplayer.create(bot, message.from_user.id, fake_id)
    if displayer and displayer.profile:
        displayer.with_data_for_admin().with_keyboard(
            lambda profile: _fake_profile_actions_keyboard(profile["user_id"])
        )
        await displayer.send()
    await message.answer("🎭 <b>Управление тестовыми анкетами</b>", reply_markup=_fake_profiles_keyboard(await get_fake_profiles()))


@router.message(AdminStates.fake_profile_photo)
async def fake_profile_photo_invalid(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("❌ Нужна фотография, отправленная как обычное фото Telegram, не документом.")


@router.callback_query(F.data.startswith("admin_fake_view:"))
async def fake_profile_view(callback: CallbackQuery, bot: Bot):
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return
    try:
        fake_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Некорректный ID", show_alert=True)
        return
    profiles = await get_fake_profiles()
    if not any(profile["user_id"] == fake_id for profile in profiles):
        await callback.answer("Анкета не найдена", show_alert=True)
        return
    from viewers import ProfileDisplayer
    displayer = await ProfileDisplayer.create(bot, callback.from_user.id, fake_id)
    if displayer and displayer.profile:
        displayer.with_data_for_admin().with_keyboard(
            lambda profile: _fake_profile_actions_keyboard(profile["user_id"])
        )
        await displayer.send_over(reply_to=callback, delete_previous=False)
        await callback.answer()
    else:
        await callback.answer("Анкета не найдена", show_alert=True)


@router.callback_query(F.data.startswith("admin_fake_delete_prompt:"))
async def fake_profile_delete_prompt(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return
    try:
        fake_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Некорректный ID", show_alert=True)
        return
    profiles = await get_fake_profiles()
    profile = next((item for item in profiles if item["user_id"] == fake_id), None)
    if not profile:
        await callback.answer("Анкета не найдена", show_alert=True)
        return
    await callback.message.answer(
        "⚠️ <b>Удалить тестовую анкету?</b>\n\n"
        f"{html.escape(profile['name'])}, {profile['age']} лет\n"
        "Связанные с ней лайки тоже будут удалены.",
        reply_markup=_delete_confirmation_keyboard(fake_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_fake_delete_confirm:"))
async def fake_profile_delete_confirm(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав доступа", show_alert=True)
        return
    try:
        fake_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Некорректный ID", show_alert=True)
        return
    deleted = await delete_fake_profile(fake_id)
    if deleted:
        await callback.answer("Тестовая анкета удалена")
        await callback.message.edit_text("✅ Тестовая анкета и связанные лайки удалены.")
        profiles = await get_fake_profiles()
        page = 0
        if profiles:
            page = min(
                max(0, int(callback.data.rsplit(":", 1)[1]) if ":" in callback.data else 0),
                (len(profiles) - 1) // FAKE_PROFILES_PER_PAGE,
            )
        await callback.message.answer(
            "🎭 <b>Тестовые анкеты</b>",
            reply_markup=_fake_profiles_keyboard(profiles, page=page),
        )
    else:
        await callback.answer("Анкета не найдена или это реальный пользователь", show_alert=True)
