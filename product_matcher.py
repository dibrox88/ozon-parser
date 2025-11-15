"""
Модуль для сопоставления товаров с каталогом и интерактивного подтверждения через Telegram.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from loguru import logger
from notifier import sync_send_message
from excluded_manager import ExcludedOrdersManager
from bundle_manager import BundleManager, create_bundle_item
import time


class ProductMatcher:
    """Класс для сопоставления товаров с каталогом."""
    
    DEFAULT_TYPE = "расходники"
    MAPPINGS_FILE = "product_mappings.json"
    
    def __init__(self, sheets_products: list, mappings_file: Optional[str] = None):
        """
        Инициализация.
        
        Args:
            sheets_products: Список товаров из Google Sheets
            mappings_file: Путь к файлу с сохранёнными сопоставлениями
        """
        self.catalog = sheets_products
        self.mappings_file = mappings_file or self.MAPPINGS_FILE
        self.mappings = self._load_mappings()
        self.type_map = self._create_type_map()
        
        logger.info(f"🔄 Загружено товаров из каталога: {len(self.catalog)}")
        logger.info(f"📋 Загружено сохранённых сопоставлений: {len(self.mappings)}")
        logger.info(f"🏷️ Создан маппинг типов: {len(self.type_map)} уникальных типов")
    
    def _create_type_map(self) -> Dict[int, str]:
        """
        Создать маппинг номер → тип товара из каталога.
        
        Returns:
            Словарь {1: "тип1", 2: "тип2", ...}
        """
        # Собираем уникальные типы из каталога
        unique_types = set()
        for product in self.catalog:
            product_type = product.get('type', '').strip()
            if product_type:
                unique_types.add(product_type)
        
        # Сортируем и создаём маппинг
        sorted_types = sorted(unique_types)
        type_map = {i + 1: type_name for i, type_name in enumerate(sorted_types)}
        
        logger.debug(f"📋 Типы товаров: {type_map}")
        return type_map
    
    def get_type_name(self, type_number: int) -> Optional[str]:
        """
        Получить название типа по номеру.
        
        Args:
            type_number: Номер типа
            
        Returns:
            Название типа или None
        """
        return self.type_map.get(type_number)
    
    def get_type_list_message(self) -> str:
        """
        Создать сообщение со списком доступных типов.
        
        Returns:
            Отформатированное сообщение
        """
        lines = ["📋 <b>Доступные типы товаров:</b>\n"]
        for num, type_name in sorted(self.type_map.items()):
            lines.append(f"  <b>{num}</b> - {type_name}")
        return "\n".join(lines)
    
    def get_type_button_options(self) -> List[tuple[str, str]]:
        """
        Создать список кнопок для выбора типа.
        
        Returns:
            Список кортежей (значение, текст_кнопки)
        """
        from typing import List
        options = []
        emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for num, type_name in sorted(self.type_map.items()):
            emoji = emoji_numbers[num - 1] if num <= 10 else f"{num}️⃣"
            # Ограничиваем длину названия типа для кнопки
            short_name = type_name[:15] + "..." if len(type_name) > 15 else type_name
            options.append((str(num), f"{emoji} {short_name}"))
        
        return options
    
    def _load_mappings(self) -> Dict[str, Dict[str, str | int]]:
        """Загрузить сохранённые сопоставления из файла."""
        try:
            if Path(self.mappings_file).exists():
                with open(self.mappings_file, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
                logger.info(f"✅ Загружены сопоставления из {self.mappings_file}")
                return mappings
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить сопоставления: {e}")
        
        return {}
    
    def _save_mappings(self) -> bool:
        """
        Сохранить сопоставления в файл с объединением существующих данных.
        Перечитывает файл перед сохранением, чтобы не потерять маппинги,
        добавленные другими процессами или на сервере.
        """
        try:
            # Перечитываем файл для получения актуальных данных
            existing_mappings = {}
            if Path(self.mappings_file).exists():
                try:
                    with open(self.mappings_file, 'r', encoding='utf-8') as f:
                        existing_mappings = json.load(f)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось загрузить существующие маппинги: {e}")
            
            # Объединяем: приоритет у НОВЫХ маппингов (self.mappings)
            merged_mappings = {**existing_mappings, **self.mappings}
            
            # Сохраняем объединённый результат
            with open(self.mappings_file, 'w', encoding='utf-8') as f:
                json.dump(merged_mappings, f, ensure_ascii=False, indent=2)
            
            # Обновляем локальный кеш
            self.mappings = merged_mappings
            
            logger.info(f"✅ Сопоставления сохранены в {self.mappings_file} (всего записей: {len(merged_mappings)})")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сопоставлений: {e}")
            return False
    
    def _create_mapping_key(self, name: str, color: str = "") -> str:
        """
        Создать уникальный ключ для товара.
        
        Args:
            name: Название товара
            color: Цвет товара
            
        Returns:
            Уникальный ключ
        """
        # Нормализуем название: убираем лишние пробелы, приводим к нижнему регистру
        normalized_name = " ".join(name.lower().split())
        normalized_color = color.lower().strip() if color else ""
        
        if normalized_color:
            return f"{normalized_name}|{normalized_color}"
        return normalized_name
    
    def get_mapping(self, name: str, color: str = "") -> Optional[Dict[str, str | int]]:
        """
        Получить сохранённое сопоставление.
        
        Args:
            name: Название товара
            color: Цвет товара
            
        Returns:
            Словарь с mapped_name, mapped_type и опционально split_units или None
        """
        key = self._create_mapping_key(name, color)
        return self.mappings.get(key)
    
    def save_mapping(self, name: str, color: str, mapped_name: str, mapped_type: str, split_units: Optional[int] = None) -> bool:
        """
        Сохранить новое сопоставление.
        
        Args:
            name: Исходное название товара
            color: Цвет товара
            mapped_name: Сопоставленное название
            mapped_type: Тип товара
            split_units: Количество единиц для разбивки (если товар разбивается)
            
        Returns:
            True если успешно сохранено
        """
        key = self._create_mapping_key(name, color)
        mapping_data: Dict[str, str | int] = {
            'mapped_name': mapped_name,
            'mapped_type': mapped_type,
            'original_name': name,
            'color': color
        }
        
        # Добавляем информацию о разбивке, если она есть
        if split_units and split_units > 1:
            mapping_data['split_units'] = split_units
            
        self.mappings[key] = mapping_data
        return self._save_mappings()
    
    def find_matches(self, name: str, color: str = "") -> list:
        """
        Найти похожие товары в каталоге.
        
        Args:
            name: Название товара для поиска
            color: Цвет товара
            
        Returns:
            Список похожих товаров из каталога
        """
        from sheets_manager import SheetsManager
        
        # Создаём временный объект для использования метода поиска
        # (можно оптимизировать, передавая SheetsManager)
        matches = []
        
        search_lower = name.lower()
        
        for product in self.catalog:
            product_name_lower = product['name'].lower()
            
            # Точное совпадение
            if product_name_lower == search_lower:
                matches.insert(0, {**product, 'match_score': 100})
                continue
            
            # Содержит название
            if search_lower in product_name_lower or product_name_lower in search_lower:
                matches.append({**product, 'match_score': 80})
                continue
            
            # Проверка по словам
            import re
            search_words = set(re.findall(r'\w+', search_lower))
            product_words = set(re.findall(r'\w+', product_name_lower))
            
            if search_words and product_words:
                common_words = search_words & product_words
                if common_words:
                    score = int((len(common_words) / max(len(search_words), len(product_words))) * 70)
                    if score >= 30:
                        matches.append({**product, 'match_score': score})
        
        # Сортируем по score
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches[:5]  # Топ-5


def clarify_color_if_needed(color: str, item_name: str) -> str:
    """
    Уточнить цвет у пользователя если он некорректный (0).
    
    Args:
        color: Текущий цвет ('Black', 'White', '0' или '')
        item_name: Название товара для контекста
        
    Returns:
        Уточнённый цвет ('Black' или 'White')
    """
    from notifier import sync_send_message, sync_wait_for_input
    
    # Если цвет не определён или некорректный - уточняем
    if not color or color == '0':
        logger.info(f"⚠️ Требуется уточнение цвета для: {item_name}")
        
        message = f"""
🎨 <b>УТОЧНЕНИЕ ЦВЕТА</b>

📦 Товар: {item_name}
⚠️ Цвет не определён или некорректный: <code>{color or 'не указан'}</code>

💡 <b>Выберите цвет:</b>
1. Отправьте <code>1</code> - Black (чёрный)
2. Отправьте <code>2</code> - White (белый)

⏳ Ожидаю ваш ответ..."""
        
        sync_send_message(message)
        
        response = sync_wait_for_input(
            "Выберите цвет:", 
            timeout=0, 
            options=[("1", "1️⃣ Black"), ("2", "2️⃣ White")]
        )
        
        if response and response.strip() == '2':
            logger.info(f"✅ Пользователь выбрал цвет: White")
            return 'White'
        else:
            # По умолчанию Black (если 1 или таймаут)
            logger.info(f"✅ Пользователь выбрал цвет: Black (или таймаут)")
            return 'Black'
    
    return color


def split_product_into_units(
    item: Dict,
    matcher: ProductMatcher,
    order_number: Optional[str] = None,
    predefined_units: Optional[int] = None
) -> Optional[tuple[List[Dict], int]]:
    """
    Разбить товар на несколько одинаковых единиц.
    
    Args:
        item: Словарь с данными товара
        matcher: Объект ProductMatcher
        order_number: Номер заказа
        predefined_units: Предопределённое количество единиц (из сохранённого маппинга)
        
    Returns:
        Кортеж (список одинаковых товаров, количество единиц) или None при отмене
    """
    name = item.get('name', '')
    price = item.get('price', 0)
    quantity = item.get('quantity', 1)
    color = item.get('color', '')
    
    logger.info(f"🔧 Разбивка товара на несколько штук: {name[:50]}...")
    
    # Если есть сохранённое значение split_units, используем его
    if predefined_units:
        logger.info(f"✅ Используем сохранённое значение split_units: {predefined_units}")
        num_units = predefined_units
    else:
        # Запрашиваем количество у пользователя
        message = f"""
📦 <b>РАЗБИВКА ТОВАРА НА НЕСКОЛЬКО ШТУК</b>

<b>Товар:</b> {name}
<b>Цвет:</b> {color or 'не указан'}
<b>Цена:</b> {price} ₽
<b>Количество:</b> {quantity}

💡 <b>На сколько штук разбить?</b>

Цена будет разделена между всеми штуками.
В Google Таблицу будет добавлено несколько строк с одинаковым товаром.

⏳ Введите число штук (например: 2, 3, 5) или 0 для отмены..."""
        
        sync_send_message(message)
        
        from notifier import sync_wait_for_input
        units_input = sync_wait_for_input(
            "Введите количество штук или 0:", 
            timeout=0,
            options=[("2", "2️⃣"), ("3", "3️⃣"), ("5", "5️⃣"), ("0", "❌ Отмена")]
        )
        
        if not units_input or units_input.strip() == '0':
            sync_send_message("❌ Разбивка отменена")
            return None
        
        # Парсим количество
        try:
            num_units = int(units_input.strip())
            if num_units < 2:
                sync_send_message("❌ Количество должно быть минимум 2")
                return None
            if num_units > 20:
                sync_send_message("❌ Слишком большое количество (максимум 20)")
                return None
        except ValueError:
            sync_send_message(f"❌ Некорректное число: {units_input}")
            return None
    
    # Вычисляем цену за единицу
    unit_price = round(price / num_units, 2)
    
    # Корректируем последнюю цену чтобы сумма сошлась
    remainder = round(price - (unit_price * (num_units - 1)), 2)
    
    # Создаем список одинаковых товаров
    split_items = []
    for i in range(num_units):
        # Последняя единица получает остаток
        current_price = remainder if i == num_units - 1 else unit_price
        
        split_item = {
            'name': name,
            'color': color,
            'quantity': quantity,  # Сохраняем оригинальное количество для каждой единицы
            'price': current_price,
            'order_number': order_number,
            'original_price': price,  # Сохраняем оригинальную цену
            'split_index': i + 1,  # Индекс разбитой единицы (1, 2, 3...)
            'split_total': num_units,  # Общее количество единиц
            'is_split': True  # Маркер что это разбитый товар
        }
        
        # Копируем остальные поля из оригинального item
        for key in ['url', 'image', 'status', 'date']:
            if key in item:
                split_item[key] = item[key]
        
        split_items.append(split_item)
        logger.info(f"✅ Создана единица {i+1}/{num_units}: {name} = {current_price}₽")
    
    # Проверка суммы
    total = sum(si['price'] for si in split_items)
    if abs(total - price) > 0.01:
        logger.error(f"❌ Ошибка расчета: сумма {total}₽ != оригинал {price}₽")
        sync_send_message(f"❌ Ошибка расчета цены. Разбивка отменена.")
        return None
    
    sync_send_message(f"""
✅ <b>Товар разбит на {num_units} штук!</b>

<b>Товар:</b> {name}
<b>Общая цена:</b> {price} ₽
<b>Цена за единицу:</b> {unit_price} ₽
<b>Последняя единица:</b> {remainder} ₽

Будет добавлено <b>{num_units} строк</b> в Google Таблицу.""")
    
    logger.info(f"✅ Товар разбит на {num_units} единиц: {name} ({price}₽ → {num_units}x{unit_price}₽)")
    
    return split_items, num_units


def match_product_interactive(
    item: Dict,
    matcher: ProductMatcher,
    auto_mode: bool = False,
    order_number: Optional[str] = None,
    excluded_manager: Optional[ExcludedOrdersManager] = None,
    skip_split_option: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    """
    Интерактивное сопоставление товара с подтверждением через Telegram.
    
    Args:
        item: Словарь с данными товара (name, color, quantity, price)
        matcher: ProductMatcher
        auto_mode: Если True, автоматически выбирать лучшее совпадение без запроса
        order_number: Номер заказа (для возможности исключения всего заказа)
        excluded_manager: Менеджер исключённых заказов
        skip_split_option: Если True, не показывать опцию разбивки (используется после разбивки)
        
    Returns:
        Tuple (mapped_name, mapped_type) или (None, None) если заказ исключён
    """
    name = item.get('name', '')
    color = item.get('color', '')
    quantity = item.get('quantity', 1)
    price = item.get('price', 0)
    
    # Проверяем сохранённые сопоставления
    saved_mapping = matcher.get_mapping(name, color)
    if saved_mapping:
        logger.info(f"✅ Найдено сохранённое сопоставление: {name} → {saved_mapping['mapped_name']} ({saved_mapping['mapped_type']})")
        
        # Проверяем, есть ли сохраненная информация о разбивке
        if 'split_units' in saved_mapping:
            try:
                split_units_value = int(saved_mapping['split_units'])
                if split_units_value > 1:
                    logger.info(f"🔧 Применяем сохраненную разбивку: {split_units_value} единиц")
                    # Возвращаем специальный маркер для разбивки
                    return "SPLIT", None
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Некорректное значение split_units в маппинге: {saved_mapping['split_units']}")
        
        # Возвращаем сохраненные значения (гарантированно строки)
        mapped_name = str(saved_mapping['mapped_name'])
        mapped_type = str(saved_mapping['mapped_type'])
        return mapped_name, mapped_type
    
    # Ищем похожие товары в каталоге
    matches = matcher.find_matches(name, color)
    
    # Если 100% совпадение найдено
    if matches and matches[0]['match_score'] == 100:
        best_match = matches[0]
        logger.info(f"✅ 100% совпадение: {name} → {best_match['name']} ({best_match['type']})")
        
        # Автоматически сохраняем и возвращаем
        matcher.save_mapping(name, color, best_match['name'], best_match['type'])
        return best_match['name'], best_match['type']
    
    # Если auto_mode и нет 100% совпадения - используем тип по умолчанию
    if auto_mode:
        if matches:
            best_match = matches[0]
            mapped_name = best_match['name']
            mapped_type = best_match['type']
        else:
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        
        # Уточняем цвет если он некорректный (0) или не указан
        color = clarify_color_if_needed(color, name)
        
        matcher.save_mapping(name, color, mapped_name, mapped_type)
        return mapped_name, mapped_type
    
    # Интерактивный режим: запрашиваем у пользователя
    if not matches:
        # Преобразуем цвет для отображения
        display_color = color if color and color != '0' else 'не указан'
        color_status = ""
        if color == '0':
            color_status = " ⚠️ (требует уточнения)"
        elif color in ['Black', 'White']:
            color_status = f" ✅ (преобразован в {color})"
        
        # Нет совпадений - предлагаем ручной ввод
        message = f"""
🔍 <b>Товар НЕ НАЙДЕН в каталоге</b>

📦 <b>Товар из заказа:</b>
• Название: {name}
• Цвет: {display_color}{color_status}
• Количество: {quantity}
• Цена: {price} ₽"""
        
        if order_number:
            message += f"\n• Заказ: <code>{order_number}</code>"
        
        message += f"""

❓ <b>Предлагаем тип по умолчанию:</b> <code>{matcher.DEFAULT_TYPE}</code>

💡 <b>Варианты ответа:</b>
1. Отправьте <code>1</code> - использовать тип "расходники"
2. Отправьте <code>2</code> - выбрать из каталога (сначала тип, затем товар или название)"""
        
        if not skip_split_option:
            message += "\n3. Отправьте <code>3</code> - разбить на несколько штук"
        
        if order_number and excluded_manager:
            message += f"\n4. Отправьте <code>4</code> - исключить весь заказ {order_number}"
        
        message += "\n\n⏳ Ожидаю ваш ответ..."
        
        sync_send_message(message)
        
        # Собираем кнопки в зависимости от доступных опций
        button_options = [
            ("1", "1️⃣ Расходники"),
            ("2", "2️⃣ Каталог")
        ]
        if not skip_split_option:
            button_options.append(("3", "3️⃣ Разбить"))
        if order_number and excluded_manager:
            button_options.append(("4", "4️⃣ Исключить заказ"))
        
        from notifier import sync_wait_for_input
        response = sync_wait_for_input(
            "Выберите действие:",
            timeout=300,
            options=button_options
        )
        
        if not response:
            logger.warning(f"⏱️ Таймаут ожидания - используем тип по умолчанию для: {name}")
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        elif response.strip() == '1':
            # Использовать тип "расходники"
            logger.info(f"✅ Пользователь выбрал тип 'расходники' для: {name}")
            mapped_name = name
            mapped_type = "расходники"
        elif response.strip() == '3':
            # Разбивка товара на компоненты
            if skip_split_option:
                logger.warning(f"⚠️ Опция разбивки недоступна - используем тип по умолчанию")
                sync_send_message("⚠️ Опция разбивки недоступна на этом этапе")
                mapped_name = name
                mapped_type = matcher.DEFAULT_TYPE
            else:
                logger.info(f"🔧 Пользователь выбрал разбивку для: {name}")
                # Вернем специальный маркер - обработка будет в enrich_orders_with_mapping
                return "SPLIT", None
        elif response.strip() == '4':
            if order_number and excluded_manager:
                # Исключаем весь заказ
                excluded_manager.add_excluded(order_number)
                sync_send_message(f"🚫 <b>Заказ {order_number} исключён!</b>\n\nВсе товары из этого заказа будут пропущены.")
                logger.info(f"🚫 Заказ {order_number} исключён пользователем")
                return None, None
            else:
                logger.warning("⚠️ Невозможно исключить заказ - нет номера заказа или менеджера")
                mapped_name = name
                mapped_type = matcher.DEFAULT_TYPE
        elif response.strip() == '2':
            # Выбор из каталога: сначала тип, затем товар
            logger.info(f"📋 Пользователь выбрал вариант 2 - выбор из каталога для: {name}")
            
            # Шаг 1: Показываем список типов
            type_list_msg = matcher.get_type_list_message()
            sync_send_message(f"{type_list_msg}\n\n⏳ Выберите тип:")
            
            type_button_options = matcher.get_type_button_options()
            type_response = sync_wait_for_input(
                "Выберите номер типа:", 
                timeout=0,
                options=type_button_options
            )
            
            if not type_response or not type_response.strip().isdigit():
                logger.warning(f"⚠️ Некорректный выбор типа - используем тип по умолчанию для: {name}")
                mapped_name = name
                mapped_type = matcher.DEFAULT_TYPE
            else:
                type_number = int(type_response.strip())
                selected_type = matcher.get_type_name(type_number)
                
                if not selected_type:
                    logger.warning(f"⚠️ Некорректный номер типа {type_number} - используем тип по умолчанию")
                    mapped_name = name
                    mapped_type = matcher.DEFAULT_TYPE
                else:
                    logger.info(f"✅ Выбран тип: {selected_type}")
                    
                    # Шаг 2: Фильтруем товары по выбранному типу
                    products_by_type = [p for p in matcher.catalog if p.get('type', '').strip() == selected_type]
                    
                    if not products_by_type:
                        logger.warning(f"⚠️ Нет товаров с типом '{selected_type}'")
                        sync_send_message(f"⚠️ Нет товаров с типом '{selected_type}'\n\nИспользуем тип по умолчанию.")
                        mapped_name = name
                        mapped_type = matcher.DEFAULT_TYPE
                    else:
                        # Сортируем: сначала последние добавленные (из конца таблицы)
                        products_by_type = list(reversed(products_by_type))
                        
                        # Показываем до 10 товаров
                        products_to_show = products_by_type[:10]
                        
                        product_list_msg = f"📦 <b>Товары типа '{selected_type}':</b>\n\n"
                        for idx, product in enumerate(products_to_show, start=1):
                            product_name = product.get('name', 'Без названия')
                            product_price = product.get('price', 0)
                            product_list_msg += f"{idx}. <b>{product_name}</b> - {product_price} ₽\n"
                        
                        product_list_msg += f"\n⏳ Выберите товар (1-{len(products_to_show)}) или введите название:"
                        sync_send_message(product_list_msg)
                        
                        # Создаем кнопки для товаров
                        emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                        product_button_options = []
                        for idx in range(len(products_to_show)):
                            emoji = emoji_numbers[idx] if idx < 10 else f"{idx+1}️⃣"
                            product_button_options.append((str(idx + 1), emoji))
                        
                        product_response = sync_wait_for_input(
                            f"Выберите товар (1-{len(products_to_show)}):",
                            timeout=0,
                            options=product_button_options
                        )
                        
                        if not product_response:
                            logger.warning(f"⚠️ Нет ответа - используем тип по умолчанию")
                            mapped_name = name
                            mapped_type = matcher.DEFAULT_TYPE
                        elif product_response.strip().isdigit():
                            # Пользователь ввел номер товара
                            product_number = int(product_response.strip())
                            if 1 <= product_number <= len(products_to_show):
                                selected_product = products_to_show[product_number - 1]
                                mapped_name = selected_product.get('name', name)
                                mapped_type = selected_product.get('type', selected_type)
                                logger.info(f"✅ Выбран товар по номеру: {mapped_name} ({mapped_type})")
                            else:
                                logger.warning(f"⚠️ Некорректный номер товара {product_number}")
                                mapped_name = name
                                mapped_type = matcher.DEFAULT_TYPE
                        else:
                            # Пользователь ввел название товара - ищем по каталогу
                            search_text = product_response.strip()
                            logger.info(f"🔍 Поиск товара по названию: {search_text}")
                            
                            # Ищем в products_to_show
                            found_product = None
                            search_lower = search_text.lower()
                            
                            for product in products_to_show:
                                product_name_lower = product.get('name', '').lower()
                                # Точное совпадение
                                if product_name_lower == search_lower:
                                    found_product = product
                                    logger.info(f"✅ Найдено точное совпадение: {product.get('name')}")
                                    break
                                # Частичное совпадение
                                elif search_lower in product_name_lower or product_name_lower in search_lower:
                                    if found_product is None:  # Берем первое частичное совпадение
                                        found_product = product
                                        logger.info(f"✅ Найдено частичное совпадение: {product.get('name')}")
                            
                            if found_product:
                                mapped_name = found_product.get('name', name)
                                mapped_type = found_product.get('type', selected_type)
                                sync_send_message(f"✅ Выбран товар: <b>{mapped_name}</b> ({mapped_type})")
                            else:
                                logger.warning(f"⚠️ Товар '{search_text}' не найден в списке - используем тип по умолчанию")
                                sync_send_message(f"⚠️ Товар '{search_text}' не найден в списке")
                                mapped_name = name
                                mapped_type = matcher.DEFAULT_TYPE
        else:
            logger.warning(f"⚠️ Некорректный ответ '{response}' - используем тип по умолчанию для: {name}")
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        
        # Уточняем цвет если он некорректный (0) или не указан
        color = clarify_color_if_needed(color, name)
        
        matcher.save_mapping(name, color, mapped_name, mapped_type)
        return mapped_name, mapped_type
    
    # Есть совпадения, но не 100% - показываем варианты
    # Преобразуем цвет для отображения
    display_color = color if color and color != '0' else 'не указан'
    color_status = ""
    if color == '0':
        color_status = " ⚠️ (требует уточнения)"
    elif color in ['Black', 'White']:
        color_status = f" ✅ (преобразован в {color})"
    
    message = f"""
🔍 <b>Найдены похожие товары</b>

📦 <b>Товар из заказа:</b>
• Название: {name}
• Цвет: {display_color}{color_status}
• Количество: {quantity}
• Цена: {price} ₽"""
    
    if order_number:
        message += f"\n• Заказ: <code>{order_number}</code>"
    
    message += "\n\n✅ <b>Предлагаемые варианты:</b>"
    
    # Собираем уникальные названия и типы
    unique_names = []
    unique_types = []
    
    for idx, match in enumerate(matches[:5], start=1):
        message += f"\n{idx}. <b>{match['name']}</b> ({match['type']}) - {match['match_score']}%"
        
        if match['name'] not in unique_names:
            unique_names.append(match['name'])
        if match['type'] not in unique_types:
            unique_types.append(match['type'])
    
    message += "\n\n💡 <b>Варианты ответа:</b>\n"
    message += "• <code>1-5</code> - выбрать вариант по номеру\n"
    message += "• <code>6</code> - выбрать из каталога (сначала тип, затем товар или название)"
    
    if not skip_split_option:
        message += "\n• <code>7</code> - разбить на несколько штук"
    
    if order_number and excluded_manager:
        message += f"\n• <code>8</code> - исключить весь заказ {order_number}"
    
    message += "\n\n⏳ Ожидаю ваш ответ..."
    
    sync_send_message(message)
    
    # Собираем кнопки (1-5 для совпадений + дополнительные опции)
    button_options = [(str(i+1), f"{i+1}️⃣") for i in range(min(5, len(matches)))]
    button_options.append(("6", "6️⃣ Каталог"))
    if not skip_split_option:
        button_options.append(("7", "7️⃣ Разбить"))
    if order_number and excluded_manager:
        button_options.append(("8", "8️⃣ Исключить"))
    
    from notifier import sync_wait_for_input
    response = sync_wait_for_input(
        "Выберите вариант:",
        timeout=300,
        options=button_options
    )
    
    if not response:
        # Таймаут - используем лучшее совпадение
        logger.warning(f"⏱️ Таймаут - используем лучшее совпадение для: {name}")
        best_match = matches[0]
        mapped_name = best_match['name']
        mapped_type = best_match['type']
    elif response.strip() == '7':
        # Разбивка товара
        if skip_split_option:
            logger.warning(f"⚠️ Опция разбивки недоступна - используем лучшее совпадение")
            sync_send_message("⚠️ Опция разбивки недоступна на этом этапе")
            best_match = matches[0]
            mapped_name = best_match['name']
            mapped_type = best_match['type']
        else:
            logger.info(f"🔧 Пользователь выбрал разбивку для: {name}")
            return "SPLIT", None
    elif response.strip() == '8':
        if order_number and excluded_manager:
            excluded_manager.add_excluded(order_number)
            sync_send_message(f"🚫 <b>Заказ {order_number} исключён!</b>\n\nВсе товары из этого заказа будут пропущены.")
            logger.info(f"🚫 Заказ {order_number} исключён пользователем")
            return None, None
        else:
            logger.warning("⚠️ Невозможно исключить заказ - нет номера заказа или менеджера")
            best_match = matches[0]
            mapped_name = best_match['name']
            mapped_type = best_match['type']
    elif response.strip() == '6':
        # Выбор из каталога: сначала тип, затем товар
        logger.info(f"📋 Пользователь выбрал вариант 6 - выбор из каталога для: {name}")
        
        # Шаг 1: Показываем список типов
        type_list_msg = matcher.get_type_list_message()
        sync_send_message(f"{type_list_msg}\n\n⏳ Выберите тип:")
        
        type_button_options = matcher.get_type_button_options()
        type_response = sync_wait_for_input(
            "Выберите номер типа:", 
            timeout=0,
            options=type_button_options
        )
        
        if not type_response or not type_response.strip().isdigit():
            logger.warning(f"⚠️ Некорректный выбор типа - используем лучшее совпадение")
            best_match = matches[0]
            mapped_name = best_match['name']
            mapped_type = best_match['type']
        else:
            type_number = int(type_response.strip())
            selected_type = matcher.get_type_name(type_number)
            
            if not selected_type:
                logger.warning(f"⚠️ Некорректный номер типа {type_number} - используем лучшее совпадение")
                best_match = matches[0]
                mapped_name = best_match['name']
                mapped_type = best_match['type']
            else:
                logger.info(f"✅ Выбран тип: {selected_type}")
                
                # Шаг 2: Фильтруем товары по выбранному типу
                products_by_type = [p for p in matcher.catalog if p.get('type', '').strip() == selected_type]
                
                if not products_by_type:
                    logger.warning(f"⚠️ Нет товаров с типом '{selected_type}'")
                    sync_send_message(f"⚠️ Нет товаров с типом '{selected_type}'\n\nИспользуем лучшее совпадение.")
                    best_match = matches[0]
                    mapped_name = best_match['name']
                    mapped_type = best_match['type']
                else:
                    # Сортируем: сначала последние добавленные (из конца таблицы)
                    products_by_type = list(reversed(products_by_type))
                    
                    # Показываем до 10 товаров
                    products_to_show = products_by_type[:10]
                    
                    product_list_msg = f"📦 <b>Товары типа '{selected_type}':</b>\n\n"
                    for idx, product in enumerate(products_to_show, start=1):
                        product_name = product.get('name', 'Без названия')
                        product_price = product.get('price', 0)
                        product_list_msg += f"{idx}. <b>{product_name}</b> - {product_price} ₽\n"
                    
                    product_list_msg += f"\n⏳ Выберите товар (1-{len(products_to_show)}) или введите название:"
                    sync_send_message(product_list_msg)
                    
                    # Создаем кнопки для товаров
                    emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                    product_button_options = []
                    for idx in range(len(products_to_show)):
                        emoji = emoji_numbers[idx] if idx < 10 else f"{idx+1}️⃣"
                        product_button_options.append((str(idx + 1), emoji))
                    
                    product_response = sync_wait_for_input(
                        f"Выберите товар (1-{len(products_to_show)}):",
                        timeout=0,
                        options=product_button_options
                    )
                    
                    if not product_response:
                        logger.warning(f"⚠️ Нет ответа - используем лучшее совпадение")
                        best_match = matches[0]
                        mapped_name = best_match['name']
                        mapped_type = best_match['type']
                    elif product_response.strip().isdigit():
                        # Пользователь ввел номер товара
                        product_number = int(product_response.strip())
                        if 1 <= product_number <= len(products_to_show):
                            selected_product = products_to_show[product_number - 1]
                            mapped_name = selected_product.get('name', name)
                            mapped_type = selected_product.get('type', selected_type)
                            logger.info(f"✅ Выбран товар по номеру: {mapped_name} ({mapped_type})")
                        else:
                            logger.warning(f"⚠️ Некорректный номер товара {product_number}")
                            best_match = matches[0]
                            mapped_name = best_match['name']
                            mapped_type = best_match['type']
                    else:
                        # Пользователь ввел название товара - ищем по каталогу
                        search_text = product_response.strip()
                        logger.info(f"🔍 Поиск товара по названию: {search_text}")
                        
                        # Ищем в products_to_show
                        found_product = None
                        search_lower = search_text.lower()
                        
                        for product in products_to_show:
                            product_name_lower = product.get('name', '').lower()
                            # Точное совпадение
                            if product_name_lower == search_lower:
                                found_product = product
                                logger.info(f"✅ Найдено точное совпадение: {product.get('name')}")
                                break
                            # Частичное совпадение
                            elif search_lower in product_name_lower or product_name_lower in search_lower:
                                if found_product is None:  # Берем первое частичное совпадение
                                    found_product = product
                                    logger.info(f"✅ Найдено частичное совпадение: {product.get('name')}")
                        
                        if found_product:
                            mapped_name = found_product.get('name', name)
                            mapped_type = found_product.get('type', selected_type)
                            sync_send_message(f"✅ Выбран товар: <b>{mapped_name}</b> ({mapped_type})")
                        else:
                            logger.warning(f"⚠️ Товар '{search_text}' не найден в списке - используем лучшее совпадение")
                            sync_send_message(f"⚠️ Товар '{search_text}' не найден в списке")
                            best_match = matches[0]
                            mapped_name = best_match['name']
                            mapped_type = best_match['type']
    elif response.strip().isdigit():
        # Выбран номер из предложенных совпадений
        choice = int(response.strip())
        if 1 <= choice <= min(5, len(matches)):
            selected = matches[choice - 1]
            mapped_name = selected['name']
            mapped_type = selected['type']
            logger.info(f"✅ Пользователь выбрал вариант {choice}: {mapped_name} ({mapped_type})")
        else:
            logger.warning(f"⚠️ Некорректный номер - используем лучшее совпадение для: {name}")
            best_match = matches[0]
            mapped_name = best_match['name']
            mapped_type = best_match['type']
    else:
        # Некорректный ответ - используем лучшее совпадение
        logger.warning(f"⚠️ Некорректный ответ '{response}' - используем лучшее совпадение для: {name}")
        best_match = matches[0]
        mapped_name = best_match['name']
        mapped_type = best_match['type']
    
    # Уточняем цвет если он некорректный (0) или не указан
    color = clarify_color_if_needed(color, name)
    
    # Сохраняем сопоставление
    matcher.save_mapping(name, color, mapped_name, mapped_type)
    
    return mapped_name, mapped_type


def enrich_orders_with_mapping(
    orders_data: list, 
    matcher: ProductMatcher, 
    interactive: bool = True, 
    excluded_manager: Optional[ExcludedOrdersManager] = None,
    bundle_manager: Optional[BundleManager] = None
) -> list:
    """
    Обогатить данные заказов сопоставлениями из каталога.
    
    Args:
        orders_data: Список заказов с товарами
        matcher: Объект ProductMatcher
        interactive: Если True, использовать интерактивный режим через Telegram
        excluded_manager: Менеджер исключённых заказов (для возможности исключения)
        bundle_manager: Менеджер связок товаров (для разбивки на компоненты)
        
    Returns:
        Обогащённый список заказов (без исключённых)
    """
    logger.info("🔄 Начинаем сопоставление товаров с каталогом...")
    
    # Инициализируем bundle_manager если не передан
    if bundle_manager is None:
        bundle_manager = BundleManager()
    
    # Сначала извлекаем уникальные товары с информацией о заказах
    unique_items_dict = {}
    item_to_orders = {}  # Для отслеживания, в каких заказах встречается товар
    
    for order in orders_data:
        order_number = order.get('order_number', '')
        for item in order.get('items', []):
            key = f"{item['name']}|{item.get('color', '')}"
            if key not in unique_items_dict:
                unique_items_dict[key] = item.copy()
                item_to_orders[key] = []
            
            if order_number not in item_to_orders[key]:
                item_to_orders[key].append(order_number)
    
    unique_items = list(unique_items_dict.values())
    logger.info(f"📦 Уникальных товаров для сопоставления: {len(unique_items)}")
    
    # Создаём кеш сопоставлений
    mapping_cache = {}
    orders_to_exclude = set()
    
    # Сопоставляем каждый уникальный товар
    for idx, item in enumerate(unique_items, 1):
        logger.info(f"[{idx}/{len(unique_items)}] Обрабатываем: {item['name']}")
        
        key = f"{item['name']}|{item.get('color', '')}"
        
        # Берём первый заказ из списка для контекста
        order_numbers = item_to_orders.get(key, [])
        first_order = order_numbers[0] if order_numbers else None
        
        # 🔧 АВТОМАТИЧЕСКАЯ РАЗБИВКА: проверяем сохранённый маппинг на split_units
        saved_mapping = matcher.get_mapping(item['name'], item.get('color', ''))
        split_units_raw = saved_mapping.get('split_units', 0) if saved_mapping else 0
        if saved_mapping and split_units_raw:
            try:
                split_units = int(split_units_raw) if isinstance(split_units_raw, (int, str)) else 0
            except (ValueError, TypeError):
                split_units = 0
            
            if split_units > 1:
                mapped_name = saved_mapping['mapped_name']
                mapped_type = saved_mapping['mapped_type']
                
                logger.info(f"🔄 Авто-разбивка на {split_units} единиц (из сохранённого маппинга): {item['name'][:50]}...")
                
                # Создаём разбивку с предопределённым количеством единиц
                split_result = split_product_into_units(item, matcher, first_order, predefined_units=split_units)
                
                if split_result:
                    split_items, num_units = split_result
                    
                    # Применяем сохранённый маппинг к каждой единице
                    for split_item in split_items:
                        split_item['mapped_name'] = mapped_name
                        split_item['mapped_type'] = mapped_type
                    
                    # Сохраняем в кеш
                    mapping_cache[key] = {'is_split': True, 'split_items': split_items, 'split_units': num_units}
                    logger.info(f"✅ Авто-разбит на {len(split_items)} единиц: {mapped_name} ({mapped_type})")
                    continue
                else:
                    logger.warning(f"⚠️ Авто-разбивка не удалась, переход к интерактивному режиму")
        
        # Используем интерактивный или автоматический режим
        mapped_name, mapped_type = match_product_interactive(
            item, 
            matcher, 
            auto_mode=not interactive,
            order_number=first_order,
            excluded_manager=excluded_manager
        )
        
        # Если товар исключён (заказ исключён)
        if mapped_name is None and mapped_type is None:
            logger.info(f"🚫 Товар из исключённого заказа: {item['name']}")
            # Добавляем все заказы с этим товаром в список исключённых
            orders_to_exclude.update(order_numbers)
            continue
        
        # Обработка разбивки товара на единицы
        if mapped_name == "SPLIT" and mapped_type is None:
            logger.info(f"🔧 Разбивка товара на единицы: {item['name'][:50]}...")
            
            # Проверяем, есть ли сохраненная информация о split_units
            saved_mapping = matcher.get_mapping(item['name'], item.get('color', ''))
            saved_split_units = None
            if saved_mapping and 'split_units' in saved_mapping:
                try:
                    saved_split_units = int(saved_mapping['split_units'])
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Некорректное значение split_units: {saved_mapping['split_units']}")
                    saved_split_units = None
            
            # Создаём новую разбивку на единицы (или используем сохраненное значение)
            split_result = split_product_into_units(item, matcher, first_order, predefined_units=saved_split_units)
            
            if split_result:
                split_items, num_units = split_result
                # Разбивка успешна - сохраняем список единиц
                mapping_cache[key] = {'is_split': True, 'split_items': split_items, 'split_units': num_units}
                logger.info(f"✅ Разбит на {len(split_items)} единиц: {item['name'][:50]}...")
                
                # После разбивки задаем вопрос заново, но БЕЗ опции разбивки
                logger.info(f"🔄 Повторное сопоставление после разбивки: {item['name'][:50]}...")
                mapped_name, mapped_type = match_product_interactive(
                    item, 
                    matcher, 
                    auto_mode=not interactive,
                    order_number=first_order,
                    excluded_manager=excluded_manager,
                    skip_split_option=True  # Не показывать опцию разбивки
                )
                
                # Обновляем маппинг для каждой единицы + сохраняем split_units
                if mapped_name and mapped_type:
                    for split_item in split_items:
                        split_item['mapped_name'] = mapped_name
                        split_item['mapped_type'] = mapped_type
                    logger.info(f"✅ Маппинг применен к {len(split_items)} единицам: {mapped_name} ({mapped_type})")
                    
                    # Сохраняем mapping с информацией о разбивке
                    matcher.save_mapping(item['name'], item.get('color', ''), mapped_name, mapped_type, split_units=num_units)
                
                # ВАЖНО: НЕ перезаписываем mapping_cache - разбивка уже сохранена выше!
                # mapping_cache[key] уже содержит {'is_split': True, 'split_items': split_items, 'split_units': num_units}
            else:
                logger.warning(f"⚠️ Разбивка отменена для: {item['name'][:50]}...")
                # Fallback к обычному маппингу
                mapping_cache[key] = {
                    'mapped_name': item['name'],
                    'mapped_type': matcher.DEFAULT_TYPE
                }
            
            continue
        
        mapping_cache[key] = {
            'mapped_name': mapped_name,
            'mapped_type': mapped_type
        }
        
        logger.info(f"✅ [{idx}/{len(unique_items)}] {item['name']} → {mapped_name} ({mapped_type})")
    
    # Применяем сопоставления ко всем товарам (исключая исключённые заказы)
    enriched_orders = []
    total_items = 0
    matched_items = 0
    excluded_orders_count = 0
    
    for order in orders_data:
        order_number = order.get('order_number', '')
        
        # Пропускаем исключённые заказы
        if order_number in orders_to_exclude:
            excluded_orders_count += 1
            logger.info(f"⏭️ Пропускаем исключённый заказ: {order_number}")
            continue
        
        enriched_order = order.copy()
        enriched_items = []
        
        for item in order.get('items', []):
            total_items += 1
            
            key = f"{item['name']}|{item.get('color', '')}"
            
            # Проверяем кеш
            if key in mapping_cache:
                cache_entry = mapping_cache[key]
                
                # Если это разбитый товар - добавляем все единицы
                if cache_entry.get('is_split'):
                    split_items = cache_entry['split_items']
                    # Добавляем каждую единицу как отдельную строку
                    for split_item in split_items:
                        enriched_item = split_item.copy()
                        # Применяем маппинг - используем уже установленные значения из split_item
                        enriched_item['mapped_name'] = split_item.get('mapped_name', split_item['name'])
                        enriched_item['mapped_type'] = split_item.get('mapped_type', matcher.DEFAULT_TYPE)
                        enriched_items.append(enriched_item)
                        matched_items += 1
                    logger.info(f"📦 Добавлено {len(split_items)} единиц для: {item['name'][:30]}")
                else:
                    # Обычный маппинг
                    enriched_item = item.copy()
                    enriched_item['mapped_name'] = cache_entry['mapped_name']
                    enriched_item['mapped_type'] = cache_entry['mapped_type']
                    enriched_items.append(enriched_item)
                    matched_items += 1
            else:
                # На всякий случай, если что-то пропустили
                enriched_item = item.copy()
                enriched_item['mapped_name'] = item['name']
                enriched_item['mapped_type'] = matcher.DEFAULT_TYPE
                enriched_items.append(enriched_item)

        
        enriched_order['items'] = enriched_items
        enriched_orders.append(enriched_order)
    
    logger.info(f"✅ Сопоставлено товаров: {matched_items}/{total_items}")
    if excluded_orders_count > 0:
        logger.info(f"🚫 Исключено заказов: {excluded_orders_count}")
    
    return enriched_orders
