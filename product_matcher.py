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
    
    def _load_mappings(self) -> Dict[str, Dict[str, str]]:
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
        """Сохранить сопоставления в файл."""
        try:
            with open(self.mappings_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Сопоставления сохранены в {self.mappings_file}")
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
    
    def get_mapping(self, name: str, color: str = "") -> Optional[Dict[str, str]]:
        """
        Получить сохранённое сопоставление.
        
        Args:
            name: Название товара
            color: Цвет товара
            
        Returns:
            Словарь с mapped_name и mapped_type или None
        """
        key = self._create_mapping_key(name, color)
        return self.mappings.get(key)
    
    def save_mapping(self, name: str, color: str, mapped_name: str, mapped_type: str) -> bool:
        """
        Сохранить новое сопоставление.
        
        Args:
            name: Исходное название товара
            color: Цвет товара
            mapped_name: Сопоставленное название
            mapped_type: Тип товара
            
        Returns:
            True если успешно сохранено
        """
        key = self._create_mapping_key(name, color)
        self.mappings[key] = {
            'mapped_name': mapped_name,
            'mapped_type': mapped_type,
            'original_name': name,
            'color': color
        }
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


def split_product_interactive(
    item: Dict,
    matcher: ProductMatcher,
    bundle_manager: BundleManager,
    order_number: Optional[str] = None
) -> Optional[Dict]:
    """
    Интерактивная разбивка товара на компоненты через Telegram.
    
    Args:
        item: Словарь с данными товара
        matcher: Объект ProductMatcher
        bundle_manager: Менеджер связок
        order_number: Номер заказа
        
    Returns:
        Item с компонентами или None при отмене
    """
    name = item.get('name', '')
    price = item.get('price', 0)
    quantity = item.get('quantity', 1)
    
    logger.info(f"🔧 Начало разбивки товара: {name[:50]}...")
    
    # Показываем список типов
    type_list_msg = matcher.get_type_list_message()
    
    message = f"""
📦 <b>РАЗБИВКА ТОВАРА</b>

<b>Товар:</b> {name}
<b>Цена:</b> {price} ₽
<b>Количество:</b> {quantity}

{type_list_msg}

💡 <b>Введите схему разбивки:</b>
Формат: <code>тип1-тип2-тип3</code>

Пример: <code>2-3-5</code> означает:
• 1-я часть: тип 2 (корпус)
• 2-я часть: тип 3 (кулер)  
• 3-я часть: тип 5 (блок питания)

⏳ Ожидаю схему разбивки..."""
    
    sync_send_message(message)
    
    from notifier import sync_wait_for_input
    schema_input = sync_wait_for_input("Введите схему (например: 2-3-5) или CANCEL:", timeout=300)
    
    if not schema_input or schema_input.upper() == 'CANCEL':
        sync_send_message("❌ Разбивка отменена")
        return None
    
    # Парсим схему
    try:
        type_numbers = [int(x.strip()) for x in schema_input.split('-')]
    except ValueError:
        sync_send_message(f"❌ Некорректная схема: {schema_input}\nОжидался формат: 2-3-5")
        return None
    
    # Проверяем валидность типов
    invalid_types = [t for t in type_numbers if t not in matcher.type_map]
    if invalid_types:
        sync_send_message(f"❌ Некорректные номера типов: {invalid_types}\n\n{type_list_msg}")
        return None
    
    components = []
    
    # Для каждого типа выбираем товар и цену
    for i, type_num in enumerate(type_numbers, 1):
        type_name = matcher.get_type_name(type_num)
        
        # Получаем товары этого типа
        type_products = [p for p in matcher.catalog if p.get('type') == type_name]
        
        if not type_products:
            sync_send_message(f"⚠️ Нет товаров типа '{type_name}' в каталоге. Пропускаем.")
            continue
        
        # Показываем варианты
        variants_msg = f"""
🔧 <b>Часть {i}/{len(type_numbers)}</b>

<b>Тип:</b> {type_name}

<b>Выберите товар:</b>
"""
        for idx, product in enumerate(type_products[:15], 1):  # Максимум 15 вариантов
            variants_msg += f"\n{idx}. {product['name']} ({product.get('price', 0)} ₽)"
        
        variants_msg += "\n\n💡 Введите номер товара:"
        
        sync_send_message(variants_msg)
        
        choice = sync_wait_for_input(f"Выберите товар (1-{min(15, len(type_products))}):", timeout=180)
        
        if not choice or not choice.isdigit():
            sync_send_message(f"❌ Некорректный выбор. Отмена разбивки.")
            return None
        
        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= len(type_products):
            sync_send_message(f"❌ Номер вне диапазона. Отмена разбивки.")
            return None
        
        selected_product = type_products[choice_idx]
        
        # Запрашиваем цену
        price_msg = f"""
💰 <b>Укажите цену для:</b>
{selected_product['name']}

<b>Рекомендуемая цена:</b> {selected_product.get('price', 0)} ₽

💡 Введите цену (число):"""
        
        sync_send_message(price_msg)
        
        price_input = sync_wait_for_input("Введите цену:", timeout=120)
        
        if not price_input:
            sync_send_message(f"❌ Цена не указана. Отмена разбивки.")
            return None
        
        try:
            component_price = float(price_input.replace(',', '.'))
        except ValueError:
            sync_send_message(f"❌ Некорректная цена: {price_input}")
            return None
        
        components.append({
            "mapped_name": selected_product['name'],
            "mapped_type": type_name,
            "price": component_price
        })
        
        logger.info(f"✅ Добавлен компонент {i}: {selected_product['name']} = {component_price}₽")
    
    if not components:
        sync_send_message("❌ Не добавлено ни одного компонента")
        return None
    
    # Проверка суммы
    max_attempts = 3
    for attempt in range(max_attempts):
        total = sum(c['price'] for c in components)
        
        if abs(total - price) < 0.01:  # Совпадение
            break
        
        sync_send_message(f"""
⚠️ <b>Несовпадение суммы!</b>

Сумма компонентов: {total} ₽
Цена товара: {price} ₽
Разница: {total - price} ₽

💡 <b>Введите цены заново:</b>""")
        
        # Перезапрос цен
        for i, component in enumerate(components, 1):
            price_msg = f"""
💰 <b>Цена {i}/{len(components)}:</b>
{component['mapped_name']}

Текущая цена: {component['price']} ₽

Введите новую цену:"""
            
            sync_send_message(price_msg)
            
            price_input = sync_wait_for_input(f"Цена для {component['mapped_name']}:", timeout=120)
            
            if price_input:
                try:
                    component['price'] = float(price_input.replace(',', '.'))
                except ValueError:
                    pass
    
    # Финальная проверка
    total = sum(c['price'] for c in components)
    if abs(total - price) >= 0.01:
        sync_send_message(f"""
❌ <b>Суммы не совпадают после {max_attempts} попыток!</b>

Сумма: {total} ₽
Нужно: {price} ₽

Разбивка отменена.""")
        return None
    
    # Сохраняем связку
    if bundle_manager.create_bundle(name, components, price):
        sync_send_message(f"""
✅ <b>Связка создана!</b>

<b>Товар:</b> {name}
<b>Компонентов:</b> {len(components)}
<b>Общая цена:</b> {price} ₽

Детали:""")
        
        for i, comp in enumerate(components, 1):
            sync_send_message(f"{i}. {comp['mapped_name']} = {comp['price']}₽")
        
        # Создаём bundle item
        bundle_item = create_bundle_item(item, components)
        logger.info(f"✅ Создан bundle item для: {name[:50]}...")
        return bundle_item
    
    sync_send_message("❌ Ошибка сохранения связки")
    return None


def match_product_interactive(
    item: Dict,
    matcher: ProductMatcher,
    auto_mode: bool = False,
    order_number: Optional[str] = None,
    excluded_manager: Optional[ExcludedOrdersManager] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Интерактивное сопоставление товара с подтверждением через Telegram.
    
    Args:
        item: Словарь с данными товара (name, color, quantity, price)
        matcher: Объект ProductMatcher
        auto_mode: Если True, автоматически выбирать лучшее совпадение без запроса
        order_number: Номер заказа (для возможности исключения всего заказа)
        excluded_manager: Менеджер исключённых заказов
        
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
        return saved_mapping['mapped_name'], saved_mapping['mapped_type']
    
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
        
        matcher.save_mapping(name, color, mapped_name, mapped_type)
        return mapped_name, mapped_type
    
    # Интерактивный режим: запрашиваем у пользователя
    if not matches:
        # Нет совпадений - предлагаем ручной ввод
        message = f"""
🔍 <b>Товар НЕ НАЙДЕН в каталоге</b>

📦 <b>Товар из заказа:</b>
• Название: {name}
• Цвет: {color or 'не указан'}
• Количество: {quantity}
• Цена: {price} ₽"""
        
        if order_number:
            message += f"\n• Заказ: <code>{order_number}</code>"
        
        message += f"""

❓ <b>Предлагаем тип по умолчанию:</b> <code>{matcher.DEFAULT_TYPE}</code>

💡 <b>Варианты ответа:</b>
1. Отправьте <code>OK</code> - использовать тип "{matcher.DEFAULT_TYPE}"
2. Отправьте <code>Название | Тип</code> - ввести вручную
3. Отправьте <code>Р</code> - разбить товар на компоненты"""
        
        if order_number and excluded_manager:
            message += f"\n4. Отправьте <code>EXCLUDE</code> - исключить весь заказ {order_number}"
        
        message += "\n\n⏳ Ожидаю ваш ответ..."
        
        sync_send_message(message)
        
        from notifier import sync_wait_for_input
        response = sync_wait_for_input(
            "Отправьте OK, EXCLUDE или введите 'Название | Тип':",
            timeout=300
        )
        
        if not response:
            logger.warning(f"⏱️ Таймаут ожидания - используем тип по умолчанию для: {name}")
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        elif response.upper() == 'Р':
            # Разбивка товара
            logger.info(f"🔧 Пользователь выбрал разбивку для: {name}")
            # Вернем специальный маркер - обработка будет в enrich_orders_with_mapping
            return "SPLIT", None
        elif response.upper() == 'EXCLUDE':
            if order_number and excluded_manager:
                excluded_manager.add_excluded(order_number)
                sync_send_message(f"🚫 <b>Заказ {order_number} исключён!</b>\n\nВсе товары из этого заказа будут пропущены.")
                logger.info(f"🚫 Заказ {order_number} исключён пользователем")
                return None, None
            else:
                logger.warning("⚠️ Невозможно исключить заказ - нет номера заказа или менеджера")
                mapped_name = name
                mapped_type = matcher.DEFAULT_TYPE
        elif response.upper() == 'OK':
            logger.info(f"✅ Пользователь подтвердил тип по умолчанию для: {name}")
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        elif '|' in response:
            parts = response.split('|', 1)
            mapped_name = parts[0].strip()
            mapped_type = parts[1].strip()
            logger.info(f"✅ Пользователь ввёл вручную: {mapped_name} | {mapped_type}")
        else:
            logger.warning(f"⚠️ Некорректный ответ - используем тип по умолчанию для: {name}")
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        
        matcher.save_mapping(name, color, mapped_name, mapped_type)
        return mapped_name, mapped_type
    
    # Есть совпадения, но не 100% - показываем варианты
    message = f"""
🔍 <b>Найдены похожие товары</b>

📦 <b>Товар из заказа:</b>
• Название: {name}
• Цвет: {color or 'не указан'}
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
    message += "• <code>Название | Тип</code> - ввести вручную\n"
    message += "• <code>Р</code> - разбить товар на компоненты"
    
    if order_number and excluded_manager:
        message += f"\n• <code>EXCLUDE</code> - исключить весь заказ {order_number}"
    
    message += "\n\n⏳ Ожидаю ваш ответ..."
    
    sync_send_message(message)
    
    from notifier import sync_wait_for_input
    response = sync_wait_for_input(
        "Выберите номер (1-5), EXCLUDE или введите 'Название | Тип':",
        timeout=300
    )
    
    if not response:
        # Таймаут - используем лучшее совпадение
        logger.warning(f"⏱️ Таймаут - используем лучшее совпадение для: {name}")
        best_match = matches[0]
        mapped_name = best_match['name']
        mapped_type = best_match['type']
    elif response.upper() == 'Р':
        # Разбивка товара
        logger.info(f"🔧 Пользователь выбрал разбивку для: {name}")
        return "SPLIT", None
    elif response.upper() == 'EXCLUDE':
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
    elif response.isdigit():
        # Выбран номер
        choice = int(response)
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
    elif '|' in response:
        # Ручной ввод
        parts = response.split('|', 1)
        mapped_name = parts[0].strip()
        mapped_type = parts[1].strip()
        logger.info(f"✅ Пользователь ввёл вручную: {mapped_name} | {mapped_type}")
    else:
        # Некорректный ответ - используем лучшее
        logger.warning(f"⚠️ Некорректный ответ - используем лучшее совпадение для: {name}")
        best_match = matches[0]
        mapped_name = best_match['name']
        mapped_type = best_match['type']
    
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
        
        # Обработка разбивки товара
        if mapped_name == "SPLIT" and mapped_type is None:
            logger.info(f"🔧 Разбивка товара: {item['name'][:50]}...")
            
            # Проверяем, есть ли уже сохранённая связка
            if bundle_manager.has_bundle(item['name']):
                existing_bundle = bundle_manager.get_bundle(item['name'])
                
                # Проверяем что связка успешно получена
                if existing_bundle:
                    # Показываем детали и спрашиваем про переиспользование
                    from notifier import sync_send_message, sync_wait_for_input
                    
                    reuse_msg = f"""
📦 <b>Найдена сохранённая связка!</b>

<b>Товар:</b> {item['name']}
<b>Компонентов:</b> {len(existing_bundle['components'])}

<b>Детали:</b>"""
                    sync_send_message(reuse_msg)
                    
                    for i, comp in enumerate(existing_bundle['components'], 1):
                        sync_send_message(
                            f"  {i}. {comp['mapped_name']} ({comp['mapped_type']}) = {comp['price']}₽"
                        )
                    
                    sync_send_message("\n💡 <b>Варианты ответа:</b>\n• <code>ДА</code> - использовать сохранённую\n• <code>НЕТ</code> - создать новую")
                    
                    reuse_response = sync_wait_for_input("ДА или НЕТ:", timeout=120)
                    
                    if reuse_response and reuse_response.upper() == 'ДА':
                        # Переиспользуем существующую связку
                        bundle_item = create_bundle_item(item, existing_bundle['components'])
                        mapping_cache[key] = {'is_bundle': True, 'bundle_item': bundle_item}
                        logger.info(f"♻️ Переиспользована связка для: {item['name'][:50]}...")
                        continue
            
            # Создаём новую связку
            bundle_item = split_product_interactive(item, matcher, bundle_manager, first_order)
            
            if bundle_item:
                mapping_cache[key] = {'is_bundle': True, 'bundle_item': bundle_item}
                logger.info(f"✅ Создана связка для: {item['name'][:50]}...")
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
                
                # Если это связка - заменяем товар на компоненты
                if cache_entry.get('is_bundle'):
                    bundle_item = cache_entry['bundle_item']
                    # Добавляем каждый компонент как отдельный товар
                    for component in bundle_item['components']:
                        component_item = {
                            'name': item['name'],  # Оригинальное название
                            'price': component['price'],
                            'quantity': item['quantity'],
                            'color': item.get('color', ''),
                            'mapped_name': component['mapped_name'],
                            'mapped_type': component['mapped_type'],
                            'is_bundle_component': True,
                            'bundle_key': item['name']
                        }
                        enriched_items.append(component_item)
                        matched_items += 1
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
