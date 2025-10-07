"""
Тестовый скрипт для проверки синхронизации с Google Sheets.
"""
from pathlib import Path
from loguru import logger
from sheets_sync import sync_to_sheets
from notifier import sync_send_message

# Настройка логирования
Path('logs').mkdir(exist_ok=True)
logger.add(
    "logs/test_sync_{time}.log",
    rotation="1 day",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

def main():
    """Главная функция теста."""
    try:
        logger.info("=" * 60)
        logger.info("🧪 ТЕСТИРОВАНИЕ СИНХРОНИЗАЦИИ С GOOGLE SHEETS")
        logger.info("=" * 60)
        
        sync_send_message("🧪 <b>Запуск тестирования синхронизации</b>\n\nПроверяем работу sheets_sync.py...")
        
        # Используем существующий файл с сопоставленными данными
        test_file = "ozon_orders_rematched_2025-10-06_22-13-34.json"
        
        logger.info(f"📂 Тестовый файл: {test_file}")
        sync_send_message(f"📂 Тестовый файл:\n<code>{test_file}</code>")
        
        # Запускаем синхронизацию
        logger.info("🔄 Запуск синхронизации...")
        result = sync_to_sheets(test_file)
        
        if result:
            logger.info("=" * 60)
            logger.info("✅ ТЕСТ ПРОЙДЕН УСПЕШНО!")
            logger.info("=" * 60)
            sync_send_message("✅ <b>Тест пройден!</b>\n\nПроверьте Google Sheets - должны появиться новые заказы.")
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
