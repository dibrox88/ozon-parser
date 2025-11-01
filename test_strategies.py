"""
Серия тестов для подбора рабочей стратегии обхода блокировки Ozon.
Тестируем разные комбинации настроек браузера.
"""
import time
from playwright.sync_api import sync_playwright
from loguru import logger
from notifier import sync_send_message, sync_send_photo

# Стратегии для тестирования
STRATEGIES = [
    {
        "name": "Strategy 1: Mobile (baseline - работает)",
        "viewport": {'width': 412, 'height': 915},
        "user_agent": 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
        "has_touch": True,
        "is_mobile": True,
        "device_scale_factor": 3.5,
    },
    {
        "name": "Strategy 2: Desktop Standard (1920x1080)",
        "viewport": {'width': 1920, 'height': 1080},
        "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        "has_touch": False,
        "is_mobile": False,
        "device_scale_factor": 1,
    },
    {
        "name": "Strategy 3: Desktop with Linux UA",
        "viewport": {'width': 1920, 'height': 1080},
        "user_agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        "has_touch": False,
        "is_mobile": False,
        "device_scale_factor": 1,
    },
    {
        "name": "Strategy 4: Desktop with Mac UA",
        "viewport": {'width': 1920, 'height': 1080},
        "user_agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        "has_touch": False,
        "is_mobile": False,
        "device_scale_factor": 2,
    },
    {
        "name": "Strategy 5: Tablet (iPad Pro)",
        "viewport": {'width': 1024, 'height': 1366},
        "user_agent": 'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        "has_touch": True,
        "is_mobile": False,
        "device_scale_factor": 2,
    },
    {
        "name": "Strategy 6: Desktop Small (1366x768)",
        "viewport": {'width': 1366, 'height': 768},
        "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        "has_touch": False,
        "is_mobile": False,
        "device_scale_factor": 1,
    },
    {
        "name": "Strategy 7: Desktop with Older Chrome",
        "viewport": {'width': 1920, 'height': 1080},
        "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        "has_touch": False,
        "is_mobile": False,
        "device_scale_factor": 1,
    },
    {
        "name": "Strategy 8: Android Tablet",
        "viewport": {'width': 800, 'height': 1280},
        "user_agent": 'Mozilla/5.0 (Linux; Android 13; SM-X906B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Safari/537.36',
        "has_touch": True,
        "is_mobile": False,
        "device_scale_factor": 2,
    },
]


def test_strategy(strategy, strategy_num):
    """Тестирует одну стратегию."""
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 ТЕСТ #{strategy_num}: {strategy['name']}")
    logger.info(f"{'='*80}")
    
    sync_send_message(
        f"🧪 <b>Тест #{strategy_num}</b>\n\n"
        f"<b>{strategy['name']}</b>\n\n"
        f"Viewport: {strategy['viewport']['width']}x{strategy['viewport']['height']}\n"
        f"Mobile: {strategy['is_mobile']}\n"
        f"Touch: {strategy['has_touch']}"
    )
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            # Создаём контекст с настройками стратегии
            context = browser.new_context(
                viewport=strategy['viewport'],
                user_agent=strategy['user_agent'],
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                has_touch=strategy['has_touch'],
                is_mobile=strategy['is_mobile'],
                device_scale_factor=strategy['device_scale_factor'],
            )
            
            # Минимальный stealth
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = context.new_page()
            
            # Тест 1: Главная страница
            logger.info("📍 Тест 1/3: Открываем главную страницу...")
            page.goto("https://www.ozon.ru", timeout=30000)
            page.wait_for_timeout(3000)
            
            title = page.title()
            content = page.content()
            
            if "Доступ ограничен" in content:
                logger.error(f"❌ Блокировка на главной!")
                screenshot_path = f"screenshots/strategy{strategy_num}_blocked.png"
                page.screenshot(path=screenshot_path)
                sync_send_photo(
                    screenshot_path,
                    f"❌ <b>Стратегия #{strategy_num}: БЛОКИРОВКА</b>\n\n{strategy['name']}\n\nTitle: {title}"
                )
                browser.close()
                return False
            
            logger.success(f"✅ Главная OK: {title}")
            screenshot_path = f"screenshots/strategy{strategy_num}_main.png"
            page.screenshot(path=screenshot_path)
            
            # Тест 2: Страница категории
            logger.info("📍 Тест 2/3: Открываем категорию...")
            page.goto("https://www.ozon.ru/category/elektronika-15500/", timeout=30000)
            page.wait_for_timeout(3000)
            
            content2 = page.content()
            if "Доступ ограничен" in content2:
                logger.error(f"❌ Блокировка на категории!")
                screenshot_path = f"screenshots/strategy{strategy_num}_category_blocked.png"
                page.screenshot(path=screenshot_path)
                sync_send_photo(
                    screenshot_path,
                    f"❌ <b>Стратегия #{strategy_num}: БЛОКИРОВКА на категории</b>"
                )
                browser.close()
                return False
            
            logger.success(f"✅ Категория OK")
            
            # Тест 3: Страница заказов
            logger.info("📍 Тест 3/3: Открываем страницу заказов...")
            page.goto("https://www.ozon.ru/my/orderlist", timeout=30000)
            page.wait_for_timeout(3000)
            
            content3 = page.content()
            title3 = page.title()
            
            if "Доступ ограничен" in content3:
                logger.error(f"❌ Блокировка на заказах!")
                screenshot_path = f"screenshots/strategy{strategy_num}_orders_blocked.png"
                page.screenshot(path=screenshot_path)
                sync_send_photo(
                    screenshot_path,
                    f"❌ <b>Стратегия #{strategy_num}: БЛОКИРОВКА на заказах</b>"
                )
                browser.close()
                return False
            
            logger.success(f"✅ Заказы OK (требуется авторизация)")
            screenshot_path = f"screenshots/strategy{strategy_num}_orders.png"
            page.screenshot(path=screenshot_path)
            sync_send_photo(
                screenshot_path,
                f"✅ <b>Стратегия #{strategy_num}: УСПЕХ!</b>\n\n"
                f"{strategy['name']}\n\n"
                f"Все 3 теста пройдены:\n"
                f"• Главная ✅\n"
                f"• Категория ✅\n"
                f"• Заказы ✅\n\n"
                f"Title: {title3}"
            )
            
            browser.close()
            logger.success(f"✅ Стратегия #{strategy_num} - ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка в стратегии #{strategy_num}: {e}")
        sync_send_message(f"❌ <b>Стратегия #{strategy_num}: ОШИБКА</b>\n\n{str(e)}")
        return False


def main():
    """Запускаем все тесты."""
    logger.info("🚀 Начинаем серию тестов стратегий")
    sync_send_message(
        "🚀 <b>Серия тестов обхода блокировки</b>\n\n"
        f"Будет протестировано {len(STRATEGIES)} стратегий\n\n"
        "Каждая стратегия проходит 3 теста:\n"
        "1️⃣ Главная страница\n"
        "2️⃣ Страница категории\n"
        "3️⃣ Страница заказов\n\n"
        "Ожидайте результаты..."
    )
    
    results = []
    
    for i, strategy in enumerate(STRATEGIES, start=1):
        success = test_strategy(strategy, i)
        results.append({
            "num": i,
            "name": strategy["name"],
            "success": success
        })
        
        # Пауза между тестами
        if i < len(STRATEGIES):
            logger.info(f"⏸️ Пауза 5 секунд перед следующим тестом...")
            time.sleep(5)
    
    # Итоговый отчёт
    logger.info(f"\n{'='*80}")
    logger.info("📊 ИТОГОВЫЙ ОТЧЁТ")
    logger.info(f"{'='*80}")
    
    report = "📊 <b>ИТОГОВЫЙ ОТЧЁТ</b>\n\n"
    successful = []
    failed = []
    
    for result in results:
        if result["success"]:
            logger.success(f"✅ #{result['num']}: {result['name']}")
            successful.append(f"✅ #{result['num']}: {result['name']}")
        else:
            logger.error(f"❌ #{result['num']}: {result['name']}")
            failed.append(f"❌ #{result['num']}: {result['name']}")
    
    if successful:
        report += "<b>✅ РАБОЧИЕ СТРАТЕГИИ:</b>\n" + "\n".join(successful) + "\n\n"
    
    if failed:
        report += "<b>❌ ЗАБЛОКИРОВАННЫЕ:</b>\n" + "\n".join(failed) + "\n\n"
    
    report += f"\n<b>Итого:</b> {len(successful)}/{len(STRATEGIES)} успешных"
    
    sync_send_message(report)
    
    logger.info(f"\n✅ Тестирование завершено!")
    logger.info(f"Успешных: {len(successful)}/{len(STRATEGIES)}")


if __name__ == "__main__":
    main()
