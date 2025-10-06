"""Конфигурация приложения."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Класс конфигурации."""
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Ozon
    OZON_PHONE = os.getenv('OZON_PHONE', '')
    OZON_EMAIL = os.getenv('OZON_EMAIL', '')
    OZON_USER_ID = os.getenv('OZON_USER_ID', '')
    OZON_LOGIN_URL = 'https://www.ozon.ru/'
    OZON_ORDERS_URL = 'https://www.ozon.ru/my/orderlist/'
    
    # Browser
    HEADLESS = os.getenv('HEADLESS', 'False').lower() == 'true'
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    
    # Timeouts
    DEFAULT_TIMEOUT = 30000  # 30 секунд
    NAVIGATION_TIMEOUT = 60000  # 60 секунд
    
    # Directories
    SCREENSHOTS_DIR = 'screenshots'
    LOGS_DIR = 'logs'
    BROWSER_STATE_DIR = 'browser_state'
    
    # Google Sheets
    GOOGLE_SHEETS_URL = os.getenv('GOOGLE_SHEETS_URL', '')
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
    PRODUCT_MAPPINGS_FILE = 'product_mappings.json'
    
    @classmethod
    def validate(cls):
        """Проверка наличия обязательных настроек."""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append('TELEGRAM_BOT_TOKEN не установлен')
        if not cls.TELEGRAM_CHAT_ID:
            errors.append('TELEGRAM_CHAT_ID не установлен')
        if not cls.OZON_EMAIL:
            errors.append('OZON_EMAIL не установлен')
            
        if errors:
            raise ValueError(f"Ошибки конфигурации:\n" + "\n".join(f"- {e}" for e in errors))
        
        return True
