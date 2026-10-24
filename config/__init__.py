from pathlib import Path
import os

from dotenv import load_dotenv

# Load secrets from this project's config/.env in local runs.
# Docker Compose may also inject these variables via env_file.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / "config" / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
PATH_DB = os.getenv("PATH_DB") or str(BASE_DIR / "data" / "database.db")
ADMIN_ID = os.getenv("ADMIN_ID")
TELEGRAM_LOG_CHANNEL_ID = os.getenv("TELEGRAM_LOG_CHANNEL_ID")

MESSAGE_PROFILE_END = (
    "<b>📭 Новых анкет пока нет</b>\n\n"
    "<i>Загляните позже!</i>"
)

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден. Укажите его в config/.env или в переменных окружения."
    )

FILTER_GENDER_MAP = {
    "filter_all_gender": 0,
    "filter_female_gender": 1,
    "filter_male_gender": 2,
}
