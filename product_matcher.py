"""
Модуль для сопоставления товаров с каталогом и интерактивного подтверждения через Telegram.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from loguru import logger
from notifier import sync_send_message
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
        
        logger.info(f"🔄 Загружено товаров из каталога: {len(self.catalog)}")
        logger.info(f"📋 Загружено сохранённых сопоставлений: {len(self.mappings)}")
    
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


def match_product_interactive(
    item: Dict,
    matcher: ProductMatcher,
    auto_mode: bool = False
) -> Tuple[str, str]:
    """
    Интерактивное сопоставление товара с подтверждением через Telegram.
    
    Args:
        item: Словарь с данными товара (name, color, quantity, price)
        matcher: Объект ProductMatcher
        auto_mode: Если True, автоматически выбирать лучшее совпадение без запроса
        
    Returns:
        Tuple (mapped_name, mapped_type)
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
• Цена: {price} ₽

❓ <b>Предлагаем тип по умолчанию:</b> <code>{matcher.DEFAULT_TYPE}</code>

💡 <b>Варианты ответа:</b>
1. Отправьте <code>OK</code> - использовать тип "{matcher.DEFAULT_TYPE}"
2. Отправьте <code>Название | Тип</code> - ввести вручную

⏳ Ожидаю ваш ответ...
        """
        
        sync_send_message(message)
        
        from notifier import sync_wait_for_input
        response = sync_wait_for_input(
            "Отправьте OK или введите 'Название | Тип':",
            timeout=300
        )
        
        if not response:
            logger.warning(f"⏱️ Таймаут ожидания - используем тип по умолчанию для: {name}")
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
• Цена: {price} ₽

✅ <b>Предлагаемые варианты:</b>
"""
    
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
    message += "\n⏳ Ожидаю ваш ответ..."
    
    sync_send_message(message)
    
    from notifier import sync_wait_for_input
    response = sync_wait_for_input(
        "Выберите номер (1-5) или введите 'Название | Тип':",
        timeout=300
    )
    
    if not response:
        # Таймаут - используем лучшее совпадение
        logger.warning(f"⏱️ Таймаут - используем лучшее совпадение для: {name}")
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


def enrich_orders_with_mapping(orders_data: list, matcher: ProductMatcher, interactive: bool = True) -> list:
    """
    Обогатить данные заказов сопоставлениями из каталога.
    
    Args:
        orders_data: Список заказов с товарами
        matcher: Объект ProductMatcher
        interactive: Если True, использовать интерактивный режим через Telegram
        
    Returns:
        Обогащённый список заказов
    """
    logger.info("🔄 Начинаем сопоставление товаров с каталогом...")
    
    # Сначала извлекаем уникальные товары
    unique_items_dict = {}
    for order in orders_data:
        for item in order.get('items', []):
            key = f"{item['name']}|{item.get('color', '')}"
            if key not in unique_items_dict:
                unique_items_dict[key] = item
    
    unique_items = list(unique_items_dict.values())
    logger.info(f"📦 Уникальных товаров для сопоставления: {len(unique_items)}")
    
    # Создаём кеш сопоставлений
    mapping_cache = {}
    
    # Сопоставляем каждый уникальный товар
    for idx, item in enumerate(unique_items, 1):
        logger.info(f"[{idx}/{len(unique_items)}] Обрабатываем: {item['name']}")
        
        # Используем интерактивный или автоматический режим
        mapped_name, mapped_type = match_product_interactive(
            item, 
            matcher, 
            auto_mode=not interactive
        )
        
        key = f"{item['name']}|{item.get('color', '')}"
        mapping_cache[key] = {
            'mapped_name': mapped_name,
            'mapped_type': mapped_type
        }
        
        logger.info(f"✅ [{idx}/{len(unique_items)}] {item['name']} → {mapped_name} ({mapped_type})")
    
    # Применяем сопоставления ко всем товарам
    enriched_orders = []
    total_items = 0
    matched_items = 0
    
    for order in orders_data:
        enriched_order = order.copy()
        enriched_items = []
        
        for item in order.get('items', []):
            total_items += 1
            
            key = f"{item['name']}|{item.get('color', '')}"
            
            # Добавляем новые поля из кеша
            enriched_item = item.copy()
            if key in mapping_cache:
                enriched_item['mapped_name'] = mapping_cache[key]['mapped_name']
                enriched_item['mapped_type'] = mapping_cache[key]['mapped_type']
                matched_items += 1
            else:
                # На всякий случай, если что-то пропустили
                enriched_item['mapped_name'] = item['name']
                enriched_item['mapped_type'] = matcher.DEFAULT_TYPE
            
            enriched_items.append(enriched_item)
        
        enriched_order['items'] = enriched_items
        enriched_orders.append(enriched_order)
    
    logger.info(f"✅ Сопоставлено товаров: {matched_items}/{total_items}")
    
    return enriched_orders
