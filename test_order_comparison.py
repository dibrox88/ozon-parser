"""
Тест для проверки методов get_order_data и compare_orders.
"""

from loguru import logger
from sheets_sync import SheetsSynchronizer
import json

def main():
    logger.info("=" * 80)
    logger.info("🧪 ТЕСТ: Получение и сравнение данных заказа")
    logger.info("=" * 80)
    
    # Инициализируем синхронизатор
    from config import Config
    sync = SheetsSynchronizer(credentials_file=Config.GOOGLE_CREDENTIALS_FILE)
    
    # Подключаемся к Google Sheets
    if not sync.connect():
        logger.error("❌ Не удалось подключиться к Google Sheets")
        return
    
    # Открываем лист
    if not sync.open_sync_worksheet(Config.GOOGLE_SHEETS_URL, Config.GOOGLE_SHEETS_SYNC_GID):
        logger.error("❌ Не удалось открыть лист")
        return
    
    # Читаем JSON с заказами
    with open('ozon_orders.json', encoding='utf-8') as f:
        data = json.load(f)
    
    # Берём первый заказ для теста
    test_order = data['orders'][0]
    order_number = test_order['order_number']
    
    logger.info(f"\n📦 Тестовый заказ: {order_number}")
    logger.info(f"   Товаров в JSON: {len(test_order['items'])}")
    
    # Получаем данные из Sheets
    logger.info(f"\n🔍 Получение данных из Google Sheets...")
    sheets_data = sync.get_order_data(order_number)
    
    if not sheets_data:
        logger.warning(f"⚠️ Заказ {order_number} не найден в таблице")
        logger.info("\nВозможно, это новый заказ. Попробуйте другой номер заказа.")
        return
    
    logger.info(f"   Найдено строк в Sheets: {sheets_data.get('total_rows', 0)}")
    logger.info(f"   Диапазон строк: {sheets_data.get('start_row')}-{sheets_data.get('end_row')}")
    
    # Показываем первые 3 строки
    logger.info(f"\n   Первые 3 строки:")
    for row in sheets_data.get('rows', [])[:3]:
        logger.info(f"     • {row['mapped_name']} | status={row['status']} | price={row['price']}")
    
    # Сравниваем
    logger.info(f"\n🔄 Сравнение данных...")
    comparison = sync.compare_orders(test_order, sheets_data)
    
    if comparison['has_changes']:
        logger.warning(f"⚠️ Обнаружены изменения ({len(comparison['changes'])} изменений):")
        for change in comparison['changes']:
            logger.warning(f"     {change}")
        
        # Детальная информация
        details = comparison['details']
        if 'added' in details:
            logger.info(f"\n   ➕ Добавлено товаров: {len(details['added'])}")
        if 'removed' in details:
            logger.info(f"\n   ➖ Удалено товаров: {len(details['removed'])}")
        if 'modified' in details:
            logger.info(f"\n   🔄 Изменено товаров: {len(details['modified'])}")
    else:
        logger.info(f"✅ Изменений не обнаружено - данные совпадают")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ТЕСТ ЗАВЕРШЁН")
    logger.info("=" * 80)

if __name__ == '__main__':
    main()
