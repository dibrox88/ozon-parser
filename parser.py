"""Модуль парсинга заказов Ozon."""
import time
from pathlib import Path
from typing import List, Dict, Any
from playwright.sync_api import Page
from loguru import logger
from config import Config
from notifier import sync_send_message, sync_send_photo


class OzonParser:
    """Класс для парсинга заказов."""
    
    def __init__(self, page: Page):
        """
        Инициализация.
        
        Args:
            page: Страница Playwright
        """
        self.page = page
        self.config = Config()
        
        # Создаем директорию для скриншотов
        Path(Config.SCREENSHOTS_DIR).mkdir(exist_ok=True)
    
    def _take_screenshot(self, name: str) -> str:
        """
        Сделать скриншот.
        
        Args:
            name: Имя файла
            
        Returns:
            Путь к скриншоту
        """
        timestamp = int(time.time())
        filename = f"{Config.SCREENSHOTS_DIR}/{name}_{timestamp}.png"
        self.page.screenshot(path=filename, full_page=True)
        logger.info(f"Скриншот сохранен: {filename}")
        return filename
    
    def navigate_to_orders(self) -> bool:
        """
        Перейти на страницу заказов.
        
        Returns:
            True если успешно
        """
        try:
            logger.info(f"Переходим на страницу заказов: {Config.OZON_ORDERS_URL}")
            sync_send_message("📦 Переходим к списку заказов...")
            
            self.page.goto(Config.OZON_ORDERS_URL, timeout=Config.NAVIGATION_TIMEOUT)
            self.page.wait_for_load_state('networkidle', timeout=Config.DEFAULT_TIMEOUT)
            
            time.sleep(3)
            
            # Делаем скриншот
            screenshot = self._take_screenshot('orders_page')
            sync_send_photo(screenshot, "Страница заказов открыта")
            
            logger.info("Успешно перешли на страницу заказов")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при переходе на страницу заказов: {e}")
            sync_send_message(f"❌ Ошибка при переходе к заказам: {str(e)}")
            return False
    
    def parse_orders(self) -> List[Dict[str, Any]]:
        """
        Парсинг списка заказов.
        
        Returns:
            Список заказов
        """
        try:
            logger.info("Начинаем парсинг заказов")
            sync_send_message("🔍 Начинаем парсинг заказов...")
            
            orders = []
            
            # Здесь будет логика парсинга после изучения структуры страницы
            # Пока просто получаем HTML для анализа
            page_content = self.page.content()
            
            logger.info("Парсинг завершен")
            sync_send_message(f"✅ Найдено заказов: {len(orders)}")
            
            return orders
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге заказов: {e}")
            sync_send_message(f"❌ Ошибка при парсинге: {str(e)}")
            return []
    
    def get_page_html(self) -> str:
        """
        Получить HTML страницы для анализа.
        
        Returns:
            HTML контент
        """
        try:
            return self.page.content()
        except Exception as e:
            logger.error(f"Ошибка при получении HTML: {e}")
            return ""
