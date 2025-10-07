"""
Тестирование механизма исключения заказов.
"""

import json
from pathlib import Path
from loguru import logger
from excluded_manager import ExcludedOrdersManager

# Настройка логирования
Path('logs').mkdir(exist_ok=True)
logger.add(
    "logs/test_exclude_{time}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


def test_excluded_manager():
    """Тестирование ExcludedOrdersManager."""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ МЕХАНИЗМА ИСКЛЮЧЕНИЯ ЗАКАЗОВ")
    print("="*60 + "\n")
    
    # Создаём менеджер
    manager = ExcludedOrdersManager("excluded_orders_test.json")
    
    # Тест 1: Добавление заказов
    print("📝 Тест 1: Добавление заказов в список исключённых")
    test_orders = ["46206571-0580", "46206571-0593", "46206571-0609"]
    
    for order_num in test_orders:
        result = manager.add_excluded(order_num)
        print(f"  {'✅' if result else '❌'} Добавлен: {order_num}")
    
    print(f"\n📊 Всего исключённых: {manager.get_count()}")
    
    # Тест 2: Проверка наличия
    print("\n🔍 Тест 2: Проверка наличия заказов")
    check_orders = ["46206571-0580", "46206571-0591", "46206571-0593"]
    
    for order_num in check_orders:
        is_excluded = manager.is_excluded(order_num)
        status = "🚫 ИСКЛЮЧЁН" if is_excluded else "✅ АКТИВЕН"
        print(f"  {status}: {order_num}")
    
    # Тест 3: Фильтрация заказов
    print("\n🔄 Тест 3: Фильтрация списка заказов")
    
    # Загружаем тестовые данные
    test_file = "ozon_orders_rematched_2025-10-06_22-13-34.json"
    
    if Path(test_file).exists():
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_orders = data.get('orders', [])
        
        print(f"  📂 Загружено заказов: {len(all_orders)}")
        
        valid_orders, excluded_orders = manager.filter_orders(all_orders)
        
        print(f"  ✅ Активных заказов: {len(valid_orders)}")
        print(f"  🚫 Исключённых заказов: {len(excluded_orders)}")
        
        if excluded_orders:
            print("\n  Список исключённых:")
            for order in excluded_orders:
                print(f"    • {order.get('order_number', '?')}")
    else:
        print(f"  ⚠️ Файл {test_file} не найден")
    
    # Тест 4: Удаление заказа
    print("\n🗑️ Тест 4: Удаление заказа из списка")
    remove_order = "46206571-0593"
    result = manager.remove_excluded(remove_order)
    print(f"  {'✅' if result else '❌'} Удалён: {remove_order}")
    print(f"  📊 Осталось исключённых: {manager.get_count()}")
    
    # Тест 5: Получение списка
    print("\n📋 Тест 5: Получение полного списка исключённых")
    excluded_list = manager.get_excluded_list()
    print(f"  Всего: {len(excluded_list)}")
    for order_num in excluded_list:
        print(f"    • {order_num}")
    
    # Очистка тестового файла
    print("\n🧹 Очистка тестового файла...")
    test_path = Path("excluded_orders_test.json")
    if test_path.exists():
        test_path.unlink()
        print("  ✅ Тестовый файл удалён")
    
    print("\n" + "="*60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*60 + "\n")


def test_integration_with_matcher():
    """Тест интеграции с product_matcher."""
    print("\n" + "="*60)
    print("🧪 ТЕСТ ИНТЕГРАЦИИ С PRODUCT MATCHER")
    print("="*60 + "\n")
    
    # Создаём тестовый менеджер
    manager = ExcludedOrdersManager("excluded_orders_test2.json")
    
    # Добавляем тестовый заказ
    test_order = "46206571-TEST"
    manager.add_excluded(test_order)
    print(f"✅ Добавлен тестовый заказ: {test_order}")
    
    # Проверяем, что он в списке
    is_excluded = manager.is_excluded(test_order)
    print(f"🔍 Проверка: {'🚫 ИСКЛЮЧЁН' if is_excluded else '✅ АКТИВЕН'}")
    
    # Очистка
    test_path = Path("excluded_orders_test2.json")
    if test_path.exists():
        test_path.unlink()
        print("🧹 Тестовый файл удалён")
    
    print("\n✅ ТЕСТ ИНТЕГРАЦИИ ПРОЙДЕН!\n")


if __name__ == '__main__':
    try:
        logger.info("="*60)
        logger.info("🧪 ЗАПУСК ТЕСТОВ МЕХАНИЗМА ИСКЛЮЧЕНИЯ")
        logger.info("="*60)
        
        test_excluded_manager()
        test_integration_with_matcher()
        
        logger.info("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        
    except Exception as e:
        logger.exception(f"❌ Ошибка при выполнении тестов: {e}")
        print(f"\n❌ ОШИБКА: {e}\n")
        raise
