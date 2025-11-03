"""
Тест синхронизации статусов для разбитых товаров.
Проверяет, что все единицы разбитого товара получают одинаковый статус.
"""

import json
from typing import Dict, List
from sheets_sync import SheetsSynchronizer


def create_test_order_with_split_items() -> Dict:
    """
    Создать тестовый заказ с разбитыми товарами с разными статусами.
    """
    return {
        "order_number": "TEST-12345",
        "date": "2025-11-03",
        "items": [
            # Разбитый товар - 3 единицы с РАЗНЫМИ статусами
            {
                "name": "Тестовый товар #1",
                "mapped_name": "Тестовый товар #1",
                "mapped_type": "Расходники",
                "quantity": 1,
                "price": 100,
                "status": "забрать",  # Статус 1
                "is_split": True,
                "split_index": 1,
                "split_total": 3,
                "order_number": "TEST-12345"
            },
            {
                "name": "Тестовый товар #1",
                "mapped_name": "Тестовый товар #1",
                "mapped_type": "Расходники",
                "quantity": 1,
                "price": 100,
                "status": "получен",  # Статус 2 (приоритетный!)
                "is_split": True,
                "split_index": 2,
                "split_total": 3,
                "order_number": "TEST-12345"
            },
            {
                "name": "Тестовый товар #1",
                "mapped_name": "Тестовый товар #1",
                "mapped_type": "Расходники",
                "quantity": 1,
                "price": 100,
                "status": "в пункте выдачи",  # Статус 3
                "is_split": True,
                "split_index": 3,
                "split_total": 3,
                "order_number": "TEST-12345"
            },
            # Обычный товар (не разбитый) для сравнения
            {
                "name": "Обычный товар",
                "mapped_name": "Обычный товар",
                "mapped_type": "Комплектующие",
                "quantity": 1,
                "price": 500,
                "status": "забрать",
                "order_number": "TEST-12345"
            }
        ]
    }


def test_sync_split_items_status():
    """
    Тестировать синхронизацию статусов разбитых товаров.
    """
    print("=" * 80)
    print("🧪 ТЕСТ: Синхронизация статусов разбитых товаров")
    print("=" * 80)
    
    # Создаем тестовый заказ
    test_order = create_test_order_with_split_items()
    
    print("\n📦 ИСХОДНЫЕ ДАННЫЕ:")
    print("-" * 80)
    for i, item in enumerate(test_order['items'], 1):
        is_split = item.get('is_split', False)
        split_info = ""
        if is_split:
            split_info = f" [Разбит: {item['split_index']}/{item['split_total']}]"
        
        print(f"{i}. {item['mapped_name']}{split_info}")
        print(f"   Статус: {item['status']}")
        print(f"   Цена: {item['price']}₽")
        print()
    
    # Создаем экземпляр синхронизатора (передаем dummy файл, т.к. не будем подключаться к Sheets)
    synchronizer = SheetsSynchronizer("google_credentials.json")
    
    print("\n🔄 ПРИМЕНЯЕМ СИНХРОНИЗАЦИЮ СТАТУСОВ...")
    print("-" * 80)
    
    # Вызываем метод синхронизации
    synchronizer.sync_split_items_status(test_order)
    
    print("\n✅ РЕЗУЛЬТАТ ПОСЛЕ СИНХРОНИЗАЦИИ:")
    print("-" * 80)
    
    # Проверяем результаты
    split_items = [item for item in test_order['items'] if item.get('is_split')]
    non_split_items = [item for item in test_order['items'] if not item.get('is_split')]
    
    if split_items:
        print("\n🔸 Разбитые товары:")
        statuses = set()
        for item in split_items:
            statuses.add(item['status'])
            print(f"   • {item['mapped_name']} [{item['split_index']}/{item['split_total']}]: {item['status']}")
        
        if len(statuses) == 1:
            print(f"\n   ✅ ВСЕ СТАТУСЫ СИНХРОНИЗИРОВАНЫ: '{list(statuses)[0]}'")
        else:
            print(f"\n   ❌ ОШИБКА: Найдено {len(statuses)} разных статусов: {statuses}")
    
    if non_split_items:
        print("\n🔸 Обычные товары (не затронуты):")
        for item in non_split_items:
            print(f"   • {item['mapped_name']}: {item['status']}")
    
    print("\n" + "=" * 80)
    print("🏁 ТЕСТ ЗАВЕРШЁН")
    print("=" * 80)
    
    return test_order


def test_priority_status():
    """
    Тестировать приоритеты статусов.
    """
    print("\n" + "=" * 80)
    print("🧪 ТЕСТ: Приоритеты статусов")
    print("=" * 80)
    
    synchronizer = SheetsSynchronizer("google_credentials.json")
    
    test_cases = [
        (['забрать', 'получен', 'в пункте выдачи'], 'получен'),
        (['отменён', 'забрать'], 'отменён'),
        (['в пункте выдачи', 'забрать'], 'в пункте выдачи'),
        (['получен'], 'получен'),
    ]
    
    print("\nПроверка приоритетов:")
    print("-" * 80)
    
    all_passed = True
    for statuses, expected in test_cases:
        result = synchronizer._get_priority_status(statuses)
        status_icon = "✅" if result == expected else "❌"
        print(f"{status_icon} {statuses} → '{result}' (ожидалось: '{expected}')")
        if result != expected:
            all_passed = False
    
    if all_passed:
        print("\n✅ ВСЕ ТЕСТЫ ПРИОРИТЕТОВ ПРОЙДЕНЫ")
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРИОРИТЕТОВ НЕ ПРОШЛИ")
    
    print("=" * 80)


def test_multiple_split_groups():
    """
    Тестировать несколько групп разбитых товаров в одном заказе.
    """
    print("\n" + "=" * 80)
    print("🧪 ТЕСТ: Несколько групп разбитых товаров")
    print("=" * 80)
    
    test_order = {
        "order_number": "TEST-67890",
        "date": "2025-11-03",
        "items": [
            # Группа 1: Товар A - 2 единицы
            {
                "name": "Товар A",
                "mapped_name": "Товар A",
                "mapped_type": "Расходники",
                "quantity": 1,
                "price": 50,
                "status": "забрать",
                "is_split": True,
                "split_index": 1,
                "split_total": 2,
                "order_number": "TEST-67890"
            },
            {
                "name": "Товар A",
                "mapped_name": "Товар A",
                "mapped_type": "Расходники",
                "quantity": 1,
                "price": 50,
                "status": "получен",
                "is_split": True,
                "split_index": 2,
                "split_total": 2,
                "order_number": "TEST-67890"
            },
            # Группа 2: Товар B - 3 единицы
            {
                "name": "Товар B",
                "mapped_name": "Товар B",
                "mapped_type": "Комплектующие",
                "quantity": 1,
                "price": 100,
                "status": "в пункте выдачи",
                "is_split": True,
                "split_index": 1,
                "split_total": 3,
                "order_number": "TEST-67890"
            },
            {
                "name": "Товар B",
                "mapped_name": "Товар B",
                "mapped_type": "Комплектующие",
                "quantity": 1,
                "price": 100,
                "status": "забрать",
                "is_split": True,
                "split_index": 2,
                "split_total": 3,
                "order_number": "TEST-67890"
            },
            {
                "name": "Товар B",
                "mapped_name": "Товар B",
                "mapped_type": "Комплектующие",
                "quantity": 1,
                "price": 100,
                "status": "отменён",
                "is_split": True,
                "split_index": 3,
                "split_total": 3,
                "order_number": "TEST-67890"
            }
        ]
    }
    
    synchronizer = SheetsSynchronizer("google_credentials.json")
    
    print("\n📦 ДО СИНХРОНИЗАЦИИ:")
    print("-" * 80)
    print("Группа 1 (Товар A - 2 единицы):")
    for item in test_order['items'][:2]:
        print(f"   • Единица {item['split_index']}: {item['status']}")
    
    print("\nГруппа 2 (Товар B - 3 единицы):")
    for item in test_order['items'][2:]:
        print(f"   • Единица {item['split_index']}: {item['status']}")
    
    synchronizer.sync_split_items_status(test_order)
    
    print("\n✅ ПОСЛЕ СИНХРОНИЗАЦИИ:")
    print("-" * 80)
    
    # Проверяем Группу 1
    group1_statuses = set(item['status'] for item in test_order['items'][:2])
    print(f"Группа 1 (Товар A): {list(group1_statuses)}")
    if len(group1_statuses) == 1:
        print(f"   ✅ Синхронизировано: '{list(group1_statuses)[0]}'")
    else:
        print(f"   ❌ Не синхронизировано")
    
    # Проверяем Группу 2
    group2_statuses = set(item['status'] for item in test_order['items'][2:])
    print(f"\nГруппа 2 (Товар B): {list(group2_statuses)}")
    if len(group2_statuses) == 1:
        print(f"   ✅ Синхронизировано: '{list(group2_statuses)[0]}'")
    else:
        print(f"   ❌ Не синхронизировано")
    
    print("=" * 80)


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "ТЕСТИРОВАНИЕ СИНХРОНИЗАЦИИ СТАТУСОВ" + " " * 23 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Запускаем все тесты
    test_sync_split_items_status()
    test_priority_status()
    test_multiple_split_groups()
    
    print("\n✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ\n")
