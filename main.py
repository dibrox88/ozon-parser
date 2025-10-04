"""Главный файл приложения."""
import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from loguru import logger

# Настройка логирования
Path('logs').mkdir(exist_ok=True)
logger.add(
    "logs/ozon_parser_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

from config import Config
from auth import OzonAuth
from parser import OzonParser
from notifier import sync_send_message


def setup_browser_context(browser: Browser) -> BrowserContext:
    """
    Настройка контекста браузера для обхода защиты.
    
    Args:
        browser: Браузер Playwright
        
    Returns:
        Настроенный контекст
    """
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent=Config.USER_AGENT,
        locale='ru-RU',
        timezone_id='Europe/Moscow',
        geolocation={'longitude': 37.6173, 'latitude': 55.7558},  # Москва
        permissions=['geolocation'],
        # Дополнительные параметры для stealth
        extra_http_headers={
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    )
    
    # Добавляем инициализационный скрипт для подмены navigator свойств
    context.add_init_script("""
        // Подменяем webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Подменяем plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Подменяем languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['ru-RU', 'ru', 'en-US', 'en']
        });
        
        // Chrome property
        window.chrome = {
            runtime: {}
        };
        
        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)
    
    return context


def main():
    """Главная функция."""
    try:
        # Проверяем конфигурацию
        logger.info("Проверка конфигурации...")
        Config.validate()
        
        logger.info("Запуск Ozon Parser")
        sync_send_message("🚀 <b>Ozon Parser запущен</b>\n\nНачинаем работу...")
        
        # Запускаем браузер
        with sync_playwright() as p:
            logger.info("Запуск браузера...")
            
            # Запускаем Chromium с аргументами для обхода защиты
            browser = p.chromium.launch(
                headless=Config.HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )
            
            # Настраиваем контекст
            context = setup_browser_context(browser)
            page = context.new_page()
            
            # Устанавливаем таймауты
            page.set_default_timeout(Config.DEFAULT_TIMEOUT)
            page.set_default_navigation_timeout(Config.NAVIGATION_TIMEOUT)
            
            try:
                # Авторизация
                auth = OzonAuth(page)
                if not auth.login():
                    logger.error("Не удалось авторизоваться")
                    sync_send_message("❌ Авторизация не удалась")
                    return
                
                # Парсинг
                parser = OzonParser(page)
                if not parser.navigate_to_orders():
                    logger.error("Не удалось перейти к заказам")
                    sync_send_message("❌ Не удалось перейти к заказам")
                    return
                
                # Получаем заказы
                orders = parser.parse_orders()
                
                logger.info(f"Парсинг завершен. Получено заказов: {len(orders)}")
                sync_send_message(f"✅ <b>Парсинг завершен</b>\n\nВсего заказов: {len(orders)}")
                
                # Ждем перед закрытием для просмотра результата
                logger.info("Ожидание перед закрытием браузера...")
                page.wait_for_timeout(5000)
                
            finally:
                # Закрываем браузер
                logger.info("Закрытие браузера...")
                context.close()
                browser.close()
        
        logger.info("Работа завершена успешно")
        sync_send_message("✅ <b>Работа завершена</b>")
        
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        print(f"\n❌ Ошибка конфигурации:\n{e}\n")
        print("Пожалуйста, создайте файл .env на основе .env.example и заполните все необходимые поля.")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
        sync_send_message("⚠️ Работа прервана пользователем")
        sys.exit(0)
        
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sync_send_message(f"❌ <b>Критическая ошибка</b>\n\n{str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
