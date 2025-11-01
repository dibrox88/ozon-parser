"""
Скрипт для тестирования стратегий обхода блокировок Ozon.
Запускается из Telegram бота командой /test_antidetect
"""
import sys
from playwright.sync_api import sync_playwright
from loguru import logger
from antidetect_strategies import StrategyTester
from config import Config

# Настройка логирования
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

def main():
    """Основная функция тестирования."""
    logger.info("🧪 Начинаем тестирование антидетект стратегий")
    
    tester = StrategyTester()
    strategies = tester.get_all_strategies()
    
    results = []
    successful_strategies = []
    
    with sync_playwright() as p:
        # Запускаем браузер
        browser = p.chromium.launch(
            headless=Config.HEADLESS,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        logger.info(f"Браузер запущен (headless={Config.HEADLESS})")
        
        # Тестируем каждую стратегию
        for i, strategy in enumerate(strategies, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Тест #{i}/{len(strategies)}: {strategy.name}")
            logger.info(f"Описание: {strategy.description}")
            logger.info(f"{'='*60}")
            
            success, message, screenshot = tester.test_strategy(
                browser=browser,
                strategy=strategy,
                test_url="https://www.ozon.ru"
            )
            
            results.append({
                'num': i,
                'name': strategy.name,
                'success': success,
                'message': message
            })
            
            if success:
                successful_strategies.append(i)
                logger.success(f"✅ Стратегия #{i} успешна")
            else:
                logger.warning(f"❌ Стратегия #{i} не прошла")
        
        browser.close()
    
    # Выводим итоговые результаты
    logger.info(f"\n{'='*60}")
    logger.info("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    logger.info(f"{'='*60}\n")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} #{result['num']}. {result['name']}")
        print(f"   {result['message']}")
        print()
    
    logger.info(f"{'='*60}")
    if successful_strategies:
        logger.success(f"✅ Успешных стратегий: {len(successful_strategies)}/{len(strategies)}")
        logger.success(f"Рекомендуется использовать стратегию #{successful_strategies[0]}: {results[successful_strategies[0]-1]['name']}")
    else:
        logger.error("❌ Ни одна стратегия не прошла тест")
        logger.warning("Возможно требуется обновить cookies вручную")
    
    logger.info(f"{'='*60}\n")
    
    # Возвращаем код выхода
    return 0 if successful_strategies else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
