"""
Модуль с различными стратегиями обхода защиты от ботов.
Тестируем разные комбинации настроек для обхода блокировок Ozon.
"""
import random
from typing import List, Tuple, Optional
from playwright.sync_api import Browser, BrowserContext
from loguru import logger


class AntidetectStrategy:
    """Базовый класс для стратегии обхода детектирования."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def apply(self, browser: Browser) -> BrowserContext:
        """Применить стратегию и создать контекст браузера."""
        raise NotImplementedError
    
    def __str__(self):
        return f"{self.name}: {self.description}"


class Strategy1_BasicStealth(AntidetectStrategy):
    """Базовая stealth-стратегия с минимальными изменениями."""
    
    def __init__(self):
        super().__init__(
            "Basic Stealth",
            "Базовый stealth: убираем webdriver, добавляем плагины"
        )
    
    def apply(self, browser: Browser) -> BrowserContext:
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        return context


class Strategy2_GithubParser(AntidetectStrategy):
    """Стратегия из успешного GitHub репозитория aglihowstan/parser_ozon."""
    
    def __init__(self):
        super().__init__(
            "GitHub Parser",
            "Настройки из проверенного парсера (ignore_https_errors, java_script)"
        )
    
    def apply(self, browser: Browser) -> BrowserContext:
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            java_script_enabled=True,
            ignore_https_errors=True
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        return context


class Strategy3_FullStealth(AntidetectStrategy):
    """Полный набор stealth техник."""
    
    def __init__(self):
        super().__init__(
            "Full Stealth",
            "Максимальный набор: webdriver, plugins, permissions, chrome runtime"
        )
    
    def apply(self, browser: Browser) -> BrowserContext:
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            has_touch=False,
            is_mobile=False,
            device_scale_factor=1,
        )
        
        context.add_init_script("""
            // Убираем webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Плагины
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
            
            // Platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // Hardware
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
        """)
        
        return context


class Strategy4_RandomFingerprint(AntidetectStrategy):
    """Случайные отпечатки браузера."""
    
    def __init__(self):
        super().__init__(
            "Random Fingerprint",
            "Случайный user-agent и разрешение экрана"
        )
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self.viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
        ]
    
    def apply(self, browser: Browser) -> BrowserContext:
        user_agent = random.choice(self.user_agents)
        viewport = random.choice(self.viewports)
        
        logger.info(f"🎲 Случайный UA: {user_agent[:50]}...")
        logger.info(f"🎲 Разрешение: {viewport['width']}x{viewport['height']}")
        
        context = browser.new_context(
            viewport={'width': viewport['width'], 'height': viewport['height']},
            user_agent=user_agent,
            locale='ru-RU',
            timezone_id='Europe/Moscow',
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        return context


class Strategy5_MobileEmulation(AntidetectStrategy):
    """Эмуляция мобильного устройства."""
    
    def __init__(self):
        super().__init__(
            "Mobile Emulation",
            "Притворяемся мобильным телефоном (Android)"
        )
    
    def apply(self, browser: Browser) -> BrowserContext:
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
        
        return context


class Strategy6_ExtendedHeaders(AntidetectStrategy):
    """Расширенные HTTP заголовки."""
    
    def __init__(self):
        super().__init__(
            "Extended Headers",
            "Дополнительные HTTP заголовки (sec-ch-ua, Accept-Language)"
        )
    
    def apply(self, browser: Browser) -> BrowserContext:
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)
        
        return context


class Strategy7_CanvasProtection(AntidetectStrategy):
    """Защита от Canvas fingerprinting."""
    
    def __init__(self):
        super().__init__(
            "Canvas Protection",
            "Защита от Canvas и WebGL fingerprinting"
        )
    
    def apply(self, browser: Browser) -> BrowserContext:
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
        )
        
        context.add_init_script("""
            // Базовый stealth
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Canvas fingerprint protection
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                const context = this.getContext('2d');
                const imageData = context.getImageData(0, 0, this.width, this.height);
                
                // Добавляем минимальный шум
                for (let i = 0; i < imageData.data.length; i += 4) {
                    if (Math.random() < 0.01) {
                        imageData.data[i] = imageData.data[i] ^ 1;
                    }
                }
                
                context.putImageData(imageData, 0, 0);
                return originalToDataURL.call(this, type);
            };
            
            // WebGL fingerprint protection
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel(R) UHD Graphics 620';
                }
                return getParameter.call(this, parameter);
            };
        """)
        
        return context


class StrategyTester:
    """Класс для тестирования стратегий обхода блокировок."""
    
    def __init__(self):
        self.strategies: List[AntidetectStrategy] = [
            Strategy1_BasicStealth(),
            Strategy2_GithubParser(),
            Strategy3_FullStealth(),
            Strategy4_RandomFingerprint(),
            Strategy5_MobileEmulation(),
            Strategy6_ExtendedHeaders(),
            Strategy7_CanvasProtection(),
        ]
    
    def get_all_strategies(self) -> List[AntidetectStrategy]:
        """Получить список всех стратегий."""
        return self.strategies
    
    def get_strategy_by_index(self, index: int) -> Optional[AntidetectStrategy]:
        """Получить стратегию по индексу (1-based)."""
        if 1 <= index <= len(self.strategies):
            return self.strategies[index - 1]
        return None
    
    def get_strategy_names(self) -> List[str]:
        """Получить названия всех стратегий."""
        return [f"{i+1}. {s.name}" for i, s in enumerate(self.strategies)]
    
    def test_strategy(
        self,
        browser: Browser,
        strategy: AntidetectStrategy,
        test_url: str = "https://www.ozon.ru"
    ) -> Tuple[bool, str, Optional[bytes]]:
        """
        Тестировать стратегию.
        
        Args:
            browser: Браузер Playwright
            strategy: Стратегия для тестирования
            test_url: URL для теста
            
        Returns:
            (успех, сообщение, скриншот_bytes)
        """
        logger.info(f"🧪 Тестируем стратегию: {strategy.name}")
        
        context = None
        screenshot = None
        
        try:
            # Применяем стратегию
            context = strategy.apply(browser)
            page = context.new_page()
            
            # Переходим на страницу
            logger.info(f"Переход на {test_url}...")
            page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)  # Ждем 3 секунды
            
            # Делаем скриншот
            screenshot = page.screenshot(full_page=False)
            logger.info("Скриншот сделан")
            
            # Проверяем блокировку
            title = page.title()
            content = page.content()
            
            # Индикаторы блокировки
            is_blocked = False
            block_reason = ""
            
            if "Доступ ограничен" in content or "Access Denied" in content:
                is_blocked = True
                block_reason = "❌ Блокировка: 'Доступ ограничен'"
            elif "Проверка безопасности" in content or "Security check" in content:
                is_blocked = True
                block_reason = "❌ Блокировка: 'Проверка безопасности'"
            elif "Captcha" in content or "captcha" in content:
                is_blocked = True
                block_reason = "❌ Обнаружена CAPTCHA"
            elif "Ozon" not in title and "ozon" not in content.lower():
                is_blocked = True
                block_reason = f"❌ Неожиданная страница (title: {title[:50]})"
            
            if is_blocked:
                logger.warning(f"❌ Стратегия '{strategy.name}' не прошла: {block_reason}")
                return False, block_reason, screenshot
            else:
                success_msg = f"✅ Успех! Title: {title[:100]}"
                logger.success(f"✅ Стратегия '{strategy.name}' успешна!")
                return True, success_msg, screenshot
                
        except Exception as e:
            error_msg = f"❌ Ошибка: {str(e)[:200]}"
            logger.error(f"❌ Ошибка при тестировании стратегии '{strategy.name}': {e}")
            return False, error_msg, screenshot
        
        finally:
            # Закрываем контекст
            if context:
                try:
                    context.close()
                except:
                    pass
