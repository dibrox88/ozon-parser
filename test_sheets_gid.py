"""
Тестовый скрипт для проверки работы Google Sheets с gid.
"""
from sheets_manager import SheetsManager
from config import Config
from loguru import logger

# Настройка логирования
logger.add("test_sheets.log", level="DEBUG")

def test_sheets_connection():
    """Тестируем подключение и загрузку данных."""
    print("=" * 60)
    print("Тест подключения к Google Sheets")
    print("=" * 60)
    
    # Подключаемся
    sheets = SheetsManager(Config.GOOGLE_CREDENTIALS_FILE)
    if not sheets.connect():
        print("❌ Ошибка подключения!")
        return False
    
    print("✅ Подключение успешно!")
    print(f"\n📊 URL таблицы: {Config.GOOGLE_SHEETS_URL}")
    
    # Загружаем товары
    products = sheets.load_products_from_sheet(
        Config.GOOGLE_SHEETS_URL,
        columns_range="A:AU"
    )
    
    if not products:
        print("❌ Не удалось загрузить товары!")
        return False
    
    print(f"\n✅ Загружено товаров: {len(products)}")
    print("\n📋 Первые 10 товаров:")
    for i, product in enumerate(products[:10], 1):
        print(f"{i}. {product['name']} ({product['type']}) - {product['price']}₽")
    
    # Проверяем поиск похожих товаров
    print("\n" + "=" * 60)
    print("Тест поиска похожих товаров")
    print("=" * 60)
    
    test_name = "Корпус"
    print(f"\n🔍 Ищем товары похожие на: '{test_name}'")
    similar = sheets.find_similar_product(test_name)
    
    if similar:
        print(f"\n✅ Найдено совпадений: {len(similar)}")
        for i, match in enumerate(similar, 1):
            print(f"{i}. {match['name']} ({match['type']}) - Совпадение: {match['match_score']}%")
    else:
        print("❌ Совпадений не найдено!")
    
    print("\n" + "=" * 60)
    print("✅ Все тесты пройдены!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        test_sheets_connection()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.exception("Ошибка при тестировании")
