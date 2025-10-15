"""
Тест разбивки товаров на компоненты (bundle splitting).
"""

import json
from pathlib import Path
from bundle_manager import BundleManager, create_bundle_item
from loguru import logger

def test_bundle_creation():
    """Тест создания связки."""
    logger.info("=== Тест 1: Создание связки ===")
    
    # Создаём временный файл для тестов
    test_file = "test_bundles.json"
    bm = BundleManager(bundles_file=test_file)
    
    # Тестовые компоненты
    components = [
        {"mapped_name": "Товар А", "mapped_type": "Тип 1", "price": 5000},
        {"mapped_name": "Товар Б", "mapped_type": "Тип 2", "price": 7000},
        {"mapped_name": "Товар В", "mapped_type": "Тип 3", "price": 3000}
    ]
    
    total_price = 15000
    product_name = "Комплект XYZ"
    
    # Создаём связку
    result = bm.create_bundle(product_name, components, total_price)
    
    assert result == True, "Связка должна быть создана"
    assert bm.has_bundle(product_name), "Связка должна существовать"
    
    # Проверяем что файл создан
    assert Path(test_file).exists(), "Файл связок должен существовать"
    
    logger.success("✅ Тест 1 пройден: связка создана")
    
    # Очистка
    Path(test_file).unlink()


def test_bundle_retrieval():
    """Тест получения связки."""
    logger.info("=== Тест 2: Получение связки ===")
    
    test_file = "test_bundles.json"
    bm = BundleManager(bundles_file=test_file)
    
    components = [
        {"mapped_name": "Компонент 1", "mapped_type": "Тип X", "price": 8000},
        {"mapped_name": "Компонент 2", "mapped_type": "Тип Y", "price": 2000}
    ]
    
    product_name = "Набор ABC"
    bm.create_bundle(product_name, components, 10000)
    
    # Получаем связку
    bundle = bm.get_bundle(product_name)
    
    assert bundle is not None, "Связка должна быть найдена"
    assert bundle['original_name'] == product_name
    assert len(bundle['components']) == 2
    assert bundle['total_price'] == 10000
    assert bundle['components_count'] == 2
    
    logger.success("✅ Тест 2 пройден: связка получена")
    
    # Очистка
    Path(test_file).unlink()


def test_bundle_validation():
    """Тест валидации суммы цен."""
    logger.info("=== Тест 3: Валидация суммы ===")
    
    test_file = "test_bundles.json"
    bm = BundleManager(bundles_file=test_file)
    
    # Неправильная сумма
    components = [
        {"mapped_name": "Товар 1", "mapped_type": "Тип A", "price": 5000},
        {"mapped_name": "Товар 2", "mapped_type": "Тип B", "price": 6000}
    ]
    
    product_name = "Ошибочный набор"
    result = bm.create_bundle(product_name, components, 20000)  # Сумма не совпадает!
    
    assert result == False, "Связка с неправильной суммой не должна быть создана"
    assert not bm.has_bundle(product_name), "Связка не должна существовать"
    
    logger.success("✅ Тест 3 пройден: валидация работает")
    
    # Очистка (если файл был создан)
    if Path(test_file).exists():
        Path(test_file).unlink()


def test_create_bundle_item():
    """Тест создания bundle item."""
    logger.info("=== Тест 4: Создание bundle item ===")
    
    original_item = {
        "name": "Набор инструментов",
        "price": 12000,
        "quantity": 2,
        "status": "получен"
    }
    
    components = [
        {"mapped_name": "Молоток", "mapped_type": "Инструменты", "price": 3000},
        {"mapped_name": "Отвёртка", "mapped_type": "Инструменты", "price": 2000},
        {"mapped_name": "Плоскогубцы", "mapped_type": "Инструменты", "price": 7000}
    ]
    
    bundle_item = create_bundle_item(original_item, components)
    
    assert bundle_item['is_bundle'] == True
    assert bundle_item['bundle_key'] == "Набор инструментов"
    assert len(bundle_item['components']) == 3
    assert bundle_item['components'][0]['status'] == 'получен'
    assert bundle_item['price'] == 12000
    assert bundle_item['quantity'] == 2
    
    logger.success("✅ Тест 4 пройден: bundle item создан")


def test_bundle_stats():
    """Тест статистики."""
    logger.info("=== Тест 5: Статистика ===")
    
    test_file = "test_bundles.json"
    bm = BundleManager(bundles_file=test_file)
    
    # Создаём несколько связок
    bm.create_bundle("Набор 1", [
        {"mapped_name": "A", "mapped_type": "T1", "price": 5000},
        {"mapped_name": "B", "mapped_type": "T2", "price": 5000}
    ], 10000)
    
    bm.create_bundle("Набор 2", [
        {"mapped_name": "C", "mapped_type": "T3", "price": 3000},
        {"mapped_name": "D", "mapped_type": "T4", "price": 4000},
        {"mapped_name": "E", "mapped_type": "T5", "price": 3000}
    ], 10000)
    
    stats = bm.get_stats()
    
    assert stats['total_bundles'] == 2
    assert stats['total_components'] == 5
    assert stats['avg_components'] == 2.5
    
    logger.success("✅ Тест 5 пройден: статистика корректна")
    
    # Очистка
    Path(test_file).unlink()


def test_schema_parsing():
    """Тест парсинга схемы."""
    logger.info("=== Тест 6: Парсинг схемы ===")
    
    # Тестируем разные форматы схемы
    test_cases = [
        ("2-3-5", [2, 3, 5]),
        ("1", [1]),
        ("10-20-30-40", [10, 20, 30, 40]),
        ("2-2-2", [2, 2, 2])
    ]
    
    for schema, expected in test_cases:
        parts = schema.split('-')
        type_numbers = [int(p) for p in parts]
        assert type_numbers == expected, f"Схема {schema} должна парситься в {expected}"
    
    logger.success("✅ Тест 6 пройден: парсинг схемы работает")


def run_all_tests():
    """Запустить все тесты."""
    logger.info("🚀 Запуск тестов bundle splitting...")
    
    try:
        test_bundle_creation()
        test_bundle_retrieval()
        test_bundle_validation()
        test_create_bundle_item()
        test_bundle_stats()
        test_schema_parsing()
        
        logger.success("=" * 50)
        logger.success("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        logger.success("=" * 50)
        
    except AssertionError as e:
        logger.error(f"❌ Тест провален: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка в тестах: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
