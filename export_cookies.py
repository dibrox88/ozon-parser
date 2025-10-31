"""
Скрипт для экспорта cookies из браузера с ручной авторизацией

Запуск: python export_cookies.py
"""

from playwright.sync_api import sync_playwright
import json
from loguru import logger
import time

def export_cookies():
    """Экспорт cookies после ручной авторизации"""
    
    logger.info("=" * 70)
    logger.info("🍪 ЭКСПОРТ COOKIES ИЗ БРАУЗЕРА")
    logger.info("=" * 70)
    
    with sync_playwright() as p:
        # Запускаем браузер В ВИДИМОМ РЕЖИМЕ
        logger.info("🌐 Запускаем браузер (будет видимое окно)...")
        browser = p.chromium.launch(
            headless=False,  # ВИДИМЫЙ режим
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
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
        
        logger.info("📍 Открываем Ozon...")
        page.goto('https://www.ozon.ru/')
        
        logger.info("=" * 70)
        logger.warning("⚠️  ДЕЙСТВИЯ ТРЕБУЮТСЯ:")
        logger.warning("")
        logger.warning("1. В открывшемся браузере АВТОРИЗУЙТЕСЬ на Ozon")
        logger.warning("2. Введите логин/пароль")
        logger.warning("3. Введите код из SMS/email")
        logger.warning("4. Дождитесь загрузки главной страницы")
        logger.warning("5. Нажмите Enter в ЭТОМ ОКНЕ терминала")
        logger.warning("")
        logger.info("=" * 70)
        
        # Ждем пока пользователь авторизуется
        input("\n👉 Нажмите Enter после авторизации... ")
        
        logger.info("🔄 Проверяем авторизацию...")
        
        # Проверяем что пользователь авторизован
        current_url = page.url
        logger.info(f"📍 Текущий URL: {current_url}")
        
        # Экспортируем cookies
        cookies = context.cookies()
        
        if not cookies:
            logger.error("❌ Cookies не найдены! Возможно авторизация не прошла.")
            browser.close()
            return False
        
        logger.info(f"📦 Получено {len(cookies)} cookies из браузера")
        
        # Удаляем дубликаты - оставляем последнюю (самую свежую) версию каждой cookie
        # Ключ: только имя cookie (игнорируем домен/путь)
        unique_cookies = {}
        for cookie in cookies:
            name = cookie.get('name', '')
            expires = cookie.get('expires', -1)
            
            # Если такая cookie уже есть, сравниваем expires
            if name in unique_cookies:
                existing_expires = unique_cookies[name].get('expires', -1)
                # Оставляем ту, что истекает позже (более свежая)
                if expires > existing_expires:
                    unique_cookies[name] = cookie
            else:
                unique_cookies[name] = cookie
        
        cookies = list(unique_cookies.values())
        logger.success(f"✅ Уникальных cookies: {len(cookies)}")
        
        # Проверяем наличие важных cookies
        important_cookies = ['__Secure-access-token', '__Secure-refresh-token', 'xcid']
        found_important = [c['name'] for c in cookies if c['name'] in important_cookies]
        
        if found_important:
            logger.success(f"✅ Найдены важные cookies: {', '.join(found_important)}")
        else:
            logger.warning("⚠️  Важные cookies не найдены. Возможно авторизация не завершена.")
            logger.warning("   Попробуйте ещё раз и убедитесь что вы вошли в аккаунт.")
        
        # Сохраняем cookies в файл
        cookies_file = 'ozon_cookies.json'
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        logger.success(f"✅ Cookies сохранены в: {cookies_file}")
        
        # Также сохраним в формате для curl/wget
        with open('ozon_cookies.txt', 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for cookie in cookies:
                domain = cookie.get('domain', '')
                flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                expiry = int(cookie.get('expires', -1))
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        
        logger.success("✅ Cookies также сохранены в формате Netscape: ozon_cookies.txt")
        
        logger.info("=" * 70)
        logger.success("🎉 ГОТОВО!")
        logger.info("")
        logger.info("Теперь можете запустить парсер: python main.py")
        logger.info("Он будет использовать сохраненные cookies вместо браузерной авторизации")
        logger.info("=" * 70)
        
        time.sleep(2)
        browser.close()
        
        return True

if __name__ == "__main__":
    try:
        success = export_cookies()
        if success:
            logger.info("✅ Экспорт завершен успешно")
        else:
            logger.error("❌ Экспорт не удался")
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Отменено пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
