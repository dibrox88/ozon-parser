"""Главный файл приложения."""
import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from loguru import logger
import fcntl  # Для блокировки файла (Unix)
import time

# ВАЖНО: playwright-stealth ВЫЗЫВАЕТ БЛОКИРОВКУ на Ozon!
# Не используем его - достаточно только базовой подмены navigator.webdriver
# try:
#     from playwright_stealth import Stealth
#     stealth = Stealth()
#     STEALTH_AVAILABLE = True
#     logger.info("✅ playwright-stealth загружен (v2.0)")
# except ImportError:
#     logger.warning("playwright-stealth не установлен, используем базовую защиту")
#     STEALTH_AVAILABLE = False
#     stealth = None

STEALTH_AVAILABLE = False
stealth = None

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
from session_manager import SessionManager


def main():
    """Главная функция."""
    # Парсинг аргументов командной строки
    import argparse
    parser_args = argparse.ArgumentParser(description='Ozon Parser')
    parser_args.add_argument('--range', nargs=2, metavar=('FIRST', 'LAST'),
                            help='Parse range of orders (e.g., --range 46206571-0680 46206571-0710)')
    args = parser_args.parse_args()
    
    # Путь к файлу-флагу блокировки
    lock_file_path = Path("logs/parser.lock")
    lock_file_path.parent.mkdir(exist_ok=True)
    lock_file = None  # Инициализация переменной
    
    try:
        # Пытаемся создать файл-флаг блокировки
        lock_file = open(lock_file_path, 'w')
        
        try:
            # Пытаемся получить эксклюзивную блокировку (только для Unix)
            if sys.platform != 'win32':
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                # Для Windows - просто проверяем существование файла
                if lock_file_path.exists():
                    # Проверяем, не устарел ли lock (более 2 часов)
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age < 7200:  # 2 часа
                        logger.warning("⚠️ Парсер уже запущен! Обнаружен активный lock файл.")
                        sync_send_message("⚠️ <b>Парсер уже запущен</b>\n\nДождитесь завершения текущего процесса или используйте /stop")
                        sys.exit(0)
                    else:
                        logger.warning(f"⚠️ Найден устаревший lock файл (возраст: {lock_age/60:.1f} мин). Удаляем...")
                        lock_file_path.unlink()
            
            # Записываем PID в lock файл
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            
            logger.info(f"🔒 Lock файл создан: {lock_file_path}")
            
        except (IOError, OSError) as e:
            logger.warning(f"⚠️ Парсер уже запущен! Lock файл заблокирован: {e}")
            sync_send_message("⚠️ <b>Парсер уже запущен</b>\n\nДождитесь завершения текущего процесса или используйте /stop")
            lock_file.close()
            sys.exit(0)
        
        # Основная логика парсера
        # Проверяем конфигурацию
        Config.validate()
        
        #logger.info("Запуск Ozon Parser v2.2.0 (Strategy #3: Desktop Linux UA)")
        #sync_send_message("🚀 <b>Ozon Parser v2.2.0</b>\n\n🖥️ Strategy #3: Desktop Linux 1920x1080\n✅ Обход защиты активен")
        
        # Инициализируем менеджер сессий
        session_manager = SessionManager()
        
        # Запускаем браузер
        with sync_playwright() as p:
            logger.info("Запуск браузера...")
            
            # Strategy #3: Desktop with Linux UA (ПРОТЕСТИРОВАНО - РАБОТАЕТ!)
            logger.info("🌐 Запускаем браузер (Strategy #3: Desktop Linux UA)...")
            browser = p.chromium.launch(
                headless=Config.HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            # Пробуем загрузить сохраненную сессию или экспортированные cookies
            context = None
            page = None
            needs_auth = True
            cookies_failed = False  # Флаг: пытались ли использовать cookies и они не сработали
            
            # ========== ВРЕМЕННО ОТКЛЮЧЕНО ДЛЯ ТЕСТИРОВАНИЯ ==========
            # ПРИОРИТЕТ 1: Проверяем наличие экспортированных cookies (обходит блокировку!)
            # if session_manager.cookies_exist():
            #     logger.info("🍪 Найдены экспортированные cookies! Используем их для обхода блокировки...")
            #     sync_send_message("🍪 Используем cookies из обычного браузера...")
            #     
            #     # Создаем новый контекст
            #     context = setup_browser_context(browser)
            #     
            #     # Загружаем cookies
            #     if session_manager.load_cookies_to_context(context):
            #         page = context.new_page()
            #         
            #         # Применяем stealth для обхода антибот защиты
            #         if STEALTH_AVAILABLE and stealth:
            #             stealth.apply_stealth_sync(page)
            #             logger.info("✅ Stealth применен к странице")
            #         
            #         page.set_default_timeout(Config.DEFAULT_TIMEOUT)
            #         page.set_default_navigation_timeout(Config.NAVIGATION_TIMEOUT)
            #         
            #         try:
            #             # Пробуем открыть страницу заказов
            #             logger.info("📍 Проверяем авторизацию с cookies...")
            #             page.goto(Config.OZON_ORDERS_URL, timeout=30000)
            #             page.wait_for_load_state('networkidle', timeout=15000)
            #             
            #             # Проверяем, авторизованы ли мы
            #             auth = OzonAuth(page)
            #             if auth.verify_login():
            #                 logger.success("✅ Авторизация с cookies успешна! Блокировка обойдена!")
            #                 sync_send_message("✅ Вход выполнен через cookies! Парсинг начинается...")
            #                 needs_auth = False
            #             else:
            #                 logger.warning("⚠️ Cookies устарели, требуется повторный экспорт")
            #                 sync_send_message("⚠️ Cookies устарели. Экспортируйте новые: python export_cookies.py")
            #                 cookies_failed = True  # Отмечаем что cookies не сработали, но page ещё открыт
            #                 # НЕ закрываем context и page - переиспользуем их для авторизации
            #         
            #         except RuntimeError as e:
            #             # Блокировка обнаружена - немедленно останавливаем
            #             if "Блокировка Ozon" in str(e):
            #                 logger.error(f"🛑 ПАРСИНГ ОСТАНОВЛЕН: {e}")
            #                 if context:
            #                     context.close()
            #                 browser.close()
            #                 sys.exit(1)
            #             else:
            #                 raise  # Другие RuntimeError пробрасываем
            #         
            #         except Exception as e:
            #             logger.warning(f"⚠️ Cookies не сработали: {e}")
            #             sync_send_message(f"⚠️ Cookies не сработали. Попробуйте экспортировать заново.")
            #             if context:
            #                 context.close()
            #             context = None
            #     else:
            #         logger.error("❌ Не удалось загрузить cookies")
            #         if context:
            #             context.close()
            #         context = None
            # ========== КОНЕЦ ВРЕМЕННОГО ОТКЛЮЧЕНИЯ ==========
            
            logger.info("🖥️ Используем Strategy #3 (Desktop Linux UA)")
            #sync_send_message("🖥️ <b>Desktop Linux UA</b>\n\nРазрешение: 1920x1080\nТестирование обхода защиты...")
            
            # ПРИОРИТЕТ 2: Пытаемся загрузить старую Playwright сессию
            # Вместо того чтобы позволять session_manager создавать собственный контекст
            # (который раньше использовал mobile emulation), создаём контекст с
            # storage_state, но с текущей стратегией (Desktop Linux UA). Это предотвращает
            # смену User-Agent/viewport при восстановлении сессии и делает поведение
            # последовательным.
            if session_manager.session_exists():
                logger.info("🔄 Пробуем загрузить сохраненную сессию...")
                sync_send_message("🔄 Найдена сохраненная сессия. Проверяем...")

                try:
                    context = browser.new_context(
                        storage_state=str(session_manager.state_file),
                        viewport={'width': 1920, 'height': 1080},
                        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        locale='ru-RU',
                        timezone_id='Europe/Moscow',
                        has_touch=False,
                        is_mobile=False,
                        device_scale_factor=1,
                    )

                    # Обычная минимальная подмена для navigator.webdriver
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """)

                    page = context.new_page()

                    # НЕ применяем playwright-stealth - он вызывает блокировку!
                    # Достаточно только базовой подмены navigator.webdriver выше

                    page.set_default_timeout(Config.DEFAULT_TIMEOUT)
                    page.set_default_navigation_timeout(Config.NAVIGATION_TIMEOUT)

                    # Проверяем, работает ли сессия
                    try:
                        page.goto(Config.OZON_ORDERS_URL, timeout=30000)
                        page.wait_for_load_state('networkidle', timeout=15000)

                        auth = OzonAuth(page)
                        if auth.verify_login():
                            logger.info("✅ Сессия действительна! Авторизация не требуется.")
                            sync_send_message("✅ Сессия действительна! Пропускаем авторизацию.")
                            needs_auth = False
                        else:
                            logger.warning("⚠️ Сессия устарела, требуется повторная авторизация")
                            sync_send_message("⚠️ Сессия устарела. Выполняем авторизацию...")
                            session_manager.delete_session()
                            context.close()
                            context = None

                    except RuntimeError as e:
                        # Блокировка обнаружена
                        if "Блокировка Ozon" in str(e):
                            logger.error(f"🛑 ПАРСИНГ ОСТАНОВЛЕН: {e}")
                            if context:
                                context.close()
                            browser.close()
                            sys.exit(1)
                        else:
                            raise

                except Exception as e:
                    logger.warning(f"⚠️ Не удалось загрузить сохраненную сессию корректно: {e}")
                    sync_send_message("⚠️ Не удалось использовать сессию. Выполняем авторизацию...")
                    session_manager.delete_session()
                    if 'context' in locals() and context:
                        context.close()
                    context = None
            
            # Если сессии нет или она не работает - создаем новый контекст и авторизуемся
            if context is None:
                # Desktop с Linux User-Agent (Strategy #3 - РАБОТАЕТ!)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='ru-RU',
                    timezone_id='Europe/Moscow',
                    has_touch=False,
                    is_mobile=False,
                    device_scale_factor=1,
                )
                
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                page = context.new_page()
                
                # НЕ применяем playwright-stealth - он вызывает блокировку!
                # Достаточно только базовой подмены navigator.webdriver выше
                
                page.set_default_timeout(Config.DEFAULT_TIMEOUT)
                page.set_default_navigation_timeout(Config.NAVIGATION_TIMEOUT)
            
            # Убеждаемся что page определен
            if page is None:
                raise RuntimeError("Page не был инициализирован")
            
            try:
                # Авторизация (если нужна)
                if needs_auth:
                    auth = OzonAuth(page)
                    # Если cookies не сработали, передаём флаг чтобы не делать лишний goto
                    if not auth.login(skip_initial_navigation=cookies_failed):
                        logger.error("❌ Авторизация не удалась или обнаружена блокировка")
                        sync_send_message("❌ <b>Работа остановлена</b>\n\nАвторизация не удалась или Ozon заблокировал доступ.")
                        
                        # КРИТИЧЕСКАЯ ОШИБКА - останавливаем парсинг полностью
                        logger.error("🛑 ПАРСИНГ ОСТАНОВЛЕН: блокировка или неудачная авторизация")
                        context.close()
                        browser.close()
                        sys.exit(1)  # Выход с кодом ошибки
                    
                    # Сохраняем сессию после успешной авторизации
                    logger.info("💾 Сохраняем сессию...")
                    if session_manager.save_session(context):
                        sync_send_message("💾 Сессия сохранена. В следующий раз авторизация не потребуется!")
                    else:
                        logger.warning("⚠️ Не удалось сохранить сессию")
                
                # Парсинг
                parser = OzonParser(page)
                if not parser.navigate_to_orders():
                    logger.error("❌ Не удалось перейти к заказам (возможна блокировка)")
                    sync_send_message("❌ <b>Работа остановлена</b>\n\nНе удалось перейти к заказам.")
                    
                    # КРИТИЧЕСКАЯ ОШИБКА - останавливаем парсинг
                    logger.error("🛑 ПАРСИНГ ОСТАНОВЛЕН: блокировка или ошибка доступа к заказам")
                    context.close()
                    browser.close()
                    sys.exit(1)
                
                # Получаем список заказов (с диапазоном если указан)
                if args.range:
                    first_order, last_order = args.range
                    orders = parser.parse_orders(first_order=first_order, last_order=last_order)
                else:
                    orders = parser.parse_orders()
                
                logger.info(f"Парсинг номеров завершен. Получено заказов: {len(orders)}")
                sync_send_message(f"✅ <b>Найдено заказов: {len(orders)}</b>\n\nНачинаем парсинг деталей...")
                
                # Парсим детали каждого заказа
                if orders:
                    logger.info("📄 Начинаем парсинг деталей заказов...")
                    all_orders_data = []
                    
                    # Парсим все заказы
                    for i, order_number in enumerate(orders, 1):
                        logger.info(f"📦 [{i}/{len(orders)}] Парсим детали заказа: {order_number}")
                        sync_send_message(f"📦 Парсим заказ {order_number}")
                        
                        try:
                            order_details = parser.parse_order_details(order_number)
                            
                            if order_details:
                                all_orders_data.append(order_details)
                                logger.info(f"✅ [{i}/{len(orders)}] Успешно спарсен заказ {order_number}")
                                logger.info(f"   Товаров: {order_details['items_count']}, Сумма: {order_details['total_amount']}₽")
                            else:
                                logger.warning(f"⚠️ [{i}/{len(orders)}] Не удалось спарсить заказ {order_number}")
                        
                        except RuntimeError as e:
                            # Блокировка обнаружена - немедленно останавливаем парсинг
                            if "Блокировка Ozon" in str(e):
                                logger.error(f"🛑 ПАРСИНГ ОСТАНОВЛЕН: {e}")
                                context.close()
                                browser.close()
                                sys.exit(1)
                            else:
                                raise  # Другие RuntimeError пробрасываем дальше
                    
                    logger.info(f"✅ Парсинг завершен. Успешно обработано: {len(all_orders_data)}/{len(orders)} заказов")
                    
                    # Фильтруем исключённые заказы
                    from excluded_manager import ExcludedOrdersManager
                    excluded_manager = ExcludedOrdersManager()
                    
                    if excluded_manager.get_count() > 0:
                        logger.info(f"📋 В списке исключённых: {excluded_manager.get_count()} заказов")
                        valid_orders, excluded_orders = excluded_manager.filter_orders(all_orders_data)
                        
                        if excluded_orders:
                            logger.info(f"⏭️ Пропущено исключённых заказов: {len(excluded_orders)}")
                            excluded_nums = [o.get('order_number', '?') for o in excluded_orders]
                            sync_send_message(f"⏭️ <b>Пропущено исключённых заказов:</b> {len(excluded_orders)}\n\n" + 
                                            "\n".join(f"• <code>{num}</code>" for num in excluded_nums))
                        
                        all_orders_data = valid_orders
                    
                    logger.info(f"✅ Заказов для обработки: {len(all_orders_data)}")
                    
                    # Формируем детальный отчет о спарсенных заказах
                    summary_message = f"✅ <b>Парсинг завершен!</b>\n\n"
                    summary_message += f"📊 <b>Обработано:</b> {len(all_orders_data)}/{len(orders)} заказов\n\n"
                    
                    if all_orders_data:
                        total_items = sum(order.get('items_count', 0) for order in all_orders_data)
                        # Исправлено: проверяем на None перед сложением
                        total_amount = sum(order.get('total_amount') or 0 for order in all_orders_data)
                        
                        summary_message += f"📦 <b>Всего товаров:</b> {total_items} шт\n"
                        summary_message += f"💰 <b>Общая сумма:</b> {total_amount:,.2f} ₽\n\n"
                        summary_message += f"<b>Детали заказов:</b>\n"
                        
                        for idx, order in enumerate(all_orders_data[:10], 1):  # Показываем первые 10
                            order_num = order.get('order_number', '?')
                            order_date = order.get('date', '?')
                            order_items = order.get('items_count', 0)
                            order_sum = order.get('total_amount', 0)
                            
                            summary_message += f"\n{idx}. <code>{order_num}</code>"
                            summary_message += f"\n   📅 {order_date} | 📦 {order_items} шт | 💰 {order_sum:,.0f} ₽"
                        
                        if len(all_orders_data) > 10:
                            summary_message += f"\n\n... и ещё {len(all_orders_data) - 10} заказов"
                    
                    sync_send_message(summary_message)
                    
                    # Сопоставление товаров с каталогом из Google Sheets
                    if all_orders_data and Config.GOOGLE_SHEETS_URL and Config.GOOGLE_CREDENTIALS_FILE:
                        try:
                            logger.info("🔄 Запуск сопоставления товаров с каталогом...")
                            sync_send_message("🔄 <b>Сопоставление с каталогом...</b>")
                            
                            from sheets_manager import SheetsManager
                            from product_matcher import ProductMatcher, enrich_orders_with_mapping
                            from bundle_manager import BundleManager
                            
                            # Подключаемся к Google Sheets
                            sheets = SheetsManager(Config.GOOGLE_CREDENTIALS_FILE)
                            if sheets.connect():
                                # Загружаем товары из таблицы (структура: цена, название, тип, номер заказа)
                                catalog_products = sheets.load_products_from_sheet(
                                    Config.GOOGLE_SHEETS_URL,
                                    columns_range="A:AU"
                                )
                                
                                if catalog_products:
                                    logger.info(f"✅ Загружено товаров из каталога: {len(catalog_products)}")
                                    sync_send_message(f"✅ Загружено товаров: {len(catalog_products)}")
                                    
                                    # Создаём matcher с основным файлом кеша
                                    matcher = ProductMatcher(
                                        catalog_products,
                                        mappings_file=Config.PRODUCT_MAPPINGS_FILE
                                    )
                                    
                                    # Создаём менеджер связок
                                    bundle_manager = BundleManager()
                                    
                                    # Обогащаем данные с интерактивным режимом (interactive=True)
                                    all_orders_data = enrich_orders_with_mapping(
                                        all_orders_data, 
                                        matcher,
                                        interactive=True,  # ИНТЕРАКТИВНЫЙ РЕЖИМ через Telegram
                                        excluded_manager=excluded_manager,  # Передаём менеджер исключений
                                        bundle_manager=bundle_manager  # Передаём менеджер связок
                                    )
                                    
                                    logger.info("✅ Сопоставление завершено")
                                    sync_send_message("✅ <b>Сопоставление завершено!</b>")
                                else:
                                    logger.warning("⚠️ Каталог товаров пуст")
                            else:
                                logger.warning("⚠️ Не удалось подключиться к Google Sheets")
                                
                        except Exception as e:
                            logger.error(f"❌ Ошибка при сопоставлении товаров: {e}")
                            sync_send_message(f"⚠️ Ошибка сопоставления: {e}")
                    
                    # Экспортируем данные в JSON
                    if all_orders_data:
                        from export_data import export_orders
                        try:
                            json_file = export_orders(all_orders_data)
                            logger.info(f"📁 Данные сохранены в: {json_file}")
                            
                            # Формируем итоговый отчет
                            export_message = f"📁 <b>Данные экспортированы</b>\n\n"
                            export_message += f"📄 Файл: <code>{json_file}</code>\n\n"
                            
                            # Статистика по типам товаров (если есть маппинг)
                            types_stats = {}
                            for order in all_orders_data:
                                for item in order.get('items', []):
                                    item_type = item.get('type', 'Не указан')
                                    if item_type not in types_stats:
                                        types_stats[item_type] = {'count': 0, 'sum': 0}
                                    types_stats[item_type]['count'] += item.get('quantity', 0)
                                    types_stats[item_type]['sum'] += item.get('quantity', 0) * item.get('price', 0)
                            
                            if types_stats:
                                export_message += "<b>📊 Статистика по типам:</b>\n"
                                for item_type, stats in sorted(types_stats.items()):
                                    export_message += f"\n• {item_type}: {stats['count']} шт ({stats['sum']:,.0f} ₽)"
                            
                            sync_send_message(export_message)
                            
                            # Синхронизация с Google Sheets
                            try:
                                logger.info("🔄 Запуск синхронизации с Google Sheets...")
                                from sheets_sync import sync_to_sheets
                                
                                if sync_to_sheets(json_file):
                                    logger.info("✅ Синхронизация с Google Sheets завершена")
                                else:
                                    logger.warning("⚠️ Синхронизация не удалась")
                                    
                            except Exception as e:
                                logger.error(f"❌ Ошибка синхронизации с Google Sheets: {e}")
                                sync_send_message(f"⚠️ Ошибка синхронизации: {e}")
                            
                        except Exception as e:
                            logger.error(f"❌ Ошибка при экспорте данных: {e}")
                            sync_send_message(f"⚠️ Ошибка при экспорте данных: {e}")

                
                # Ждем перед закрытием для просмотра результата
                logger.info("Ожидание перед закрытием браузера...")
                if page:
                    page.wait_for_timeout(5000)
                
                # ВАЖНО: Сохраняем обновлённые cookies перед закрытием
                # Это позволяет использовать актуальные токены при следующем запуске
                if session_manager.cookies_exist():
                    logger.info("💾 Сохраняем обновлённые cookies после парсинга...")
                    if session_manager.save_cookies_from_context(context):
                        logger.success("✅ Cookies обновлены и сохранены")
                    else:
                        logger.warning("⚠️ Не удалось сохранить обновлённые cookies")
                
            finally:
                # Закрываем браузер
                logger.info("Закрытие браузера...")
                try:
                    context.close()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии context: {e}")
                try:
                    browser.close()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии browser: {e}")
                
                # Принудительно завершаем все процессы playwright
                try:
                    p.stop()
                    logger.info("✅ Playwright остановлен")
                except Exception as e:
                    logger.warning(f"Ошибка при остановке playwright: {e}")
        
            logger.info("Работа завершена успешно")
            sync_send_message("✅ <b>Работа завершена</b>")
            
            # Явно завершаем программу, чтобы избежать зависания
            # Используем os._exit(0) вместо sys.exit(0), чтобы избежать
            # блокировки на p.__exit__() в блоке with sync_playwright()
            logger.info("🏁 Принудительное завершение процесса...")
            os._exit(0)  # Немедленное завершение без cleanup handlers
    
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
    
    finally:
        # Удаляем lock файл при любом завершении
        try:
            if lock_file is not None:
                lock_file.close()
            if lock_file_path.exists():
                lock_file_path.unlink()
                logger.info("🔓 Lock файл удалён")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить lock файл: {e}")


if __name__ == '__main__':
    main()
