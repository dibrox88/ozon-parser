"""Тестовый скрипт для парсинга одного заказа с антидетект защитой."""
import sys
from playwright.sync_api import sync_playwright
from loguru import logger
from config import Config
from auth import OzonAuth
from parser import OzonParser
from session_manager import SessionManager
import json


def test_single_order(order_number: str):
    """Тест парсинга одного заказа с Strategy #3 (Desktop with Linux UA)."""
    
    logger.info(f"🧪 Тестируем парсинг заказа: {order_number}")
    logger.info(f"🛡️ Используем Strategy #3: Desktop with Linux UA (успешная стратегия)")
    
    # Конфигурация Strategy #3 из test_strategies.py
    strategy_config = {
        "name": "Strategy 3: Desktop with Linux UA",
        "viewport": {'width': 1920, 'height': 1080},
        "user_agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        "has_touch": False,
        "is_mobile": False,
        "device_scale_factor": 1,
    }
    
    with sync_playwright() as p:
        # Запускаем браузер с антидетект настройками
        browser = p.chromium.launch(
            headless=False,  # Видимый браузер для отладки
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # Создаём контекст с настройками Strategy #3
        context = browser.new_context(
            viewport=strategy_config['viewport'],
            user_agent=strategy_config['user_agent'],
            has_touch=strategy_config['has_touch'],
            is_mobile=strategy_config['is_mobile'],
            device_scale_factor=strategy_config['device_scale_factor'],
            locale='ru-RU',
            timezone_id='Europe/Moscow',
        )
        
        # Добавляем stealth скрипты для обхода детектирования
        context.add_init_script("""
            // Скрываем webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Добавляем plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Переопределяем языки
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
        """)
        
        logger.info("✅ Браузер запущен с Strategy #3 (Desktop + Linux UA + Stealth)")
        
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
                logger.info("📂 Найдена сохраненная сессия, загружаем...")
                
                # Закрываем текущий контекст и загружаем сохранённый
                page.close()
                context.close()
                
                saved_context = session_manager.load_session(
                    browser,
                    viewport=strategy_config['viewport'],
                    user_agent=strategy_config['user_agent'],
                    has_touch=strategy_config['has_touch'],
                    is_mobile=strategy_config['is_mobile'],
                    device_scale_factor=strategy_config['device_scale_factor']
                )
                
                if saved_context:
                    context = saved_context
                    
                    # Добавляем stealth скрипты для загруженного контекста
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['ru-RU', 'ru', 'en-US', 'en']
                        });
                    """)
                    
                    page = context.new_page()
                    logger.info("✅ Сессия загружена успешно")
                else:
                    logger.warning("⚠️ Не удалось загрузить сессию, создаём новую")
                    context = browser.new_context(
                        viewport=strategy_config['viewport'],
                        user_agent=strategy_config['user_agent'],
                        has_touch=strategy_config['has_touch'],
                        is_mobile=strategy_config['is_mobile'],
                        device_scale_factor=strategy_config['device_scale_factor'],
                        locale='ru-RU',
                        timezone_id='Europe/Moscow',
                    )
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
                    """)
                    page = context.new_page()
                
                # Переходим на страницу заказов
                logger.info("🌐 Переход на страницу заказов...")
                page.goto(Config.OZON_ORDERS_URL, timeout=60000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
                
                # Проверяем авторизацию
                if not auth.verify_login():
                    logger.warning("⚠️ Сессия устарела, требуется авторизация")
                    session_manager.delete_session()
                    
                    logger.info("🔑 Выполняем авторизацию...")
                    auth.login()
                    session_manager.save_session(context)
                else:
                    logger.info("✅ Авторизация действительна")
            else:
                logger.info("🔑 Сессия не найдена, выполняем авторизацию...")
                auth.login()
                session_manager.save_session(context)
            
            logger.info("✅ Авторизация успешна")
            
            # Парсим заказ
            logger.info(f"📦 Начинаем парсинг заказа {order_number}...")
            order_data = parser.parse_order_details(order_number)
            
            if order_data:
                logger.info("✅ Заказ успешно спарсен!")
                logger.info(f"\n📊 Результат:")
                logger.info(f"  Номер заказа: {order_data.get('order_number', 'N/A')}")
                logger.info(f"  Дата: {order_data.get('date', 'N/A')}")
                logger.info(f"  Сумма: {order_data.get('total_amount', 0)} ₽")
                logger.info(f"  Товаров: {order_data.get('items_count', 0)} шт")
                logger.info(f"  Позиций: {len(order_data.get('items', []))}")
                
                logger.info(f"\n🛍 Список товаров:")
                for idx, item in enumerate(order_data.get('items', []), 1):
                    logger.info(f"\n  {idx}. {item.get('name', 'N/A')}")
                    logger.info(f"     Количество: {item.get('quantity', 0)} шт")
                    logger.info(f"     Цена: {item.get('price', 0)} ₽")
                    logger.info(f"     Сумма: {item.get('quantity', 0) * item.get('price', 0)} ₽")
                    logger.info(f"     Статус: {item.get('status', 'N/A')}")
                    if item.get('color'):
                        logger.info(f"     Цвет: {item.get('color')}")
                    if item.get('url'):
                        logger.info(f"     URL: {item.get('url')}")
                
                # Сохраняем в JSON
                output_file = f"test_order_{order_number}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(order_data, f, ensure_ascii=False, indent=2)
                logger.info(f"\n💾 Данные сохранены в файл: {output_file}")
                
                # Выводим информацию по проблеме с цветом корпуса
                logger.info(f"\n🔍 ПРОВЕРКА ЦВЕТОВ КОРПУСОВ:")
                corpus_items = [item for item in order_data.get('items', []) if 'корпус' in item.get('name', '').lower()]
                if corpus_items:
                    for idx, item in enumerate(corpus_items, 1):
                        logger.info(f"  Корпус #{idx}:")
                        logger.info(f"    Название: {item.get('name')}")
                        logger.info(f"    Цвет: {item.get('color', 'НЕ ОПРЕДЕЛЁН')}")
                        logger.info(f"    Количество: {item.get('quantity')}")
                else:
                    logger.warning("  ⚠️ Корпусы не найдены в заказе")
                
            else:
                logger.error("❌ Не удалось спарсить заказ")
                logger.error("   Возможные причины:")
                logger.error("   - Заказ не найден")
                logger.error("   - Нет доступа к заказу")
                logger.error("   - Проблемы с парсингом страницы")
            
            # Ждем перед закрытием
            logger.info("\n✅ Тест завершён!")
            logger.info("📝 Нажмите Enter для закрытия браузера...")
            input()
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ Прервано пользователем")
            
        except Exception as e:
            logger.exception(f"❌ Ошибка при тестировании: {e}")
            logger.info("\n📝 Нажмите Enter для закрытия...")
            input()
            
        finally:
            try:
                browser.close()
                logger.info("🔒 Браузер закрыт")
            except:
                pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        order_num = sys.argv[1]
    else:
        logger.info("💡 Использование: python test_single_order.py <номер_заказа>")
        logger.info("   Пример: python test_single_order.py 46206571-0672")
        order_num = input("\nВведите номер заказа: ").strip()
    
    if order_num:
        test_single_order(order_num)
    else:
        logger.error("❌ Номер заказа не указан")
