"""
Тестовый скрипт для проверки обхода anti-bot защиты Ozon
с использованием undetected-chromedriver
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from loguru import logger

def human_delay(min_sec=2.0, max_sec=5.0):
    """Случайная задержка"""
    delay = random.uniform(min_sec, max_sec)
    logger.info(f"⏱️ Задержка: {delay:.2f}с")
    time.sleep(delay)

def test_ozon_access():
    """Тест доступа к Ozon"""
    
    logger.info("=" * 60)
    logger.info("🚀 ТЕСТ UNDETECTED-CHROMEDRIVER")
    logger.info("=" * 60)
    
    # Настройки Chrome
    options = uc.ChromeOptions()
    
    # Добавляем аргументы
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    
    # Создаем драйвер (undetected автоматически обходит детект)
    logger.info("🌐 Запускаем браузер...")
    driver = uc.Chrome(options=options, version_main=141)
    
    try:
        # Устанавливаем User-Agent
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        logger.info("📍 Переходим на Ozon...")
        driver.get('https://www.ozon.ru/')
        
        human_delay(3, 6)
        
        # Проверяем что загрузилось
        current_url = driver.current_url
        page_title = driver.title
        page_source = driver.page_source[:1000]
        
        logger.info(f"✅ URL: {current_url}")
        logger.info(f"✅ Title: {page_title}")
        
        # Проверяем на блокировку
        if "captcha" in current_url.lower() or "captcha" in page_source.lower():
            logger.error("❌ ОБНАРУЖЕНА КАПЧА!")
            driver.save_screenshot('screenshots/captcha_detected.png')
        elif "access" in current_url.lower() or "denied" in page_source.lower():
            logger.error("❌ ДОСТУП ЗАПРЕЩЕН!")
            driver.save_screenshot('screenshots/access_denied.png')
        elif "cloudflare" in page_source.lower():
            logger.error("❌ CLOUDFLARE ЗАЩИТА!")
            driver.save_screenshot('screenshots/cloudflare.png')
        elif "ozon.ru" in current_url:
            logger.success("✅ СТРАНИЦА ЗАГРУЖЕНА УСПЕШНО!")
            driver.save_screenshot('screenshots/success_load.png')
            
            # Пробуем найти кнопку "Войти"
            try:
                human_delay(2, 4)
                login_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Войти') or contains(., 'войти')]"))
                )
                logger.success("✅ Кнопка 'Войти' найдена!")
                logger.info("🎉 ДОСТУП К OZON ПОЛУЧЕН! Anti-bot обойден!")
            except Exception as e:
                logger.warning(f"⚠️ Кнопка 'Войти' не найдена (возможно другой лейаут): {e}")
        else:
            logger.warning(f"⚠️ Неожиданный URL: {current_url}")
            driver.save_screenshot('screenshots/unexpected.png')
        
        # Ждем немного чтобы посмотреть результат
        logger.info("⏳ Держим браузер открытым 10 секунд для проверки...")
        time.sleep(10)
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        driver.save_screenshot('screenshots/error.png')
    
    finally:
        logger.info("🔚 Закрываем браузер...")
        driver.quit()

if __name__ == "__main__":
    test_ozon_access()
