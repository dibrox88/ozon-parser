"""
Скрипт для локального тестирования сопоставления товаров из JSON.
Использование: python test_order_matching.py <номер_заказа>

Пример: python test_order_matching.py 46206571-0672
"""

import sys
import json
from pathlib import Path
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

from product_matcher import ProductMatcher, match_product_interactive
from sheets_manager import SheetsManager
from config import Config
from notifier import sync_send_message


def load_order_from_json(order_number: str) -> dict:
    """Загрузить конкретный заказ из ozon_orders.json"""
    try:
        with open('ozon_orders.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        orders = data.get('orders', [])
        for order in orders:
            if order.get('order_number') == order_number:
                return order
        
        logger.error(f"Заказ {order_number} не найден в ozon_orders.json")
        return None
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        return None


def display_order_info(order: dict):
    """Отобразить информацию о заказе"""
    logger.info("=" * 80)
    logger.info("📦 ИНФОРМАЦИЯ О ЗАКАЗЕ")
    logger.info("=" * 80)
    logger.info(f"Номер заказа: {order.get('order_number')}")
    logger.info(f"Дата: {order.get('date')}")
    logger.info(f"Общая сумма: {order.get('total_amount')} ₽")
    logger.info(f"Количество позиций: {len(order.get('items', []))}")
    logger.info(f"Всего товаров: {order.get('items_count', 0)}")
    logger.info("")
    
    logger.info("📋 ТОВАРЫ:")
    for i, item in enumerate(order.get('items', []), 1):
        logger.info(f"\n  {i}. {item.get('name', 'N/A')}")
        logger.info(f"     Количество: {item.get('quantity', 1)}")
        logger.info(f"     Цена: {item.get('price', 0)} ₽")
        logger.info(f"     Цвет: {item.get('color', 'N/A')}")
        logger.info(f"     Статус: {item.get('status', 'N/A')}")
        
        if item.get('mapped_name'):
            logger.info(f"     ✅ Mapped: {item.get('mapped_name')} ({item.get('mapped_type')})")
        else:
            logger.info(f"     ⚠️  Not mapped yet")
    
    logger.info("\n" + "=" * 80)


def test_order_matching(order: dict):
    """Протестировать сопоставление товаров в заказе"""
    try:
        logger.info("🔄 Инициализация системы...")
        
        # Загружаем конфигурацию
        config = Config()
        
        # Подключаемся к Google Sheets и загружаем каталог
        logger.info("📊 Подключение к Google Sheets...")
        sheets = SheetsManager(config.GOOGLE_CREDENTIALS_FILE)
        catalog_products = sheets.load_catalog()
        
        if not catalog_products:
            logger.error("❌ Каталог товаров пуст")
            return
        
        logger.info(f"✅ Загружено {len(catalog_products)} товаров из каталога")
        
        # Создаём matcher
        matcher = ProductMatcher(catalog_products)
        
        # Отправляем уведомление в Telegram
        sync_send_message(
            f"🧪 <b>Тест сопоставления заказа</b>\n\n"
            f"Заказ: {order.get('order_number')}\n"
            f"Товаров: {order.get('items_count', 0)}"
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("🔍 НАЧИНАЕМ СОПОСТАВЛЕНИЕ ТОВАРОВ")
        logger.info("=" * 80 + "\n")
        
        # Проходим по каждому товару
        enriched_items = []
        for i, item in enumerate(order.get('items', []), 1):
            logger.info(f"\n{'─' * 80}")
            logger.info(f"Товар {i}/{len(order['items'])}: {item.get('name', 'N/A')[:60]}...")
            logger.info(f"{'─' * 80}")
            
            # Если уже есть mapping - показываем
            if item.get('mapped_name'):
                logger.warning(f"⚠️  Товар уже сопоставлен: {item.get('mapped_name')} ({item.get('mapped_type')})")
                
                sync_send_message(
                    f"⚠️ Товар уже сопоставлен:\n"
                    f"<b>{item.get('name', 'N/A')[:80]}</b>\n\n"
                    f"Текущее сопоставление:\n"
                    f"• {item.get('mapped_name')}\n"
                    f"• {item.get('mapped_type')}\n\n"
                    f"Отправьте <b>Y</b> для пересопоставления или <b>N</b> для пропуска"
                )
                
                # Ждём ответа от пользователя
                from notifier import sync_wait_for_input
                user_input = sync_wait_for_input(timeout=300)
                
                if user_input and user_input.upper() == 'Y':
                    logger.info("✅ Пересопоставляем...")
                else:
                    logger.info("⏭️  Пропускаем...")
                    enriched_items.append(item)
                    continue
            
            # Интерактивное сопоставление через Telegram
            enriched = match_product_interactive(
                item, 
                matcher,
                auto_mode=False,
                order_number=order.get('order_number')
            )
            
            if enriched:
                enriched_items.append(enriched)
                logger.info(f"✅ Сопоставлено: {enriched.get('mapped_name', 'N/A')}")
            else:
                logger.warning("⚠️  Сопоставление не выполнено")
                enriched_items.append(item)
        
        # Сохраняем результаты
        logger.info("\n" + "=" * 80)
        logger.info("💾 СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
        logger.info("=" * 80)
        
        # Обновляем заказ с новыми данными
        updated_order = order.copy()
        updated_order['items'] = enriched_items
        
        # Сохраняем в отдельный файл для проверки
        output_file = f"test_order_{order.get('order_number')}_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(updated_order, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Результаты сохранены в: {output_file}")
        
        # Выводим итоговую статистику
        logger.info("\n" + "=" * 80)
        logger.info("📊 СТАТИСТИКА")
        logger.info("=" * 80)
        
        mapped_count = sum(1 for item in enriched_items if item.get('mapped_name'))
        logger.info(f"Всего товаров: {len(enriched_items)}")
        logger.info(f"Сопоставлено: {mapped_count}")
        logger.info(f"Не сопоставлено: {len(enriched_items) - mapped_count}")
        
        sync_send_message(
            f"✅ <b>Тест завершён!</b>\n\n"
            f"Сопоставлено: {mapped_count}/{len(enriched_items)}\n"
            f"Результаты: {output_file}"
        )
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"❌ Ошибка: {e}")


def main():
    """Главная функция"""
    # Получаем номер заказа из аргументов или используем дефолтный
    if len(sys.argv) > 1:
        order_number = sys.argv[1]
    else:
        order_number = "46206571-0672"  # Дефолтный заказ
        logger.info(f"ℹ️  Используется заказ по умолчанию: {order_number}")
    
    logger.info(f"🔍 Поиск заказа: {order_number}")
    
    # Загружаем заказ
    order = load_order_from_json(order_number)
    
    if not order:
        logger.error(f"❌ Заказ {order_number} не найден в ozon_orders.json")
        sys.exit(1)
    
    # Отображаем информацию
    display_order_info(order)
    
    logger.info("\n🚀 Начинаем тестирование через 2 секунды...")
    logger.info("   (Нажмите Ctrl+C для отмены)\n")
    
    import time
    time.sleep(2)
    
    # Запускаем тестирование
    test_order_matching(order)


if __name__ == "__main__":
    main()
