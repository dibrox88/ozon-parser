"""
Упрощённая версия main.py - ТОЧНАЯ копия логики test_no_cookies.py.
БЕЗ лишних библиотек, БЕЗ сложной авторизации.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from loguru import logger
import fcntl  # Для блокировки файла (Unix)
import time
import os

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


def main():
    """Главная функция - упрощённая версия."""
    # Путь к файлу-флагу блокировки
    lock_file_path = Path("logs/parser_simple.lock")
    lock_file_path.parent.mkdir(exist_ok=True)
    
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
                        sync_send_message("⚠️ <b>Парсер уже запущен</b>\n\nДождитесь завершения текущего процесса")
                        sys.exit(0)
                    else:
                        logger.warning(f"⚠️ Найден устаревший lock файл (возраст: {lock_age/60:.1f} мин). Удаляем...")
                        lock_file_path.unlink()
            
            # Записываем PID в lock файл
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            
            logger.info(f"� Lock файл создан: {lock_file_path}")
            
        except (IOError, OSError) as e:
            logger.warning(f"⚠️ Парсер уже запущен! Lock файл заблокирован: {e}")
            sync_send_message("⚠️ <b>Парсер уже запущен</b>\n\nДождитесь завершения текущего процесса")
            lock_file.close()
            sys.exit(0)
        
        # Основная логика парсера
        logger.info("�🚀 Запуск Ozon Parser (Strategy #3: Desktop with Linux UA)")
        sync_send_message("🚀 <b>Ozon Parser запущен</b>\n\n🖥️ Strategy #3: Desktop Linux 1920x1080...")
        
        with sync_playwright() as p:
            # Strategy #3: Desktop with Linux UA (ПРОТЕСТИРОВАНО - РАБОТАЕТ!)
            browser = p.chromium.launch(
                headless=Config.HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
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
            page.set_default_timeout(Config.DEFAULT_TIMEOUT)
            page.set_default_navigation_timeout(Config.NAVIGATION_TIMEOUT)
            
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
                sync_send_message("❌ <b>Блокировка обнаружена</b>\n\nНеобходим residential proxy")
                browser.close()
                sys.exit(1)
            
            logger.success("✅ Главная страница открылась БЕЗ блокировки!")
            sync_send_message("✅ <b>Главная страница OK</b>\n\nПереходим к заказам...")
            
            # 2. Переходим к заказам
            logger.info("📍 Переходим к 'Мои заказы'...")
            page.goto("https://www.ozon.ru/my/orderlist", timeout=30000)
            page.wait_for_timeout(3000)
            
            title2 = page.title()
            logger.info(f"Title: {title2}")
            
            content2 = page.content()
            if "Доступ ограничен" in content2:
                logger.error("❌ БЛОКИРОВКА на странице заказов!")
                sync_send_message("❌ <b>Блокировка на заказах</b>\n\nНеобходим residential proxy")
                browser.close()
                sys.exit(1)
            
            # 3. Проверяем нужна ли авторизация
            if "Войти" in content2 or "Войдите" in content2:
                logger.info("ℹ️ Требуется авторизация")
                sync_send_message("ℹ️ <b>Требуется авторизация</b>\n\nЗапускаем вход через email...")
                
                # Используем OzonAuth для авторизации
                auth = OzonAuth(page)
                if not auth.login():
                    logger.error("❌ Авторизация не удалась")
                    sync_send_message("❌ <b>Ошибка авторизации</b>\n\nПроверьте OZON_EMAIL и OZON_PASSWORD в .env")
                    browser.close()
                    sys.exit(1)
                
                logger.success("✅ Авторизация успешна!")
                sync_send_message("✅ <b>Авторизация успешна!</b>\n\nПереходим к парсингу...")
                
                # После успешной авторизации переходим к заказам
                page.goto("https://www.ozon.ru/my/orderlist", timeout=30000)
                page.wait_for_timeout(3000)
            
            # 4. Запускаем парсер
            logger.success("✅ Доступ к заказам получен!")
            sync_send_message("✅ <b>Доступ к заказам</b>\n\nЗапускаем парсер...")
            
            parser = OzonParser(page)
            orders = parser.parse_orders()
            
            if orders:
                logger.success(f"✅ Парсинг завершён! Найдено заказов: {len(orders)}")
                sync_send_message(f"✅ <b>Парсинг завершён!</b>\n\n📦 Заказов: {len(orders)}")
            else:
                logger.warning("⚠️ Заказы не найдены")
                sync_send_message("⚠️ Заказы не найдены")
            
            browser.close()
    
    except KeyboardInterrupt:
        logger.info("❌ Прервано пользователем")
        sync_send_message("❌ Парсинг прерван пользователем")
        sys.exit(0)
        
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
        sync_send_message(f"❌ <b>Критическая ошибка:</b>\n\n{str(e)}")
        sys.exit(1)
    
    finally:
        # Удаляем lock файл при любом завершении
        try:
            if 'lock_file' in locals():
                lock_file.close()
            if lock_file_path.exists():
                lock_file_path.unlink()
                logger.info("🔓 Lock файл удалён")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить lock файл: {e}")


if __name__ == "__main__":
    main()
