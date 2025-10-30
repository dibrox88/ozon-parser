"""Тестовый скрипт для парсинга одного заказа."""
from playwright.sync_api import sync_playwright
from loguru import logger
from config import Config
from auth import OzonAuth
from parser import OzonParser
from session_manager import SessionManager
import json


def test_single_order():
    """Тест парсинга одного заказа."""
    order_number = "46206571-0662"
    
    logger.info(f"🧪 Тестируем парсинг заказа: {order_number}")
    
    with sync_playwright() as p:
        # Запускаем браузер
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
        logger.debug("✅ Добавлен init_script для маскировки автоматизации")
        
        page = context.new_page()
        
        try:
            # Создаем экземпляры классов
            auth = OzonAuth(page)
            parser = OzonParser(page)
            session_manager = SessionManager()
            
            # Авторизуемся
            logger.info("🔐 Проверяем авторизацию...")
            
            # Пробуем загрузить сессию
            if session_manager.session_exists():
                logger.info("📂 Загружаем сохраненную сессию...")
                session_manager.load_session(browser)
                page.goto(Config.OZON_ORDERS_URL)
                page.wait_for_load_state('networkidle')
                
                # Проверяем авторизацию
                if not auth.verify_login():
                    logger.warning("Сессия устарела, требуется авторизация")
                    session_manager.delete_session()
                    auth.login()
                    session_manager.save_session(context)
            else:
                logger.info("🔑 Выполняем авторизацию...")
                auth.login()
                session_manager.save_session(context)
            
            logger.info("✅ Авторизация успешна")
            
            # Парсим заказ
            logger.info(f"📦 Парсим заказ {order_number}...")
            order_data = parser.parse_order_details(order_number)
            
            if order_data:
                logger.info("✅ Заказ успешно спарсен!")
                logger.info(f"📊 Результат:")
                logger.info(f"  Дата: {order_data['date']}")
                logger.info(f"  Сумма: {order_data['total_amount']} ₽")
                logger.info(f"  Товаров: {order_data['items_count']} шт ({len(order_data['items'])} позиций)")
                
                logger.info(f"\n🛍 Список товаров:")
                for idx, item in enumerate(order_data['items'], 1):
                    logger.info(f"  {idx}. {item['name']}")
                    logger.info(f"     Количество: {item['quantity']}")
                    logger.info(f"     Цена: {item['price']} ₽")
                    logger.info(f"     Сумма: {item['quantity'] * item['price']} ₽")
                    logger.info(f"     Статус: {item['status']}")
                
                # Сохраняем в JSON
                output_file = f"test_order_{order_number}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(order_data, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 Данные сохранены в {output_file}")
                
            else:
                logger.error("❌ Не удалось спарсить заказ")
            
            # Ждем перед закрытием
            input("\nНажмите Enter для завершения...")
            
        finally:
            browser.close()


if __name__ == "__main__":
    test_single_order()
