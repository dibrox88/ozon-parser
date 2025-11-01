"""
Тест: можно ли открыть Ozon БЕЗ cookies с мобильной эмуляцией?
"""
from playwright.sync_api import sync_playwright
from loguru import logger
from config import Config

def main():
    """Тестируем доступ к Ozon без cookies."""
    logger.info("🧪 Тест: Ozon БЕЗ cookies (мобильная эмуляция)")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Показываем браузер
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # Мобильная эмуляция (Strategy5 - работает!)
        context = browser.new_context(
            viewport={'width': 412, 'height': 915},
            user_agent='Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            has_touch=True,
            is_mobile=True,
            device_scale_factor=3.5,
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = context.new_page()
        
        # 1. Главная страница
        logger.info("📍 Открываем главную страницу Ozon...")
        page.goto("https://www.ozon.ru", timeout=30000)
        page.wait_for_timeout(3000)
        
        title = page.title()
        logger.info(f"✅ Title: {title}")
        
        # Проверяем блокировку
        content = page.content()
        if "Доступ ограничен" in content:
            logger.error("❌ БЛОКИРОВКА на главной странице!")
            page.screenshot(path="screenshots/no_cookies_blocked.png")
        else:
            logger.success("✅ Главная страница открылась БЕЗ блокировки!")
            page.screenshot(path="screenshots/no_cookies_main.png")
        
        # 2. Пытаемся открыть страницу "Мои заказы"
        logger.info("\n📍 Пробуем открыть 'Мои заказы' без авторизации...")
        page.goto("https://www.ozon.ru/my/orderlist", timeout=30000)
        page.wait_for_timeout(3000)
        
        title2 = page.title()
        logger.info(f"Title: {title2}")
        
        content2 = page.content()
        if "Доступ ограничен" in content2:
            logger.error("❌ БЛОКИРОВКА на странице заказов!")
            page.screenshot(path="screenshots/no_cookies_orders_blocked.png")
        elif "Войти" in content2 or "Войдите" in content2:
            logger.info("ℹ️ Требуется авторизация (редирект на вход)")
            page.screenshot(path="screenshots/no_cookies_orders_login.png")
            
            # Проверяем куда нас перенаправило
            current_url = page.url
            logger.info(f"Текущий URL: {current_url}")
            
            if "login" in current_url or "signin" in current_url:
                logger.info("✅ Ozon перенаправил на страницу входа (БЕЗ блокировки)")
                logger.info("💡 Можно использовать авторизацию через SMS!")
        else:
            logger.success("✅ Страница заказов открылась!")
            page.screenshot(path="screenshots/no_cookies_orders_ok.png")
        
        # 3. Проверяем есть ли кнопка входа
        logger.info("\n📍 Ищем элементы авторизации...")
        
        # Типичные селекторы для входа
        login_selectors = [
            'button:has-text("Войти")',
            'a:has-text("Войти")',
            '[data-widget="profileMenuAnonymous"]',
            'input[type="tel"]',
            'input[placeholder*="телефон"]',
        ]
        
        for selector in login_selectors:
            element = page.query_selector(selector)
            if element:
                logger.info(f"✅ Найден элемент: {selector}")
            
        logger.info("\n" + "="*60)
        logger.success("✅ Тест завершён! Проверьте скриншоты в папке screenshots/")
        logger.info("="*60)
        
        input("\nНажмите Enter чтобы закрыть браузер...")
        
        browser.close()

if __name__ == "__main__":
    main()
