"""Скрипт для анализа структуры страницы заказов."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from loguru import logger

# Настройка логирования
Path('logs').mkdir(exist_ok=True)
logger.add(
    "logs/analyze_{time}.log",
    rotation="1 day",
    level="INFO"
)

from config import Config
from auth import OzonAuth
from notifier import sync_send_message


def analyze_orders_page():
    """Анализ структуры страницы заказов."""
    try:
        Config.validate()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=Config.HEADLESS)
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=Config.USER_AGENT,
            )
            
            # Маскировка автоматизации
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { 
                    get: () => undefined 
                });
                
                Object.defineProperty(navigator, 'plugins', { 
                    get: () => [1, 2, 3, 4, 5] 
                });
            """)
            
            page = context.new_page()
            
            # Авторизация
            auth = OzonAuth(page)
            if not auth.login():
                print("❌ Авторизация не удалась")
                return
            
            # Переход на страницу заказов
            print("\n📦 Переходим на страницу заказов...")
            page.goto(Config.OZON_ORDERS_URL, timeout=60000)
            page.wait_for_load_state('networkidle', timeout=30000)
            
            import time
            time.sleep(5)
            
            # Анализ структуры
            print("\n🔍 Анализ структуры страницы...\n")
            
            # Ищем контейнеры с заказами
            possible_selectors = [
                '[data-widget="orders"]',
                '[data-widget="orderList"]',
                '.order',
                '.order-item',
                '[class*="order"]',
                'article',
                '[role="article"]',
            ]
            
            for selector in possible_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"✅ Найдено {len(elements)} элементов по селектору: {selector}")
                    
                    # Анализируем первый элемент
                    if len(elements) > 0:
                        first = elements[0]
                        html = first.inner_html()
                        print(f"   HTML первого элемента (первые 500 символов):")
                        print(f"   {html[:500]}...\n")
            
            # Сохраняем полный HTML
            html_file = "screenshots/orders_page.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page.content())
            print(f"\n💾 Полный HTML сохранен в: {html_file}")
            
            # Делаем скриншот
            screenshot = "screenshots/orders_analysis.png"
            page.screenshot(path=screenshot, full_page=True)
            print(f"📸 Скриншот сохранен в: {screenshot}")
            
            # Отправляем в Telegram
            sync_send_message(f"📊 Анализ завершен!\n\nHTML: {html_file}\nСкриншот: {screenshot}")
            
            print("\n✅ Анализ завершен!")
            print("Проверьте файлы:")
            print(f"  - {html_file}")
            print(f"  - {screenshot}")
            
            input("\nНажмите Enter для закрытия браузера...")
            
            context.close()
            browser.close()
            
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    analyze_orders_page()
