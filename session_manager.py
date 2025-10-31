"""Модуль управления сессиями браузера."""
import os
import json
from pathlib import Path
from typing import Optional
from playwright.sync_api import Browser, BrowserContext
from loguru import logger
from config import Config


class SessionManager:
    """Класс для управления сохранением и загрузкой сессий браузера."""
    
    def __init__(self):
        """Инициализация."""
        self.state_dir = Path(Config.BROWSER_STATE_DIR)
        self.state_file = self.state_dir / "ozon_session.json"
        # Ищем cookies сначала в /data (постоянное хранилище Amvera), потом в текущей папке
        if Path("/data/ozon_cookies.json").exists():
            self.cookies_file = Path("/data/ozon_cookies.json")
        else:
            self.cookies_file = Path("ozon_cookies.json")
        
        # Создаем директорию если её нет
        self.state_dir.mkdir(exist_ok=True)
        logger.info(f"Директория сессий: {self.state_dir.absolute()}")
        logger.info(f"Файл cookies: {self.cookies_file.absolute()}")
    
    def cookies_exist(self) -> bool:
        """
        Проверить наличие экспортированных cookies.
        
        Returns:
            True если cookies файл существует
        """
        exists = self.cookies_file.exists()
        if exists:
            logger.info(f"✅ Найдены экспортированные cookies: {self.cookies_file}")
        return exists
    
    def load_cookies_to_context(self, context: BrowserContext) -> bool:
        """
        Загрузить cookies из JSON файла в контекст браузера.
        
        Args:
            context: Контекст браузера Playwright
            
        Returns:
            True если cookies успешно загружены
        """
        try:
            if not self.cookies_exist():
                return False
            
            logger.info("🍪 Загружаем экспортированные cookies...")
            
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if not cookies:
                logger.error("❌ Cookies файл пустой")
                return False
            
            # Добавляем cookies в контекст
            context.add_cookies(cookies)
            
            logger.success(f"✅ Загружено {len(cookies)} cookies")
            
            # Проверяем важные cookies
            important = ['__Secure-access-token', '__Secure-refresh-token', 'xcid']
            cookie_names = [c['name'] for c in cookies]
            found_important = [name for name in important if name in cookie_names]
            
            if found_important:
                logger.success(f"✅ Найдены токены авторизации: {', '.join(found_important)}")
                return True
            else:
                logger.warning("⚠️ Важные cookies не найдены, авторизация может не работать")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки cookies: {e}")
            return False
    
    def session_exists(self) -> bool:
        """
        Проверить наличие сохраненной сессии.
        
        Returns:
            True если сессия существует
        """
        exists = self.state_file.exists()
        if exists:
            logger.info(f"Найдена сохраненная сессия: {self.state_file}")
        else:
            logger.info("Сохраненная сессия не найдена")
        return exists
    
    def load_session(self, browser: Browser) -> Optional[BrowserContext]:
        """
        Загрузить сохраненную сессию.
        
        Args:
            browser: Браузер Playwright
            
        Returns:
            Контекст браузера с загруженной сессией или None
        """
        try:
            if not self.session_exists():
                logger.info("Нет сохраненной сессии для загрузки")
                return None
            
            logger.info("Загружаем сохраненную сессию...")
            
            # Загружаем контекст из файла
            context = browser.new_context(
                storage_state=str(self.state_file),
                viewport={'width': 1920, 'height': 1080},
                user_agent=Config.USER_AGENT,
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                geolocation={'longitude': 37.6173, 'latitude': 55.7558},
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                }
            )
            
            # Добавляем stealth скрипты
            self._add_stealth_scripts(context)
            
            logger.info("✅ Сессия успешно загружена")
            return context
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке сессии: {e}")
            return None
    
    def save_session(self, context: BrowserContext) -> bool:
        """
        Сохранить текущую сессию.
        
        Args:
            context: Контекст браузера
            
        Returns:
            True если успешно
        """
        try:
            logger.info("Сохраняем сессию...")
            
            # Сохраняем состояние (cookies, localStorage, sessionStorage)
            context.storage_state(path=str(self.state_file))
            
            logger.info(f"✅ Сессия сохранена: {self.state_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении сессии: {e}")
            return False
    
    def delete_session(self) -> bool:
        """
        Удалить сохраненную сессию.
        
        Returns:
            True если успешно
        """
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                logger.info("✅ Сессия удалена")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении сессии: {e}")
            return False
    
    def _add_stealth_scripts(self, context: BrowserContext):
        """
        Добавить stealth скрипты в контекст.
        
        Args:
            context: Контекст браузера
        """
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
