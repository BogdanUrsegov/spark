import re

def contains_forbidden_content(text: str) -> bool:
    """Проверяет наличие запрещённых элементов: @ и ссылок"""
    # Запрещаем символ @
    if "@" in text:
        return True
    
    # Запрещаем ссылки (http/https/www и домены)
    url_pattern = re.compile(
        r'https?://\S+|www\.\S+|'
        r'[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z]{2,})+',
        re.IGNORECASE
    )
    return bool(url_pattern.search(text))