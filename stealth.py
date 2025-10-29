"""Модуль для защиты от детектирования автоматизации."""
import time
import random
from typing import Optional
from playwright.sync_api import Page
from loguru import logger


class StealthHelper:
    """Помощник для скрытной автоматизации."""
    
    @staticmethod
    def human_delay(min_sec: float = 1.0, max_sec: float = 3.0):
        """
        Случайная задержка, имитирующая человека.
        
        Args:
            min_sec: Минимальная задержка в секундах
            max_sec: Максимальная задержка в секундах
        """
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        logger.debug(f"Задержка: {delay:.2f}с")
    
    @staticmethod
    def human_type(page: Page, selector: str, text: str, delay_ms: Optional[int] = None):
        """
        Печатать как человек с случайными задержками между символами.
        
        Args:
            page: Страница Playwright
            selector: CSS селектор элемента
            text: Текст для ввода
            delay_ms: Задержка между символами (по умолчанию случайная 50-150ms)
        """
        try:
            element = page.wait_for_selector(selector, state='visible', timeout=10000)
            element.click()
            
            # Очищаем поле
            element.evaluate('el => el.value = ""')
            
            # Печатаем посимвольно
            for char in text:
                element.type(char, delay=delay_ms or random.randint(50, 150))
                
            logger.debug(f"Введен текст в {selector}")
            
        except Exception as e:
            logger.error(f"Ошибка при вводе текста: {e}")
            raise
    
    @staticmethod
    def human_click(page: Page, selector: str):
        """
        Кликнуть как человек (с небольшим движением мыши).
        
        Args:
            page: Страница Playwright
            selector: CSS селектор элемента
        """
        try:
            element = page.wait_for_selector(selector, state='visible', timeout=10000)
            
            # Получаем координаты элемента
            box = element.bounding_box()
            if not box:
                element.click()
                return
            
            # Добавляем случайное смещение внутри элемента
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Двигаем мышь к элементу
            page.mouse.move(x, y)
            StealthHelper.human_delay(0.1, 0.3)
            
            # Кликаем
            page.mouse.click(x, y)
            
            logger.debug(f"Кликнули на {selector}")
            
        except Exception as e:
            logger.error(f"Ошибка при клике: {e}")
            raise
    
    @staticmethod
    def random_mouse_movement(page: Page, num_moves: int = 3):
        """
        Случайные движения мыши для имитации живого пользователя.
        
        Args:
            page: Страница Playwright
            num_moves: Количество движений
        """
        try:
            viewport = page.viewport_size
            if not viewport:
                return
            
            for _ in range(num_moves):
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                
                # Плавное движение
                page.mouse.move(x, y)
                StealthHelper.human_delay(0.2, 0.5)
                
        except Exception as e:
            logger.debug(f"Не удалось выполнить движения мыши: {e}")
    
    @staticmethod
    def random_scroll(page: Page, direction: str = 'down', amount: Optional[int] = None):
        """
        Случайная прокрутка страницы.
        
        Args:
            page: Страница Playwright
            direction: Направление ('up' или 'down')
            amount: Количество пикселей (по умолчанию случайное)
        """
        try:
            if amount is None:
                amount = random.randint(300, 800)
            
            if direction == 'down':
                page.evaluate(f'window.scrollBy(0, {amount})')
            else:
                page.evaluate(f'window.scrollBy(0, -{amount})')
            
            StealthHelper.human_delay(0.3, 0.8)
            
        except Exception as e:
            logger.debug(f"Не удалось прокрутить страницу: {e}")
    
    @staticmethod
    def wait_for_stable_network(page: Page, timeout: int = 10000):
        """
        Подождать пока сеть успокоится (нет активных запросов).
        
        Args:
            page: Страница Playwright
            timeout: Таймаут в миллисекундах
        """
        try:
            page.wait_for_load_state('networkidle', timeout=timeout)
            StealthHelper.human_delay(0.5, 1.5)
        except Exception as e:
            logger.debug(f"Таймаут ожидания сети: {e}")
            StealthHelper.human_delay(1, 2)
    
    @staticmethod
    def check_for_captcha(page: Page) -> bool:
        """
        Проверить наличие капчи на странице.
        
        Args:
            page: Страница Playwright
            
        Returns:
            True если капча найдена
        """
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="captcha"]',
            'div[class*="captcha"]',
            'div[id*="captcha"]',
            '#challenge-form',
            '.cf-browser-verification',
            '[data-captcha]'
        ]
        
        for selector in captcha_selectors:
            try:
                if page.query_selector(selector):
                    logger.warning(f"Обнаружена капча: {selector}")
                    return True
            except:
                pass
        
        return False
    
    @staticmethod
    def check_for_block(page: Page) -> bool:
        """
        Проверить блокировку доступа.
        
        Args:
            page: Страница Playwright
            
        Returns:
            True если страница заблокирована
        """
        block_indicators = [
            'Access Denied',
            'Доступ запрещен',
            'Blocked',
            'Заблокирован',
            'Security check',
            'Проверка безопасности',
            'Your request has been blocked',
            'Ваш запрос заблокирован'
        ]
        
        try:
            content = page.content().lower()
            
            for indicator in block_indicators:
                if indicator.lower() in content:
                    logger.error(f"Обнаружена блокировка: {indicator}")
                    return True
        except:
            pass
        
        return False
