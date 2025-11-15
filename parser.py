"""Модуль парсинга заказов Ozon."""
import time
import random
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
        # full_page=False для мобильной вёрстки (иначе слишком большой для Telegram)
        self.page.screenshot(path=filename, full_page=False)
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
        
        Ищем span с текстом "Товары", поднимаемся на 4 родительских div, затем ищем span с ₽.
        
        Returns:
            Сумма заказа как число или None
        """
        try:
            # Ищем все span с классом tsBody500Medium
            body_spans = self.page.query_selector_all('span.tsBody500Medium')
            
            for span in body_spans:
                text = span.inner_text().strip()
                if text == 'Товары':
                    logger.debug("Найден span с текстом 'Товары'")
                    
                    # Поднимаемся на 4 уровня вверх к родительскому контейнеру
                    parent_element = span.evaluate_handle('''
                        el => {
                            let parent = el;
                            for (let i = 0; i < 4; i++) {
                                parent = parent.parentElement;
                                if (!parent) return null;
                            }
                            return parent;
                        }
                    ''').as_element()
                    
                    if not parent_element:
                        logger.warning("Не удалось подняться на 4 уровня от 'Товары'")
                        continue
                    
                    # Ищем span.tsHeadline400Small внутри родительского элемента
                    price_span = parent_element.query_selector('span.tsHeadline400Small')
                    
                    if price_span:
                        price_text = price_span.inner_text().strip()
                        logger.debug(f"Найден текст цены: {price_text}")
                        
                        if '₽' in price_text:
                            # Извлекаем число, убирая все виды пробелов и заменяя запятую на точку
                            price_str = price_text.replace('₽', '').replace(' ', '').replace('\xa0', '').replace('\u202f', '').replace(',', '.').strip()
                            try:
                                price = float(price_str)
                                logger.info(f"Найдена сумма заказа: {price} ₽")
                                return price
                            except ValueError:
                                logger.debug(f"Не удалось преобразовать в число: {price_str}")
                                continue
                    else:
                        logger.debug("Не найден span.tsHeadline400Small в родительском контейнере")
            
            # Fallback: пробуем найти любой span.tsHeadline400Small с суммой ₽
            logger.debug("Попытка fallback поиска суммы через все span.tsHeadline400Small")
            all_price_spans = self.page.query_selector_all('span.tsHeadline400Small')
            
            candidate_prices = []
            for price_span in all_price_spans:
                price_text = price_span.inner_text().strip()
                if '₽' in price_text:
                    # Извлекаем число, заменяя запятую на точку
                    price_str = price_text.replace('₽', '').replace(' ', '').replace('\xa0', '').replace('\u202f', '').replace(',', '.').strip()
                    try:
                        price = float(price_str)
                        # Собираем суммы >= 100₽
                        if price >= 100:
                            candidate_prices.append(price)
                            logger.debug(f"Найден кандидат на сумму заказа: {price} ₽")
                    except ValueError:
                        continue
            
            # Берем максимальную сумму (скорее всего это итоговая сумма заказа)
            if candidate_prices:
                max_price = max(candidate_prices)
                logger.info(f"Найдена сумма заказа (fallback, max из {len(candidate_prices)} кандидатов): {max_price} ₽")
                return max_price
            
            logger.warning("Не удалось найти сумму заказа")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге суммы заказа: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
            "Black" или "White" или "0" (некорректный)
        """
        color_text_lower = color_text.lower()
        
        # Белые цвета
        if any(word in color_text_lower for word in ['бел', 'white', 'светл']):
            return 'White'
        
        # Проверяем что это действительно цвет (содержит хоть какое-то описание цвета)
        color_keywords = ['черн', 'black', 'темн', 'серый', 'grey', 'gray', 'хром', 
                         'красн', 'син', 'зелен', 'желт', 'оранж', 'фиолет', 'розов',
                         'коричнев', 'голуб', 'сер']
        
        if any(word in color_text_lower for word in color_keywords):
            # Все цвета кроме белого = Black
            return 'Black'
        
        # Если не распознан - возвращаем 0 (требует уточнения)
        return '0'
    
    def _parse_shipment_items(self, shipment_element: ElementHandle, fallback_status: str) -> List[Dict[str, Any]]:
        """
        Извлечь товары из отправления.
        
        Структура HTML (октябрь 2025):
        <div data-widget="shipmentWidget">
          <div>Статус отправления (первый дочерний div)</div>
          <div>  ← Второй дочерний div = контейнер всех товаров
            ВАРИАНТ А (с группами):
              <div><span class="tsHeadline500Medium">10 товаров готовы</span></div>
              <div>Блок с товарами</div>
              <div><span class="tsHeadline500Medium">5 товаров получено</span></div>
              <div>Блок с товарами</div>
            
            ВАРИАНТ Б (простой):
              <div>Товар 1</div>
              <div>Товар 2</div>
        </div>
        
        Args:
            shipment_element: Элемент div[data-widget="shipmentWidget"]
            fallback_status: Статус по умолчанию (если не найден специфичный)
            
        Returns:
            Список товаров с полями: quantity, price, name, color, status
        """
        items = []
        seen_items = set()
        
        try:
            # Получаем все прямые дочерние div
            all_children = shipment_element.query_selector_all(':scope > div')
            logger.debug(f"Найдено прямых дочерних div: {len(all_children)}")
            
            if len(all_children) < 2:
                logger.warning("Недостаточно дочерних блоков в shipmentWidget")
                return items
            
            # Все div начиная со 2-го (индекс 1) содержат товары (может быть несколько блоков)
            # Обрабатываем каждый контейнер товаров
            for container_idx in range(1, len(all_children)):
                items_container = all_children[container_idx]
                logger.debug(f"Обрабатываем контейнер #{container_idx}")
                
                # Получаем все дочерние div из контейнера товаров
                container_children = items_container.query_selector_all(':scope > div')
                logger.debug(f"Найдено блоков в контейнере #{container_idx}: {len(container_children)}")
                
                i = 0
                while i < len(container_children):
                    current_div = container_children[i]
                    
                    # Проверяем, является ли этот div заголовком группы (содержит tsHeadline500Medium)
                    group_status_span = current_div.query_selector('span.tsHeadline500Medium')
                    
                    if group_status_span:
                        # Это заголовок группы товаров
                        status_text = group_status_span.inner_text().lower()
                        logger.debug(f"Найден групповой статус: '{status_text}'")
                        
                        # Определяем статус по ключевым словам
                        if 'отменён' in status_text or 'отменен' in status_text:
                            item_status = 'отменен'
                        elif 'готов' in status_text or 'забрать' in status_text:
                            item_status = 'забрать'
                        elif 'получен' in status_text:
                            item_status = 'получен'
                        elif 'пути' in status_text or 'передаётся' in status_text or 'передается' in status_text:
                            item_status = 'в пути'
                        else:
                            item_status = fallback_status
                        
                        logger.debug(f"Групповой статус: {item_status}")
                        
                        # Следующий div должен содержать товары этой группы
                        i += 1
                        if i >= len(container_children):
                            break
                        
                        products_block = container_children[i]
                    else:
                        # Это товар напрямую (простая структура без групп)
                        products_block = current_div
                        item_status = fallback_status
                    
                    # Парсим товары внутри products_block
                    # Ищем все блоки с названием товара (span.tsCompact500Medium)
                    name_elements = products_block.query_selector_all('span.tsCompact500Medium')
                    
                    for name_element in name_elements:
                        try:
                            name = name_element.inner_text().strip()
                            
                            # Находим родительский div, который содержит всю информацию о товаре
                            # Это div, который содержит и название (tsCompact500Medium), и цвет (tsCompact400Small), и цену
                            parent = name_element
                            product_container = None
                            
                            # Поднимаемся вверх по DOM до тех пор, пока не найдем контейнер с ценой
                            for _ in range(10):  # Максимум 10 уровней вверх
                                parent = parent.evaluate_handle('el => el.parentElement')
                                if not parent:
                                    break
                                
                                # Проверяем наличие цены в этом контейнере
                                has_price = parent.evaluate('''
                                    el => el.querySelector('span.tsHeadline400Small') !== null || 
                                          el.querySelector('span.tsBodyControl300XSmall') !== null
                                ''')
                                
                                if has_price:
                                    product_container = parent.as_element()
                                    break
                            
                            if not product_container:
                                logger.debug(f"Не найден контейнер для товара: {name}")
                                continue
                            
                            # Извлекаем цвет из того же контейнера
                            color = ""
                            color_element = product_container.query_selector('span.tsCompact400Small')
                            if color_element:
                                color_text = color_element.inner_text().strip()
                                if 'Цвет:' in color_text:
                                    color = self._extract_color_from_text(color_text)
                                    name = f"{name} {color}"
                            
                            # Извлекаем количество и цену
                            quantity = None
                            price = None
                            
                            # Ищем span.tsBodyControl300XSmall с форматом "X x ЦЕНА ₽"
                            price_spans = product_container.query_selector_all('span.tsBodyControl300XSmall')
                            
                            for span in price_spans:
                                text = span.inner_text().strip()
                                match = re.search(r'(\d+)\s*x\s*([\d\s\u202f\xa0,]+)\s*₽', text)
                                if match:
                                    quantity = int(match.group(1))
                                    price_str = match.group(2).replace(' ', '').replace('\xa0', '').replace('\u202f', '').replace(',', '.')
                                    price = float(price_str)
                                    logger.debug(f"Найдено: {name} x{quantity} @ {price}₽")
                                    break
                            
                            # Если не нашли, ищем в span.tsHeadline400Small (количество = 1)
                            if price is None:
                                headline_span = product_container.query_selector('span.tsHeadline400Small')
                                if headline_span:
                                    text = headline_span.inner_text().strip()
                                    match_single = re.search(r'([\d\s\u202f\xa0,]+)\s*₽', text)
                                    if match_single:
                                        price_str = match_single.group(1).replace(' ', '').replace('\xa0', '').replace('\u202f', '').replace(',', '.')
                                        price = float(price_str)
                                        quantity = 1
                                        logger.debug(f"Найдено: {name} x1 @ {price}₽")
                            
                            if price is None or quantity is None:
                                logger.debug(f"Не найдена цена/количество для '{name}', пропускаем")
                                continue
                            
                            # Проверяем дубликаты (включая статус, т.к. один товар может быть в разных статусах)
                            item_key = f"{name}_{quantity}_{price}_{item_status}"
                            if item_key in seen_items:
                                logger.debug(f"Пропускаем дубликат: {name} [статус: {item_status}]")
                                continue
                            
                            seen_items.add(item_key)
                            
                            items.append({
                                'quantity': quantity,
                                'price': price,
                                'name': name,
                                'color': color,
                                'status': item_status
                            })
                            
                            logger.debug(f"✅ Товар добавлен: {name} x{quantity} @ {price}₽ [статус: {item_status}]")
                            
                        except Exception as e:
                            logger.error(f"Ошибка при парсинге товара: {e}")
                            continue
                    
                    i += 1
            
            logger.info(f"Всего товаров спарсено: {len(items)}")
            return items
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге товаров отправления: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
            # Используем 'domcontentloaded' для надежности
            self.page.wait_for_load_state('domcontentloaded', timeout=Config.DEFAULT_TIMEOUT)
            
            time.sleep(3)
            
            # Проверяем на блокировку
            page_title = self.page.title()
            if "Доступ ограничен" in page_title or "Access Denied" in page_title:
                logger.error("❌ БЛОКИРОВКА: Доступ ограничен на странице заказов!")
                screenshot = self._take_screenshot('blocked_orders_page')
                sync_send_photo(screenshot, f"❌ Блокировка Ozon: {page_title}")
                sync_send_message(
                    "🍪 <b>COOKIES УСТАРЕЛИ!</b>\n\n"
                    "❌ Ozon блокирует доступ на странице заказов.\n\n"
                    "📝 <b>Действия:</b>\n"
                    "1. Запустите на локальной машине:\n"
                    "   <code>python export_cookies.py</code>\n\n"
                    "2. Скопируйте cookies на сервер:\n"
                    "   <code>scp ozon_cookies.json ozon@85.193.81.13:~/ozon_parser/</code>\n\n"
                    "⏰ Cookies нужно обновлять каждые 3-7 дней.\n\n"
                    "🛑 <b>Парсинг остановлен.</b>"
                )
                return False
            
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
            
            # АНТИДЕТЕКТ: Случайная задержка 2-5 секунд перед каждым запросом
            delay = random.uniform(2.0, 5.0)
            logger.debug(f"⏰ Задержка {delay:.1f}с перед переходом на страницу заказа")
            time.sleep(delay)
            
            # Переходим на страницу заказа
            order_url = f"https://www.ozon.ru/my/orderdetails/?order={order_number}"
            logger.info(f"Переходим на: {order_url}")
            
            self.page.goto(order_url, timeout=Config.NAVIGATION_TIMEOUT)
            # Используем 'domcontentloaded' вместо 'networkidle' - быстрее и надежнее
            # networkidle может ждать слишком долго на медленных соединениях
            self.page.wait_for_load_state('domcontentloaded', timeout=Config.DEFAULT_TIMEOUT)
            
            # АНТИДЕТЕКТ: Дополнительная задержка после загрузки 1-3 секунды
            post_delay = random.uniform(1.0, 3.0)
            logger.debug(f"⏰ Задержка {post_delay:.1f}с после загрузки страницы")
            time.sleep(post_delay)
            
            # Проверяем на блокировку
            page_title = self.page.title()
            if "Доступ ограничен" in page_title or "Access Denied" in page_title:
                logger.error(f"❌ БЛОКИРОВКА на странице заказа {order_number}!")
                screenshot = self._take_screenshot(f'blocked_order_{order_number}')
                sync_send_photo(screenshot, f"❌ Блокировка при парсинге заказа {order_number}")
                sync_send_message(
                    "🛑 <b>БЛОКИРОВКА ОБНАРУЖЕНА!</b>\n\n"
                    f"❌ Ozon заблокировал доступ при попытке открыть заказ <code>{order_number}</code>\n\n"
                    "🍪 Cookies устарели. Обновите их:\n"
                    "1. <code>python export_cookies.py</code>\n"
                    "2. <code>scp ozon_cookies.json ozon@85.193.81.13:~/ozon_parser/</code>\n\n"
                    "🛑 <b>Парсинг остановлен.</b>"
                )
                # Возвращаем None чтобы остановить парсинг
                raise RuntimeError(f"Блокировка Ozon при парсинге заказа {order_number}")
            
            # Делаем скриншот
            screenshot = self._take_screenshot(f'order_{order_number}')
            
            # Парсим дату заказа
            order_date = self._parse_order_date()
            logger.info(f"Дата заказа: {order_date}")
            
            # Парсим общую сумму
            total_amount = self._parse_order_total()
            if total_amount is None:
                logger.warning("⚠️ Не удалось определить сумму заказа")
                total_amount = 0.0
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
            order_url = f"https://www.ozon.ru/my/orderdetails/?order={order_number}"
            message = f"📦 <a href='{order_url}'>{order_number}</a>\n\n"
            message += f"📅 Дата: {order_date}\n"
            message += f"💰 Сумма: {total_amount} ₽\n"
            message += f"📊 Товаров: {total_items_quantity} шт ({len(all_items)} позиций)\n\n"
            
            if all_items:
                message += "🛍 Товары:\n"
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
    
    def parse_orders(self, first_order: Optional[str] = None, last_order: Optional[str] = None) -> List[str]:
        """
        Парсинг списка заказов.
        
        Args:
            first_order: Номер первого заказа для фильтрации (например, "46206571-0680")
            last_order: Номер последнего заказа для фильтрации (например, "46206571-0710")
        
        Returns:
            Список уникальных номеров заказов, отсортированных по возрастанию
        """
        try:
            logger.info("Начинаем парсинг заказов")
            if first_order and last_order:
                logger.info(f"📊 Режим диапазона: {first_order} - {last_order}")
                sync_send_message(f"🔍 Парсинг диапазона:\n<code>{first_order}</code> → <code>{last_order}</code>")
            else:
                sync_send_message("🔍 Начинаем парсинг номеров заказов...")
            
            order_numbers: Set[str] = set()
            
            # Если указан диапазон - генерируем список заказов, а не ищем на странице
            if first_order and last_order:
                logger.info("📊 Генерируем список заказов из диапазона...")
                
                # Извлекаем префикс и числовые части
                # Формат: 46206571-0661
                try:
                    prefix, start_num_str = first_order.rsplit('-', 1)
                    _, end_num_str = last_order.rsplit('-', 1)
                    
                    start_num = int(start_num_str)
                    end_num = int(end_num_str)
                    
                    # Генерируем все номера в диапазоне
                    for num in range(start_num, end_num + 1):
                        order_number = f"{prefix}-{num:04d}"
                        order_numbers.add(order_number)
                    
                    logger.info(f"✅ Сгенерировано {len(order_numbers)} номеров заказов из диапазона")
                
                except Exception as e:
                    logger.error(f"❌ Ошибка генерации диапазона: {e}")
                    sync_send_message(f"❌ Ошибка: некорректный формат диапазона")
                    return []
            
            else:
                # Обычный режим - ищем заказы на странице
                # Ждем загрузки страницы
                time.sleep(2)
                
                # Пробуем прокрутить страницу вниз для подгрузки всех заказов
                #logger.info("Прокручиваем страницу для загрузки всех заказов...")
                #self._scroll_to_load_all_orders()
                
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
                    # Добавляем ссылку на заказ в Ozon
                    order_url = f"https://www.ozon.ru/my/orderdetails/?order={order_num}"
                    message += f"{idx}. <a href=\"{order_url}\">{order_num}</a>\n"
                
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
