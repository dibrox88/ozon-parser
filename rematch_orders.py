"""
Скрипт для пересопоставления товаров в существующем JSON файле.
Использует обновлённую логику с интерактивным подтверждением через Telegram.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Настройка логирования
Path('logs').mkdir(exist_ok=True)
logger.add(
    "logs/rematch_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

from config import Config
from sheets_manager import SheetsManager
from product_matcher import ProductMatcher, match_product_interactive
from notifier import sync_send_message


def load_orders_json(filename: str) -> dict:
    """Загрузить заказы из JSON файла."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"✅ Загружен JSON: {filename}")
        return data
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки JSON: {e}")
        return {}


def save_orders_json(data: dict, filename: str) -> bool:
    """Сохранить обновлённые заказы в JSON файл."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Сохранён обновлённый JSON: {filename}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения JSON: {e}")
        return False


def extract_unique_items(orders_data: dict) -> list:
    """Извлечь уникальные товары из заказов."""
    unique_items = {}
    
    for order in orders_data.get('orders', []):
        for item in order.get('items', []):
            # Создаём ключ: название + цвет
            key = f"{item['name']}|{item.get('color', '')}"
            
            if key not in unique_items:
                unique_items[key] = {
                    'name': item['name'],
                    'color': item.get('color', ''),
                    'quantity': item.get('quantity', 1),
                    'price': item.get('price', 0)
                }
    
    logger.info(f"📋 Извлечено уникальных товаров: {len(unique_items)}")
    return list(unique_items.values())


def rematch_orders(orders_data: dict, matcher: ProductMatcher) -> dict:
    """
    Пересопоставить все товары в заказах с новой логикой.
    
    Args:
        orders_data: Данные заказов из JSON
        matcher: Объект ProductMatcher
        
    Returns:
        Обновлённые данные заказов
    """
    logger.info("🔄 Начинаем пересопоставление товаров...")
    sync_send_message("🔄 <b>Начинаем пересопоставление товаров</b>\n\nИспользуется интерактивный режим через Telegram.")
    
    # Извлекаем уникальные товары
    unique_items = extract_unique_items(orders_data)
    
    # Создаём карту сопоставлений для быстрого доступа
    mapping_cache = {}
    
    logger.info(f"📦 Будет обработано уникальных товаров: {len(unique_items)}")
    sync_send_message(f"📦 <b>Уникальных товаров:</b> {len(unique_items)}\n\nНачинаем сопоставление...")
    
    # Сопоставляем каждый уникальный товар
    for idx, item in enumerate(unique_items, 1):
        logger.info(f"\n[{idx}/{len(unique_items)}] Обрабатываем: {item['name']}")
        sync_send_message(f"🔄 [{idx}/{len(unique_items)}] {item['name'][:50]}...")
        
        # Интерактивное сопоставление (auto_mode=False для запроса у пользователя)
        mapped_name, mapped_type = match_product_interactive(item, matcher, auto_mode=False)
        
        # Сохраняем в кеш
        key = f"{item['name']}|{item.get('color', '')}"
        mapping_cache[key] = {
            'mapped_name': mapped_name,
            'mapped_type': mapped_type
        }
        
        logger.info(f"✅ [{idx}/{len(unique_items)}] {item['name']} → {mapped_name} ({mapped_type})")
    
    # Применяем сопоставления ко всем товарам в заказах
    logger.info("\n📝 Применяем сопоставления ко всем товарам...")
    updated_orders_data = orders_data.copy()
    
    for order in updated_orders_data.get('orders', []):
        for item in order.get('items', []):
            key = f"{item['name']}|{item.get('color', '')}"
            
            if key in mapping_cache:
                item['mapped_name'] = mapping_cache[key]['mapped_name']
                item['mapped_type'] = mapping_cache[key]['mapped_type']
    
    logger.info("✅ Пересопоставление завершено!")
    sync_send_message("✅ <b>Пересопоставление завершено!</b>\n\nВсе товары обновлены.")
    
    return updated_orders_data


def main():
    """Главная функция."""
    try:
        logger.info("=" * 60)
        logger.info("Запуск скрипта пересопоставления товаров")
        logger.info("=" * 60)
        
        sync_send_message("🚀 <b>Запуск пересопоставления товаров</b>\n\nБудет использован файл:\nozon_orders_2025-10-06_00-49-56.json")
        
        # Путь к существующему JSON (используем последний доступный)
        json_file = "ozon_orders_2025-10-06_00-49-56.json"
        
        if not Path(json_file).exists():
            logger.error(f"❌ Файл не найден: {json_file}")
            sync_send_message(f"❌ Файл не найден: {json_file}")
            return
        
        # Загружаем заказы
        orders_data = load_orders_json(json_file)
        if not orders_data:
            logger.error("❌ Не удалось загрузить данные заказов")
            return
        
        logger.info(f"📊 Загружено заказов: {orders_data.get('total_orders', 0)}")
        logger.info(f"📦 Всего товаров: {orders_data.get('statistics', {}).get('total_items', 0)}")
        
        # Подключаемся к Google Sheets
        logger.info("🔄 Подключение к Google Sheets...")
        sync_send_message("🔄 Подключение к Google Sheets...")
        
        sheets = SheetsManager(Config.GOOGLE_CREDENTIALS_FILE)
        if not sheets.connect():
            logger.error("❌ Не удалось подключиться к Google Sheets")
            sync_send_message("❌ Ошибка подключения к Google Sheets")
            return
        
        # Загружаем каталог товаров (теперь с 4 столбцами)
        catalog_products = sheets.load_products_from_sheet(
            Config.GOOGLE_SHEETS_URL,
            columns_range="A:AU"
        )
        
        if not catalog_products:
            logger.error("❌ Не удалось загрузить каталог товаров")
            sync_send_message("❌ Каталог товаров пуст")
            return
        
        logger.info(f"✅ Загружено товаров из каталога: {len(catalog_products)}")
        sync_send_message(f"✅ Загружено товаров из каталога: {len(catalog_products)}")
        
        # Создаём matcher с основным файлом маппинга
        matcher = ProductMatcher(
            catalog_products,
            mappings_file="product_mappings.json"
        )
        
        # Пересопоставляем товары
        updated_orders = rematch_orders(orders_data, matcher)
        
        # Сохраняем обновлённый JSON
        output_file = f"ozon_orders_rematched_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        if save_orders_json(updated_orders, output_file):
            logger.info(f"✅ Обновлённые данные сохранены: {output_file}")
            sync_send_message(f"✅ <b>Готово!</b>\n\nОбновлённые данные сохранены в:\n{output_file}")
        
        logger.info("=" * 60)
        logger.info("Работа завершена успешно")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("⚠️ Прервано пользователем")
        sync_send_message("⚠️ Работа прервана пользователем")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
        sync_send_message(f"❌ <b>Критическая ошибка</b>\n\n{str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
