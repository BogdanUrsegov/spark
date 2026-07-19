from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()

# Получаем токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
PATH_DB = os.getenv("PATH_DB")
ADMIN_ID = os.getenv("ADMIN_ID")
TELEGRAM_LOG_CHANNEL_ID = os.getenv("TELEGRAM_LOG_CHANNEL_ID")
MESSAGE_PROFILE_END = (
    "<b>📭 Новых анкет пока нет</b>\n\n"
    "<i>Загляните позже!</i>"
)
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Проверьте файл .env")


FILTER_GENDER_MAP = {
    "filter_all_gender":    0,
    "filter_female_gender": 1,
    "filter_male_gender":   2,
}
