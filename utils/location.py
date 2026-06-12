import asyncio
import aiohttp
import logging
from config import TELEGRAM_LOG_CHANNEL_ID


logger = logging.getLogger(__name__)

async def get_city_by_coords(lat: float, lon: float, max_retries: int = 3) -> str:
    """
    Определяет город по координатам через Nominatim (OSM) с защитой от лимитов.
    """
    # zoom=10 помогает получить уровень города, а не конкретной улицы
    from main import bot
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&accept-language=ru&zoom=10"
    
    # ВАЖНО: Nominatim строго требует корректный User-Agent
    headers = {"User-Agent": "StudentDatingBot/1.0 (your_bot_username)"}
    
    delay = 1.0  # Начальная задержка в секундах
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5.0) as response:
                    if response.status == 200:
                        data = await response.json()
                        address = data.get("address", {})
                        
                        # Иерархия поиска: город -> поселок городского типа -> деревня -> регион
                        city = (
                            address.get("city") or 
                            address.get("town") or 
                            address.get("village") or 
                            address.get("state")
                        )
                        return city if city else "Неизвестно"
                    
                    elif response.status == 429:  # Too Many Requests (превышен лимит)
                        logger.warning(f"Rate limit hit (429). Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        delay *= 2  # Увеличиваем задержку: 1с -> 2с -> 4с
                        continue
                    
                    else:
                        logger.error(f"Nominatim API error: {response.status}")
                        await bot.send_message(TELEGRAM_LOG_CHANNEL_ID, f"Не получилось определить геопозицию для координат {lat}, {lon}. Код ответа: {response.status}")
                        return "Неизвестно"
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on attempt {attempt + 1}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay *= 2
        except Exception as e:
            logger.error(f"Unexpected error getting city: {e}")
            await bot.send_message(TELEGRAM_LOG_CHANNEL_ID, f"Не получилось определить геопозицию для координат {lat}, {lon}. Код ответа: {response.status}")
            return "Неизвестно"

    logger.error(f"Failed to get city after {max_retries} attempts for coords {lat}, {lon}")
    await bot.send_message(TELEGRAM_LOG_CHANNEL_ID, f"Не получилось определить геопозицию для координат {lat}, {lon}. Код ответа: {response.status}")
    return "Неизвестно"