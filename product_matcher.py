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
        auto_mode: Если True, не спрашивать подтверждение (для тестов)
        
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
    
    if not matches:
        logger.warning(f"⚠️ Не найдено совпадений для: {name}")
        
        # Отправляем в Telegram для ручного ввода
        message = f"""
🔍 <b>Товар не найден в каталоге</b>

📦 <b>Товар из заказа:</b>
• Название: {name}
• Цвет: {color or 'не указан'}
• Количество: {quantity}
• Цена: {price} ₽

❓ <b>Предлагаем тип по умолчанию:</b> <code>{matcher.DEFAULT_TYPE}</code>

💡 Для сопоставления ответьте в формате:
<code>Название товара | Тип</code>

Или отправьте <code>OK</code> для использования типа "{matcher.DEFAULT_TYPE}"
        """
        
        sync_send_message(message)
        
        if auto_mode:
            # В авто-режиме используем тип по умолчанию
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        else:
            # TODO: Здесь должна быть логика ожидания ответа от пользователя
            # Пока используем тип по умолчанию
            logger.warning(f"⚠️ Используем тип по умолчанию: {matcher.DEFAULT_TYPE}")
            mapped_name = name
            mapped_type = matcher.DEFAULT_TYPE
        
        # Сохраняем сопоставление
        matcher.save_mapping(name, color, mapped_name, mapped_type)
        return mapped_name, mapped_type
    
    # Нашли совпадения - показываем пользователю
    best_match = matches[0]
    
    message = f"""
🔍 <b>Найдено совпадение товара</b>

📦 <b>Товар из заказа:</b>
• Название: {name}
• Цвет: {color or 'не указан'}
• Количество: {quantity}
• Цена: {price} ₽

✅ <b>Предлагаем сопоставление:</b>
• Название: <b>{best_match['name']}</b>
• Тип: <b>{best_match['type']}</b>
• Совпадение: {best_match['match_score']}%
"""
    
    if len(matches) > 1:
        message += f"\n📋 <b>Другие варианты:</b>\n"
        for idx, match in enumerate(matches[1:4], start=2):
            message += f"{idx}. {match['name']} ({match['type']}) - {match['match_score']}%\n"
    
    message += "\n💡 Отправьте <code>OK</code> для подтверждения или <code>Название | Тип</code> для изменения"
    
    sync_send_message(message)
    
    if auto_mode:
        # В авто-режиме принимаем лучшее совпадение
        mapped_name = best_match['name']
        mapped_type = best_match['type']
    else:
        # TODO: Логика ожидания ответа
        logger.info(f"✅ Принято автоматически: {best_match['name']} ({best_match['type']})")
        mapped_name = best_match['name']
        mapped_type = best_match['type']
    
    # Сохраняем сопоставление
    matcher.save_mapping(name, color, mapped_name, mapped_type)
    
    return mapped_name, mapped_type


def enrich_orders_with_mapping(orders_data: list, matcher: ProductMatcher) -> list:
    """
    Обогатить данные заказов сопоставлениями из каталога.
    
    Args:
        orders_data: Список заказов с товарами
        matcher: Объект ProductMatcher
        
    Returns:
        Обогащённый список заказов
    """
    logger.info("🔄 Начинаем сопоставление товаров с каталогом...")
    
    enriched_orders = []
    total_items = 0
    matched_items = 0
    
    for order in orders_data:
        enriched_order = order.copy()
        enriched_items = []
        
        for item in order.get('items', []):
            total_items += 1
            
            # Сопоставляем товар
            mapped_name, mapped_type = match_product_interactive(item, matcher, auto_mode=True)
            
            # Добавляем новые поля
            enriched_item = item.copy()
            enriched_item['mapped_name'] = mapped_name
            enriched_item['mapped_type'] = mapped_type
            
            enriched_items.append(enriched_item)
            matched_items += 1
            
            logger.debug(f"✅ {item['name']} → {mapped_name} ({mapped_type})")
        
        enriched_order['items'] = enriched_items
        enriched_orders.append(enriched_order)
    
    logger.info(f"✅ Сопоставлено товаров: {matched_items}/{total_items}")
    
    return enriched_orders
