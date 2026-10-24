import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)

# Nominatim's public endpoint requires a low request rate. Serialize calls and
# leave at least one second between outgoing requests from this process.
_NOMINATIM_LOCK = asyncio.Lock()
_LAST_REQUEST_AT = 0.0
_USER_AGENT = "StudentDatingBot/1.0 (+https://github.com/BogdanUrsegov/spark)"


async def get_city_by_coords(
    lat: float,
    lon: float,
    max_retries: int = 3,
) -> str:
    """Reverse-geocode coordinates. Network failures never escape to handlers."""
    global _LAST_REQUEST_AT

    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": lat,
        "lon": lon,
        "accept-language": "ru",
        "zoom": 10,
    }
    headers = {"User-Agent": _USER_AGENT}
    delay = 1.0

    for attempt in range(max_retries):
        try:
            async with _NOMINATIM_LOCK:
                loop = asyncio.get_running_loop()
                wait_for_rate_limit = 1.0 - (loop.time() - _LAST_REQUEST_AT)
                if wait_for_rate_limit > 0:
                    await asyncio.sleep(wait_for_rate_limit)

                timeout = aiohttp.ClientTimeout(total=8)
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.get(url, params=params) as response:
                        _LAST_REQUEST_AT = loop.time()

                        if response.status == 200:
                            data = await response.json(content_type=None)
                            address = data.get("address") or {}
                            city = (
                                address.get("city")
                                or address.get("town")
                                or address.get("village")
                                or address.get("municipality")
                                or address.get("state")
                            )
                            return city or "Неизвестно"

                        if response.status == 429 or response.status >= 500:
                            logger.warning(
                                "Reverse geocoding returned HTTP %s (attempt %s/%s).",
                                response.status,
                                attempt + 1,
                                max_retries,
                            )
                        else:
                            logger.warning("Reverse geocoding returned HTTP %s.", response.status)
                            return "Неизвестно"

            if attempt + 1 < max_retries:
                await asyncio.sleep(delay)
                delay *= 2

        except (asyncio.TimeoutError, aiohttp.ClientError, ValueError) as exc:
            logger.warning(
                "Reverse geocoding failed (attempt %s/%s): %s",
                attempt + 1,
                max_retries,
                type(exc).__name__,
            )
            if attempt + 1 < max_retries:
                await asyncio.sleep(delay)
                delay *= 2

    logger.error("Reverse geocoding failed after %s attempts.", max_retries)
    return "Неизвестно"
