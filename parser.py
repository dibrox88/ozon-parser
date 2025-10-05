"""Модуль парсинга заказов Ozon."""
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Set
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
    
    def parse_orders(self) -> List[str]:
        """
        Парсинг списка заказов.
        
        Returns:
            Список уникальных номеров заказов, отсортированных по возрастанию
        """
        try:
            logger.info("Начинаем парсинг заказов")
            sync_send_message("🔍 Начинаем парсинг номеров заказов...")
            
            # Ждем загрузки страницы
            time.sleep(2)
            
            # Пробуем прокрутить страницу вниз для подгрузки всех заказов
            logger.info("Прокручиваем страницу для загрузки всех заказов...")
            self._scroll_to_load_all_orders()
            
            order_numbers: Set[str] = set()
            
            # Вариант 1: Если указан USER_ID, ищем по нему
            if Config.OZON_USER_ID:
                logger.info(f"Используем USER_ID для поиска: {Config.OZON_USER_ID}")
                order_numbers.update(self._find_orders_by_user_id(Config.OZON_USER_ID))
            
            # Вариант 2: Ищем все элементы с номерами заказов по селектору
            logger.info("Ищем номера заказов по селектору...")
            order_numbers.update(self._find_orders_by_selector())
            
            # Вариант 3: Поиск по паттерну в тексте (резервный метод)
            if not order_numbers:
                logger.info("Используем резервный метод - поиск по паттерну...")
                order_numbers.update(self._find_orders_by_pattern())
            
            # Убираем дубликаты и сортируем
            unique_orders = sorted(list(order_numbers))
            
            # Логируем результаты
            logger.info(f"✅ Найдено уникальных заказов: {len(unique_orders)}")
            
            if unique_orders:
                logger.info("📋 Список номеров заказов (отсортированный):")
                for idx, order_num in enumerate(unique_orders, 1):
                    logger.info(f"  {idx}. {order_num}")
                
                # Формируем красивое сообщение для Telegram
                message = f"✅ <b>Найдено заказов: {len(unique_orders)}</b>\n\n"
                message += "📋 Номера заказов:\n"
                for idx, order_num in enumerate(unique_orders, 1):
                    message += f"{idx}. <code>{order_num}</code>\n"
                
                sync_send_message(message)
            else:
                logger.warning("⚠️ Номера заказов не найдены")
                sync_send_message("⚠️ Номера заказов не найдены на странице")
            
            return unique_orders
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге заказов: {e}")
            sync_send_message(f"❌ Ошибка при парсинге: {str(e)}")
            return []
    
    def _scroll_to_load_all_orders(self):
        """Прокрутить страницу вниз для подгрузки всех заказов."""
        try:
            # Получаем высоту страницы
            prev_height = self.page.evaluate("document.body.scrollHeight")
            
            # Прокручиваем несколько раз
            for i in range(5):
                # Прокручиваем вниз
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
                
                # Проверяем, изменилась ли высота
                new_height = self.page.evaluate("document.body.scrollHeight")
                if new_height == prev_height:
                    # Высота не изменилась, значит все загружено
                    break
                prev_height = new_height
                logger.info(f"Прокрутка {i+1}/5: высота страницы {new_height}px")
            
            # Прокручиваем обратно наверх
            self.page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Ошибка при прокрутке: {e}")
    
    def _find_orders_by_user_id(self, user_id: str) -> Set[str]:
        """
        Найти заказы по USER_ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Множество номеров заказов
        """
        orders = set()
        try:
            # Ищем элементы, содержащие user_id
            # Паттерн: USER_ID-XXXX (например, 46206571-0591)
            pattern = f'{user_id}-'
            
            # Ищем все div с классом, содержащие номера заказов
            elements = self.page.query_selector_all(f'div[title*="{user_id}"]')
            
            logger.info(f"Найдено элементов с user_id: {len(elements)}")
            
            for element in elements:
                try:
                    title = element.get_attribute('title')
                    if title and pattern in title:
                        orders.add(title)
                        logger.debug(f"Найден заказ (по user_id): {title}")
                except Exception as e:
                    logger.debug(f"Ошибка при обработке элемента: {e}")
            
        except Exception as e:
            logger.warning(f"Ошибка при поиске по user_id: {e}")
        
        return orders
    
    def _find_orders_by_selector(self) -> Set[str]:
        """
        Найти заказы по CSS селектору.
        
        Returns:
            Множество номеров заказов
        """
        orders = set()
        try:
            # Различные селекторы для поиска номеров заказов
            selectors = [
                'div.b5_4_4-b0.tsBodyControl300XSmall',  # Основной класс из примера
                'div.b5_4_4-b0',
                'div[class*="b5_4_4"]',
                'div[title][class*="tsBodyControl"]',
            ]
            
            for selector in selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    logger.info(f"Селектор '{selector}': найдено {len(elements)} элементов")
                    
                    for element in elements:
                        try:
                            # Проверяем title
                            title = element.get_attribute('title')
                            if title and self._is_order_number(title):
                                orders.add(title)
                                logger.debug(f"Найден заказ (title): {title}")
                            
                            # Проверяем текст
                            text = element.inner_text().strip()
                            if text and self._is_order_number(text):
                                orders.add(text)
                                logger.debug(f"Найден заказ (text): {text}")
                                
                        except Exception as e:
                            logger.debug(f"Ошибка при обработке элемента: {e}")
                            
                except Exception as e:
                    logger.debug(f"Ошибка с селектором {selector}: {e}")
            
        except Exception as e:
            logger.warning(f"Ошибка при поиске по селектору: {e}")
        
        return orders
    
    def _find_orders_by_pattern(self) -> Set[str]:
        """
        Найти заказы по паттерну в HTML (резервный метод).
        
        Returns:
            Множество номеров заказов
        """
        orders = set()
        try:
            # Получаем весь HTML
            html = self.page.content()
            
            # Паттерн для номера заказа: XXXXXXXX-XXXX (8 цифр, дефис, 4 цифры)
            pattern = r'\b(\d{8}-\d{4})\b'
            
            matches = re.findall(pattern, html)
            
            for match in matches:
                if self._is_order_number(match):
                    orders.add(match)
                    logger.debug(f"Найден заказ (pattern): {match}")
            
            logger.info(f"Найдено заказов по паттерну: {len(orders)}")
            
        except Exception as e:
            logger.warning(f"Ошибка при поиске по паттерну: {e}")
        
        return orders
    
    def _is_order_number(self, text: str) -> bool:
        """
        Проверить, является ли текст номером заказа.
        
        Args:
            text: Текст для проверки
            
        Returns:
            True если это номер заказа
        """
        if not text:
            return False
        
        # Паттерн: XXXXXXXX-XXXX (8 цифр, дефис, 4 цифры)
        pattern = r'^\d{8}-\d{4}$'
        return bool(re.match(pattern, text.strip()))
    
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
