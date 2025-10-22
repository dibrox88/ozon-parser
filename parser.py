"""Модуль парсинга заказов Ozon."""
import time
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
from playwright.sync_api import Page, ElementHandle
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
    
    # ============ Парсинг деталей заказа ============
    
    MONTH_MAP = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
    }
    
    def _parse_order_date(self) -> Optional[str]:
        """
        Извлечь и преобразовать дату заказа.
        
        Форматы:
        - "Заказ от 17 сентября" -> "17.09.2025"
        - "Заказ от 05.07.2023" -> "05.07.2023"
        
        Returns:
            Дата в формате DD.MM.YYYY или None
        """
        try:
            # Ищем элемент с датой заказа
            date_selectors = [
                '[data-widget="titleWithTimer"] span.tsHeadline700XLarge',
                'span:has-text("Заказ от")',
                'div:has-text("Заказ от")'
            ]
            
            date_text = None
            for selector in date_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        date_text = element.inner_text().strip()
                        if date_text and 'Заказ от' in date_text:
                            logger.debug(f"Найден текст даты: {date_text}")
                            break
                except:
                    continue
            
            if not date_text:
                logger.warning("Не удалось найти дату заказа")
                return None
            
            # Убираем "Заказ от "
            date_text = date_text.replace('Заказ от ', '').strip()
            
            # Проверяем формат DD.MM.YYYY
            if re.match(r'\d{2}\.\d{2}\.\d{4}', date_text):
                logger.info(f"Дата уже в нужном формате: {date_text}")
                return date_text
            
            # Парсим формат "17 сентября"
            match = re.match(r'(\d{1,2})\s+(\w+)', date_text)
            if match:
                day = match.group(1).zfill(2)
                month_name = match.group(2).lower()
                
                if month_name in self.MONTH_MAP:
                    month = self.MONTH_MAP[month_name]
                    current_year = datetime.now().year
                    result_date = f"{day}.{month}.{current_year}"
                    logger.info(f"Дата преобразована: '{date_text}' -> '{result_date}'")
                    return result_date
            
            logger.warning(f"Не удалось распарсить дату: {date_text}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге даты заказа: {e}")
            return None
    
    def _parse_order_total(self) -> Optional[float]:
        """
        Извлечь общую сумму заказа.
        
        Ищем span с текстом "Товары", затем в родительском div ищем сумму с ₽.
        
        Returns:
            Сумма заказа как число или None
        """
        try:
            # Ищем элемент с текстом "Товары"
            товары_элемент = self.page.query_selector('span:has-text("Товары")')
            
            if not товары_элемент:
                logger.warning("Не найден элемент 'Товары'")
                return None
            
            # Получаем родительский контейнер (без использования динамических классов)
            # Ищем ближайший div-контейнер с ценой
            parent = товары_элемент.evaluate('el => el.closest("div")')
            
            if not parent:
                logger.warning("Не найден родительский контейнер для суммы")
                return None
            
            # Ищем span с ₽ внутри родительского контейнера (без динамических классов)
            # Используем XPath: находим "Товары" и поднимаемся к родительскому div
            parent_element = self.page.query_selector(f'xpath=//*[contains(text(), "Товары")]/ancestor::div[.//span[contains(text(), "₽")]]')
            
            if parent_element:
                # Ищем все span внутри
                price_elements = parent_element.query_selector_all('span')
                
                for price_el in price_elements:
                    text = price_el.inner_text().strip()
                    if '₽' in text:
                        # Извлекаем число, убирая все виды пробелов
                        price_str = text.replace('₽', '').replace(' ', '').replace('\xa0', '').replace('\u202f', '').strip()
                        try:
                            price = float(price_str)
                            logger.info(f"Найдена сумма заказа: {price} ₽")
                            return price
                        except ValueError:
                            logger.debug(f"Не удалось преобразовать в число: {price_str}")
                            continue
            
            logger.warning("Не удалось найти сумму заказа")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге суммы заказа: {e}")
            return None
    
    def _determine_shipment_status(self, shipment_element: ElementHandle) -> str:
        """
        Определить статус отправления по ключевым словам.
        
        Args:
            shipment_element: Элемент div[data-widget="shipmentWidget"]
            
        Returns:
            Статус: "отменен", "получен", "забрать", "в пути"
        """
        try:
            text = shipment_element.inner_text().lower()
            
            # Проверяем ключевые слова в порядке приоритета
            if 'отменён' in text or 'отменен' in text:
                return 'отменен'
            
            # ВАЖНО: "получен" проверяем ПЕРЕД "готовы", так как в блоке "Успейте забрать" может быть "X товаров получено"
            if 'получен' in text:
                return 'получен'
            
            # "забирать" или "готовы" → статус "забрать"
            if 'забирать' in text or 'готовы' in text:
                return 'забрать'
            
            if 'пути' in text or 'передаётся' in text or 'передается' in text or 'в службе' in text:
                return 'в пути'
            
            # По умолчанию
            logger.warning(f"Не удалось определить статус из текста: {text[:100]}")
            return 'неизвестно'
            
        except Exception as e:
            logger.error(f"Ошибка при определении статуса: {e}")
            return 'ошибка'
    
    def _determine_item_group_status(self, group_element: ElementHandle, fallback_status: str) -> str:
        """
        Определить статус для конкретной группы товаров (div.lf6_15).
        
        В блоке "Успейте забрать" может быть несколько подблоков:
        - "5 товаров готовы к получению" → "забрать"
        - "9 товаров получено" → "получен"
        
        Args:
            group_element: Элемент группы товаров (div.lf6_15 или shipmentWidget)
            fallback_status: Статус по умолчанию, если не найден специфичный
            
        Returns:
            Статус: "отменен", "получен", "забрать", "в пути"
        """
        try:
            # Логируем полный текст группы для отладки
            full_text = group_element.inner_text()
            logger.debug(f"=== ГРУППА ТОВАРОВ ===")
            logger.debug(f"Полный текст группы (первые 200 символов): {full_text[:200]}")
            logger.debug(f"Fallback статус: {fallback_status}")
            
            # Ищем заголовок статуса в начале группы (span.tsHeadline500Medium)
            status_element = group_element.query_selector('span.tsHeadline500Medium')
            
            if status_element:
                status_text = status_element.inner_text().lower()
                logger.info(f"🔍 Найден текст статуса группы: '{status_text}'")
                
                # ВАЖНО: Проверяем в правильном порядке!
                # "готовы к получению" содержит "получен", поэтому сначала ищем "готов"
                
                if 'отменён' in status_text or 'отменен' in status_text:
                    logger.info(f"✅ Определён статус: 'отменен'")
                    return 'отменен'
                
                if 'готов' in status_text or 'забрать' in status_text:
                    logger.info(f"✅ Определён статус: 'забрать' (найдено 'готов' или 'забрать' в '{status_text}')")
                    return 'забрать'
                
                if 'получен' in status_text:
                    logger.info(f"✅ Определён статус: 'получен' (найдено 'получен' в '{status_text}')")
                    return 'получен'
                
                if 'пути' in status_text or 'передаётся' in status_text or 'передается' in status_text:
                    logger.info(f"✅ Определён статус: 'в пути'")
                    return 'в пути'
                
                logger.warning(f"⚠️ Не найдено ключевых слов в статусе: '{status_text}'")
            else:
                logger.warning(f"⚠️ Не найден элемент span.tsHeadline500Medium в группе")
            
            # Если не нашли специфичный статус, используем fallback
            logger.info(f"➡️ Используем fallback статус: {fallback_status}")
            return fallback_status
            
        except Exception as e:
            logger.error(f"❌ Ошибка при определении статуса группы товаров: {e}")
            return fallback_status
    
    def _extract_color_from_text(self, color_text: str) -> str:
        """
        Извлечь цвет из текста и привести к Black/White.
        
        Args:
            color_text: Текст типа "Цвет: черный, хром, темно-серый"
            
        Returns:
            "Black" или "White" или исходный текст
        """
        color_text_lower = color_text.lower()
        
        # Черные цвета
        if any(word in color_text_lower for word in ['черн', 'black', 'темн', 'серый', 'grey', 'gray', 'хром']):
            return 'Black'
        
        # Белые цвета
        if any(word in color_text_lower for word in ['бел', 'white', 'светл']):
            return 'White'
        
        # Если не определен - возвращаем как есть
        return color_text
    
    def _parse_shipment_items(self, shipment_element: ElementHandle, fallback_status: str) -> List[Dict[str, Any]]:
        """
        Извлечь товары из отправления.
        
        Args:
            shipment_element: Элемент div[data-widget="shipmentWidget"]
            fallback_status: Статус по умолчанию (если не найден специфичный)
            
        Returns:
            Список товаров с полями: quantity, price, name, color, status
        """
        items = []
        seen_items = set()  # Для отслеживания дубликатов
        
        try:
            # Ищем подблоки с товарами (div.lf6_15 может содержать свой статус)
            item_groups = shipment_element.query_selector_all('div.lf6_15')
            
            # Если нет подблоков lf6_15, ищем напрямую div.f2l_15
            if not item_groups:
                item_groups = [shipment_element]
            
            logger.debug(f"Найдено групп товаров: {len(item_groups)}")
            
            for group in item_groups:
                # Определяем статус для этой группы товаров
                group_status = self._determine_item_group_status(group, fallback_status)
                
                # Ищем блоки товаров внутри группы
                item_blocks = group.query_selector_all('[data-widget="shipmentWidget"]')
                
                for item_block in item_blocks:
                    try:
                        # Извлекаем наименование
                        name_element = item_block.query_selector('span.tsCompact500Medium')
                        if not name_element:
                            logger.debug("Не найдено название товара, пропускаем")
                            continue
                        
                        name = name_element.inner_text().strip()
                        
                        # Извлекаем цвет
                        color = ""
                        color_element = item_block.query_selector('span.tsCompact400Small')
                        if color_element:
                            color_text = color_element.inner_text().strip()
                            if 'Цвет:' in color_text:
                                color = self._extract_color_from_text(color_text)
                                # Добавляем цвет к названию
                                name = f"{name} {color}"
                        
                        # Извлекаем количество и цену
                        quantity = None
                        price = None
                        
                        # Ищем все span с ценами
                        price_spans = item_block.query_selector_all('span.tsBodyControl300XSmall, span.c35_3_8-a1, span.tsHeadline400Small')
                        
                        # ПЕРВЫЙ ПРОХОД: Ищем формат "X x ЦЕНА ₽"
                        for span in price_spans:
                            text = span.inner_text().strip()
                            match = re.search(r'(\d+)\s*x\s*([\d\s\u202f\xa0]+)\s*₽', text)
                            if match:
                                quantity = int(match.group(1))
                                # Убираем все виды пробелов из цены
                                price_str = match.group(2).replace(' ', '').replace('\xa0', '').replace('\u202f', '')
                                price = float(price_str)
                                logger.debug(f"Найдено (множество): количество={quantity}, цена={price}")
                                break
                        
                        # ВТОРОЙ ПРОХОД: Если не нашли "X x", ищем просто цену "2 965 ₽"
                        if price is None:
                            for span in price_spans:
                                text = span.inner_text().strip()
                                match_single = re.search(r'^([\d\s\u202f\xa0]+)\s*₽$', text)
                                if match_single:
                                    price_str = match_single.group(1).replace(' ', '').replace('\xa0', '').replace('\u202f', '')
                                    price = float(price_str)
                                    quantity = 1
                                    logger.debug(f"Найдено (одиночный): цена={price}")
                                    break
                        
                        if price is None:
                            logger.debug(f"Не найдена цена для товара '{name}', пропускаем")
                            continue
                        
                        # Проверяем дубликаты по комбинации: название + количество + цена
                        item_key = f"{name}_{quantity}_{price}"
                        if item_key in seen_items:
                            logger.debug(f"Пропускаем дубликат: {name} x{quantity} @ {price}₽")
                            continue
                        
                        seen_items.add(item_key)
                        
                        items.append({
                            'quantity': quantity,
                            'price': price,
                            'name': name,
                            'color': color,
                            'status': group_status  # Используем статус группы
                        })
                        
                        logger.debug(f"Товар добавлен: {name} x{quantity} @ {price}₽ [статус: {group_status}]")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при парсинге товара: {e}")
                        continue
            
            return items
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге товаров отправления: {e}")
            return []
    
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
    
    def parse_order_details(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        Парсинг детальной информации о заказе.
        
        Args:
            order_number: Номер заказа (например, "46206571-0591")
            
        Returns:
            Словарь с деталями заказа или None
        """
        try:
            logger.info(f"📄 Парсим детали заказа {order_number}")
            
            # Переходим на страницу заказа
            order_url = f"https://www.ozon.ru/my/orderdetails/?order={order_number}"
            logger.info(f"Переходим на: {order_url}")
            
            self.page.goto(order_url, timeout=Config.NAVIGATION_TIMEOUT)
            self.page.wait_for_load_state('networkidle', timeout=Config.DEFAULT_TIMEOUT)
            time.sleep(3)
            
            # Делаем скриншот
            screenshot = self._take_screenshot(f'order_{order_number}')
            
            # Парсим дату заказа
            order_date = self._parse_order_date()
            logger.info(f"Дата заказа: {order_date}")
            
            # Парсим общую сумму
            total_amount = self._parse_order_total()
            logger.info(f"Сумма заказа: {total_amount} ₽")
            
            # Парсим товары по отправлениям
            all_items = []
            shipment_widgets = self.page.query_selector_all('div[data-widget="shipmentWidget"]')
            
            logger.info(f"Найдено отправлений: {len(shipment_widgets)}")
            
            for idx, shipment in enumerate(shipment_widgets, 1):
                logger.debug(f"Обрабатываем отправление #{idx}")
                
                # Определяем статус отправления
                status = self._determine_shipment_status(shipment)
                logger.debug(f"Статус отправления #{idx}: {status}")
                
                # Парсим товары в этом отправлении
                items = self._parse_shipment_items(shipment, status)
                all_items.extend(items)
                logger.debug(f"Найдено товаров в отправлении #{idx}: {len(items)}")
            
            # Подсчитываем общее количество товаров (сумма всех quantity)
            total_items_quantity = sum(item['quantity'] for item in all_items)
            
            # Формируем результат
            order_data = {
                'order_number': order_number,
                'date': order_date,
                'total_amount': total_amount,
                'items': all_items,
                'items_count': total_items_quantity  # Сумма quantity вместо len(all_items)
            }
            
            # Логируем краткую информацию
            logger.info(f"✅ Заказ {order_number}: дата={order_date}, сумма={total_amount}₽, товаров={total_items_quantity} шт ({len(all_items)} позиций)")
            
            # Отправляем информацию в Telegram
            message = f"📦 <b>Заказ {order_number}</b>\n\n"
            message += f"📅 Дата: {order_date}\n"
            message += f"💰 Сумма: {total_amount} ₽\n"
            message += f"📊 Товаров: {total_items_quantity} шт ({len(all_items)} позиций)\n\n"
            
            if all_items:
                message += "🛍 <b>Товары:</b>\n"
                for i, item in enumerate(all_items[:5], 1):  # Показываем первые 5
                    message += f"{i}. {item['name']}\n"
                    message += f"   {item['quantity']} шт x {item['price']} ₽ = {item['quantity'] * item['price']} ₽\n"
                    message += f"   Статус: {item['status']}\n"
                
                if len(all_items) > 5:
                    message += f"\n... и еще {len(all_items) - 5} товаров"
            
            sync_send_photo(screenshot, message)
            
            return order_data
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге деталей заказа {order_number}: {e}")
            sync_send_message(f"❌ Ошибка при парсинге заказа {order_number}: {str(e)}")
            return None
    
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
            #logger.info("Прокручиваем страницу для загрузки всех заказов...")
            #self._scroll_to_load_all_orders()
            
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
                'div.b5_4_4-b0.tsBodyControl300XSmall'#,  # Основной класс из примера
                #'div.b5_4_4-b0',
                #'div[class*="b5_4_4"]',
                #'div[title][class*="tsBodyControl"]',
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
