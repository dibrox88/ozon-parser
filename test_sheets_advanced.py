"""
Тестовый скрипт для проверки расширенных функций Google Sheets (v1.6.1).
Проверяет группировку, сортировку, формулы и границы.
"""
from pathlib import Path
from loguru import logger
from sheets_sync import sync_to_sheets
from notifier import sync_send_message

# Настройка логирования
Path('logs').mkdir(exist_ok=True)
logger.add(
    "logs/test_sheets_advanced_{time}.log",
    rotation="1 day",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

def main():
    """Главная функция теста."""
    try:
        logger.info("=" * 60)
        logger.info("🧪 ТЕСТИРОВАНИЕ РАСШИРЕННЫХ ФУНКЦИЙ GOOGLE SHEETS")
        logger.info("=" * 60)
        
        sync_send_message(
            "🧪 <b>Тест расширенных функций Sheets</b>\n\n"
            "Проверяем:\n"
            "• Группировку по mapped_name → status\n"
            "• Границы между группами\n"
            "• Формулы SUM в колонке E"
        )
        
        # Используем ozon_orders.json
        test_file = "ozon_orders.json"
        
        logger.info(f"📂 Тестовый файл: {test_file}")
        sync_send_message(f"📂 Файл: <code>{test_file}</code>")
        
        # Запускаем синхронизацию
        logger.info("🔄 Запуск синхронизации с расширенными функциями...")
        result = sync_to_sheets(test_file)
        
        if result:
            logger.info("=" * 60)
            logger.info("✅ ТЕСТ ПРОЙДЕН УСПЕШНО!")
            logger.info("=" * 60)
            sync_send_message(
                "✅ <b>Тест пройден!</b>\n\n"
                "Проверьте Google Sheets:\n"
                "• Товары сгруппированы по названию\n"
                "• Статусы отсортированы (получен→забрать→в пути→отменен)\n"
                "• Есть границы между группами товаров\n"
                "• Формулы SUM в колонке E для каждого заказа"
            )
        else:
            logger.error("=" * 60)
            logger.error("❌ ТЕСТ НЕ ПРОЙДЕН")
            logger.error("=" * 60)
            sync_send_message("❌ <b>Тест не пройден</b>\n\nПроверьте логи для деталей.")
        
        return result
        
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка в тесте: {e}")
        sync_send_message(f"❌ <b>Критическая ошибка</b>\n\n{str(e)}")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
