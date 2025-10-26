"""Модуль авторизации на Ozon."""
import os
import time
import base64
import re
from pathlib import Path
from typing import Optional
from playwright.sync_api import Page, Browser, sync_playwright, TimeoutError as PlaywrightTimeout
from loguru import logger
from config import Config
from notifier import sync_send_message, sync_send_photo, sync_wait_for_input

try:
    from PIL import Image
    import cv2
    import numpy as np
    from pyzbar.pyzbar import decode as qr_decode
    QR_DECODE_AVAILABLE = True
except ImportError:
    logger.warning("Библиотеки для декодирования QR-кода не установлены (pyzbar, opencv-python)")
    QR_DECODE_AVAILABLE = False


class OzonAuth:
    """Класс для авторизации на Ozon."""
    
    def __init__(self, page: Page):
        """
        Инициализация.
        
        Args:
            page: Страница Playwright
        """
        self.page = page
        self.config = Config()
        
        # Создаем директорию для скриншотов
        Path(Config.SCREENSHOTS_DIR).mkdir(exist_ok=True)
    
    def _decode_qr_from_base64(self, base64_data: str) -> Optional[str]:
        """
        Декодировать QR-код из base64 изображения.
        
        Args:
            base64_data: Данные изображения в base64
            
        Returns:
            Декодированная ссылка из QR-кода или None
        """
        if not QR_DECODE_AVAILABLE:
            logger.warning("Декодирование QR-кода недоступно - библиотеки не установлены")
            return None
        
        try:
            # Импортируем библиотеки внутри функции
            import numpy as np
            import cv2
            from pyzbar.pyzbar import decode as qr_decode
            
            # Убираем префикс data:image/png;base64,
            if 'base64,' in base64_data:
                base64_data = base64_data.split('base64,')[1]
            
            # Декодируем base64
            img_data = base64.b64decode(base64_data)
            
            # Конвертируем в numpy array
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Не удалось декодировать изображение")
                return None
            
            # Декодируем QR-код
            decoded_objects = qr_decode(img)
            
            if decoded_objects:
                qr_data = decoded_objects[0].data.decode('utf-8')
                logger.info(f"✅ QR-код декодирован: {qr_data[:100]}...")
                return qr_data
            else:
                logger.warning("QR-код не найден на изображении")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при декодировании QR-кода: {e}")
            return None
    
    def _take_screenshot(self, name: str) -> str:
        """
        Сделать скриншот.
        
        Args:
            name: Имя файла
            
        Returns:
            Путь к скриншоту
        """
        try:
            timestamp = int(time.time())
            filename = f"{Config.SCREENSHOTS_DIR}/{name}_{timestamp}.png"
            # Уменьшаем таймаут до 10 секунд
            self.page.screenshot(path=filename, full_page=True, timeout=10000)
            logger.info(f"Скриншот сохранен: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Ошибка при создании скриншота '{name}': {e}")
            # Возвращаем пустой путь, но не ломаем процесс
            return ""
    
    def open_login_page(self) -> bool:
        """
        Открыть страницу входа.
        
        Returns:
            True если успешно
        """
        try:
            logger.info("Открываем главную страницу Ozon")
            self.page.goto(Config.OZON_LOGIN_URL, timeout=Config.NAVIGATION_TIMEOUT)
            
            # Ждем загрузки страницы
            self.page.wait_for_load_state('networkidle', timeout=Config.DEFAULT_TIMEOUT)
            time.sleep(2)
            
            # Делаем скриншот
            #screenshot = self._take_screenshot('main_page')
            #sync_send_photo(screenshot, "Главная страница Ozon открыта")
            
            return True
            
        except PlaywrightTimeout as e:
            logger.error(f"Таймаут при открытии страницы: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при открытии страницы: {e}")
            return False
    
    def click_login_button(self) -> bool:
        """
        Нажать на кнопку входа.
        
        Returns:
            True если успешно
        """
        try:
            logger.info("Ищем кнопку входа")
            
            # Возможные селекторы кнопки входа
            selectors = [
                'span.tsCompact300XSmall:has-text("Войти")',  # Новый селектор Ozon 2025
                'text="Войти"',
                'button:has-text("Войти")',
                'a:has-text("Войти")',
                'span:has-text("Войти")',  # Любой span с текстом Войти
                '[class*="Compact"]:has-text("Войти")',  # Любой класс содержащий Compact
            ]
            
            logger.info(f"Пробуем {len(selectors)} селекторов для кнопки входа")
            
            # Увеличиваем таймаут и пробуем все селекторы
            for idx, selector in enumerate(selectors, 1):
                try:
                    logger.info(f"Попытка {idx}/{len(selectors)}: {selector}")
                    element = self.page.wait_for_selector(selector, timeout=8000, state='visible')
                    if element and element.is_visible():
                        logger.info(f"✅ Найдена кнопка входа: {selector}")
                        
                        # Делаем скриншот перед кликом
                        screenshot = self._take_screenshot('before_login_click')
                        if screenshot:
                            pass  # sync_send_photo(screenshot, f"Найдена кнопка входа: {selector}")
                        
                        # Кликаем и ждем появления модального окна или iframe
                        element.click()
                        logger.info(f"✅ Кликнули на кнопку входа: {selector}")
                        
                        # Ждем появления iframe или модального окна
                        time.sleep(3)
                        
                        # Проверяем iframe
                        iframes = self.page.frames
                        logger.info(f"После клика найдено {len(iframes)} фреймов")
                        
                        # Ждем загрузки модального окна
                        try:
                            # Пробуем найти поле ввода (телефон или email)
                            self.page.wait_for_selector('input[type="tel"]', 
                                                       timeout=5000, state='visible')
                            logger.info("✅ Модальное окно загружено, найдено поле ввода")
                        except:
                            logger.warning("Поле ввода не найдено сразу, возможно в iframe")
 
                        return True
                except PlaywrightTimeout:
                    logger.warning(f"⏱️ Таймаут для селектора {idx}/{len(selectors)}: {selector}")
                    continue
                except Exception as e:
                    logger.error(f"❌ Ошибка при попытке селектора {idx}/{len(selectors)} ({selector}): {e}")
                    continue
            
            # Если ни один селектор не сработал - делаем скриншот и логируем все элементы
            logger.error("❌ Кнопка входа НЕ НАЙДЕНА ни одним селектором!")
            screenshot = self._take_screenshot('login_button_not_found')
            
            # Логируем все элементы с текстом "Войти"
            try:
                logger.info("Ищем ВСЕ элементы с текстом 'Войти' на странице:")
                all_login_elements = self.page.query_selector_all('*')
                found_count = 0
                for elem in all_login_elements:
                    try:
                        text = elem.inner_text() if elem.inner_text() else ""
                        if 'войти' in text.lower() and len(text) < 50:
                            tag = elem.evaluate("el => el.tagName")
                            classes = elem.get_attribute('class') or 'no-class'
                            logger.info(f"  Найден: <{tag} class='{classes[:80]}'>: '{text}'")
                            found_count += 1
                            if found_count >= 10:
                                break
                    except:
                        pass
                logger.info(f"Всего найдено элементов с 'Войти': {found_count}")
            except Exception as e:
                logger.error(f"Ошибка при поиске элементов: {e}")
            
            if screenshot:
                sync_send_photo(screenshot, "❌ Кнопка входа не найдена автоматически")
            
            logger.warning("Кнопка входа не найдена автоматически")
            
            
            response = sync_wait_for_input("Нажмите 'Войти' вручную (если нужно) и отправьте сообщение", timeout=60)
            if response:
                time.sleep(2)
                return True
            
            return True  # Продолжаем в любом случае
            
        except Exception as e:
            logger.error(f"Ошибка при нажатии кнопки входа: {e}")
            # Пробуем продолжить, может уже на форме входа
            return True
    
    def click_email_login_button(self) -> bool:
        """
        Нажать на кнопку "Войти по почте" внутри iframe.
        
        Returns:
            True если успешно
        """
        try:
            logger.info("Ищем кнопку 'Войти по почте' в iframe")
            
            # Ждем появления модального окна
            time.sleep(3)
            
            # Сначала ищем кнопку на ОСНОВНОЙ странице (модальное окно может быть БЕЗ iframe)
            logger.info("Ищем кнопку 'Войти по почте' на основной странице")
            
            # Пробуем найти кнопку прямо на странице
            page_selectors = [
                'button:has-text("Войти по почте")',
                'text="Войти по почте"',
            ]
            
            for selector in page_selectors:
                try:
                    element = self.page.wait_for_selector(selector, timeout=2000, state='visible')
                    if element and element.is_visible():
                        text = element.inner_text().strip()
                        if len(text) < 50 and 'Войти по почте' in text:
                            logger.info(f"✅ Найдена кнопка на основной странице: {selector}")
                            element.click()
                            logger.info(f"✅ КЛИК ВЫПОЛНЕН по элементу на основной странице")
                            time.sleep(3)
                            screenshot = self._take_screenshot('email_login_selected')
                            if screenshot:
                                sync_send_photo(screenshot, "✅ Выбран вход по почте")
                            return True
                except:
                    pass
            
            # Если не нашли на основной странице - ищем iframe (только ozonid-lite)
            logger.info("Кнопка не найдена на основной странице, ищем iframe авторизации")
            auth_frame = None
            for frame in self.page.frames:
                frame_url = frame.url
                logger.info(f"Проверяем frame: {frame_url}")
                
                # ВАЖНО: ищем ТОЛЬКО специальный iframe авторизации (ozonid-lite)
                if 'ozonid-lite' in frame_url or 'authFrame' in frame.name:
                    logger.info(f"✅ Найден iframe авторизации: {frame_url}")
                    auth_frame = frame
                    break
            
            # Если iframe не найден - используем основную страницу
            if not auth_frame:
                logger.warning("Специальный iframe не найден, используем основную страницу")
                auth_frame = self.page.main_frame
            
            # Ждем загрузки
            time.sleep(2)
            
            # Ищем кнопку "Войти по почте" - это BUTTON с вложенным div!
            # Структура: <button><div class="...tsBodyControl500Medium">Войти по почте</div></button>
            # Используем ТОЛЬКО стабильные селекторы (без динамических классов)
            selectors = [
                'button:has-text("Войти по почте")',  # КНОПКА с текстом внутри
                'button >> text="Войти по почте"',  # Кнопка содержащая текст
                'text="Войти по почте"',  # Любой элемент с точным текстом
                '[class*="tsBodyControl"]:has-text("Войти по почте")',  # div внутри кнопки
            ]
            
            # Также попробуем через XPath
            xpath_selectors = [
                '//button[contains(., "Войти по почте")]',  # Кнопка содержащая текст
                '//button//div[normalize-space(text())="Войти по почте"]',  # div внутри button
                '//*[normalize-space(text())="Войти по почте"]',  # Любой элемент
            ]
            
            # Пробуем CSS селекторы
            for selector in selectors:
                try:
                    element = auth_frame.wait_for_selector(selector, timeout=3000, state='visible')
                    if element:
                        logger.info(f"✅ Найдена кнопка 'Войти по почте' в iframe: {selector}")
                        
                        # Логируем элемент перед кликом
                        try:
                            text = element.inner_text().strip()
                            logger.info(f"Текст элемента (обрезанный): '{text[:100]}'")
                            
                            # ПРОВЕРКА: если текст слишком длинный - это НЕ кнопка!
                            if len(text) > 50:
                                logger.warning(f"⚠️ Элемент содержит слишком много текста ({len(text)} символов) - пропускаем")
                                continue
                        except:
                            pass
                        
                        # Кликаем
                        element.click()
                        logger.info(f"✅ КЛИК ВЫПОЛНЕН по элементу: {selector}")
                        time.sleep(3)
                        
                        screenshot = self._take_screenshot('email_login_selected')
                        sync_send_photo(screenshot, "✅ Выбран вход по почте (кнопка нажата)")
                        return True
                except PlaywrightTimeout:
                    logger.debug(f"Таймаут для селектора {selector}")
                    continue
                except Exception as e:
                    logger.error(f"Ошибка селектора {selector} в iframe: {e}")
                    continue
            
            # Пробуем XPath селекторы
            for xpath in xpath_selectors:
                try:
                    element = auth_frame.wait_for_selector(f'xpath={xpath}', timeout=3000, state='visible')
                    if element:
                        logger.info(f"✅ Найдена кнопка 'Войти по почте' через XPath")
                        
                        try:
                            text = element.inner_text().strip()
                            logger.info(f"Текст элемента: '{text}'")
                        except:
                            pass
                        
                        # Кликаем
                        element.click()
                        logger.info(f"✅ КЛИК ВЫПОЛНЕН по XPath: {xpath}")
                        time.sleep(3)
                        
                        screenshot = self._take_screenshot('email_login_selected')
                        sync_send_photo(screenshot, "✅ Выбран вход по почте (XPath)")
                        return True
                except PlaywrightTimeout:
                    logger.debug(f"Таймаут для XPath {xpath}")
                    continue
                except Exception as e:
                    logger.error(f"Ошибка XPath {xpath}: {e}")
                    continue
            
            # Если не нашли - логируем все div в iframe
            logger.warning("❌ Кнопка 'Войти по почте' НЕ НАЙДЕНА автоматически в iframe")
            
            try:
                # Логируем все элементы с текстом
                all_elements_with_text = auth_frame.query_selector_all('div, button, a, span')
                logger.info(f"Всего элементов с возможным текстом в iframe: {len(all_elements_with_text)}")
                
                elements_logged = 0
                for idx, elem in enumerate(all_elements_with_text):
                    try:
                        text = elem.inner_text().strip() if elem.inner_text() else ""
                        if text and len(text) < 100 and len(text) > 0:
                            tag = elem.evaluate("el => el.tagName")
                            class_attr = elem.get_attribute('class') or ''
                            logger.info(f"[{idx}] <{tag} class='{class_attr[:50]}'>: '{text}'")
                            elements_logged += 1
                            if elements_logged >= 30:  # Ограничиваем логи
                                break
                    except:
                        pass
            except Exception as e:
                logger.error(f"Ошибка при логировании элементов: {e}")
            
            screenshot = self._take_screenshot('no_email_button_iframe')
            sync_send_photo(screenshot, "❓ Кнопка в iframe не найдена")
            
            # Спрашиваем пользователя
            sync_send_message("⚠️ Не нашел кнопку 'Войти по почте' в iframe.\n\n"
                            "Если видите её - нажмите ВРУЧНУЮ.\n\n"
                            "Отправьте любое сообщение для продолжения.")
            
            response = sync_wait_for_input("Нажмите кнопку вручную и отправьте сообщение", timeout=90)
            
            if response:
                logger.info(f"Пользователь отправил: {response}, продолжаем")
                time.sleep(2)
                screenshot = self._take_screenshot('after_manual_selection')
                sync_send_photo(screenshot, "Продолжаем")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при выборе входа по почте: {e}")
            return False
    
    def login_by_phone_with_qr(self) -> bool:
        """
        Вход через телефон с QR-кодом (альтернативный метод при превышении лимита).
        
        Returns:
            True если успешно
        """
        try:
            logger.info("Начинаем вход через телефон с QR-кодом")
            sync_send_message("📱 Начинаем альтернативный вход через телефон с QR-кодом")
            
            # Ищем iframe с авторизацией
            auth_frame = None
            for frame in self.page.frames:
                frame_url = frame.url
                if 'ozonid-lite' in frame_url or 'authFrame' in frame.name:
                    logger.info(f"Используем iframe авторизации: {frame_url}")
                    auth_frame = frame
                    break
            
            if not auth_frame:
                logger.error("Iframe авторизации не найден")
                return False
            
            time.sleep(2)
            
            # Шаг 1: Нажать на выпадающий список выбора страны
            logger.info("Ищем выпадающий список выбора страны")
            country_selectors = [
                'div.d45_3_8-a.e35_3_8-a0[role="listbox"]',
                'div[role="listbox"]',
                '.d45_3_8-a',
            ]
            
            country_dropdown = None
            for selector in country_selectors:
                try:
                    country_dropdown = auth_frame.wait_for_selector(selector, timeout=3000, state='visible')
                    if country_dropdown:
                        logger.info(f"✅ Найден выпадающий список: {selector}")
                        country_dropdown.click()
                        time.sleep(1)
                        break
                except:
                    continue
            
            if not country_dropdown:
                logger.warning("Выпадающий список не найден, возможно уже открыт")
            
            # Шаг 2: Выбрать "Россия" (первая опция)
            logger.info("Выбираем 'Россия' из списка")
            russia_selectors = [
                'div[role="option"][title="Россия"]',
                'div.a95_3_7-a7.a95_3_7-b.a95_3_7-a8[role="option"]',
                'div[role="option"]:has-text("Россия")',
            ]
            
            for selector in russia_selectors:
                try:
                    russia_option = auth_frame.wait_for_selector(selector, timeout=3000, state='visible')
                    if russia_option:
                        logger.info(f"✅ Найдена опция 'Россия': {selector}")
                        russia_option.click()
                        time.sleep(1)
                        break
                except:
                    continue
            
            # Шаг 3: Ввести номер телефона
            phone = Config.OZON_PHONE
            logger.info(f"Вводим номер телефона: {phone}")
            
            phone_selectors = [
                'input[type="tel"][name="autocomplete"]',
                'input.d5_3_7-a.d5_3_7-a3',
                'input[type="tel"]',
            ]
            
            phone_input = None
            for selector in phone_selectors:
                try:
                    phone_input = auth_frame.wait_for_selector(selector, timeout=3000, state='visible')
                    if phone_input:
                        logger.info(f"✅ Найдено поле для телефона: {selector}")
                        
                        # Очищаем и вводим телефон
                        phone_input.click()
                        time.sleep(0.5)
                        phone_input.fill('')
                        time.sleep(0.3)
                        
                        # Вводим посимвольно
                        for char in phone:
                            phone_input.type(char, delay=50)
                        
                        logger.info(f"✅ Телефон введен: {phone}")
                        time.sleep(2)
                        break
                except Exception as e:
                    logger.error(f"Ошибка при вводе телефона через {selector}: {e}")
                    continue
            
            if not phone_input:
                logger.error("Не удалось найти поле для ввода телефона")
                return False
            
            # Шаг 4: Дождаться появления QR-кода и отправить в Telegram
            logger.info("Ждем появления QR-кода")
            time.sleep(3)
            
            # Ищем изображение с QR-кодом
            qr_selectors = [
                'img.b95_3_3-a',
                'img[src^="data:image/png;base64"]',
                'img[loading="lazy"]',
            ]
            
            qr_image = None
            for selector in qr_selectors:
                try:
                    qr_image = auth_frame.wait_for_selector(selector, timeout=5000, state='visible')
                    if qr_image:
                        logger.info(f"✅ Найден QR-код: {selector}")
                        break
                except:
                    continue
            
            # Делаем скриншот с QR-кодом
            screenshot = self._take_screenshot('qr_code_login')
            
            if qr_image:
                try:
                    # Пытаемся извлечь base64 данные QR-кода
                    qr_src = qr_image.get_attribute('src')
                    if qr_src and qr_src.startswith('data:image/png;base64,'):
                        logger.info("QR-код найден в base64 формате")
                        
                        # Пытаемся декодировать QR-код
                        qr_url = self._decode_qr_from_base64(qr_src)
                        
                        if qr_url:
                            # Отправляем и скриншот, и ссылку
                            message = (
                                "📱 QR-код для входа\n\n"
                                f"🔗 Ссылка из QR-кода:\n<code>{qr_url}</code>\n\n"
                                "Отсканируйте QR-код через приложение Ozon на телефоне:\n"
                                "1. Откройте приложение Ozon\n"
                                "2. Перейдите в профиль\n"
                                "3. Нажмите на иконку сканера\n"
                                "4. Отсканируйте QR-код на скриншоте\n\n"
                                "Или нажмите на ссылку выше (если поддерживается)\n\n"
                                "После сканирования отправьте 'OK' в Telegram."
                            )
                            sync_send_photo(screenshot, message)
                        else:
                            # Если не удалось декодировать, отправляем простое сообщение
                            sync_send_photo(screenshot, 
                                          "📱 QR-код для входа\n\n"
                                          "Отсканируйте его через приложение Ozon на телефоне:\n"
                                          "1. Откройте приложение Ozon\n"
                                          "2. Перейдите в профиль\n"
                                          "3. Нажмите на иконку сканера\n"
                                          "4. Отсканируйте QR-код\n\n"
                                          "После сканирования отправьте 'OK' в Telegram.")
                    else:
                        sync_send_photo(screenshot, "📱 QR-код для входа (отсканируйте через приложение Ozon)")
                except Exception as e:
                    logger.error(f"Ошибка при обработке QR-кода: {e}")
                    sync_send_photo(screenshot, "📱 QR-код для входа")
            else:
                sync_send_photo(screenshot, "📱 Экран входа по телефону")
            
            # Ждем подтверждения от пользователя
            response = sync_wait_for_input(
                "Отсканируйте QR-код в приложении Ozon и отправьте 'OK' когда завершите",
                timeout=180
            )
            
            if not response:
                logger.error("Таймаут ожидания сканирования QR-кода")
                return False
            
            logger.info("Пользователь подтвердил сканирование QR-кода")
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при входе через телефон с QR-кодом: {e}")
            return False
    
    def check_rate_limit_error(self) -> bool:
        """
        Проверить, есть ли сообщение о превышении лимита попыток входа.
        ТОЛЬКО явные сообщения об ошибке лимита.
        
        Returns:
            True если обнаружено превышение лимита
        """
        try:
            logger.info("Проверяем наличие сообщения о превышении лимита")
            
            # Ищем iframe с авторизацией
            auth_frame = None
            for frame in self.page.frames:
                frame_url = frame.url
                if 'ozonid-lite' in frame_url or 'authFrame' in frame.name:
                    auth_frame = frame
                    break
            
            if not auth_frame:
                auth_frame = self.page.main_frame
            
            # Делаем скриншот для отладки
            screenshot = self._take_screenshot('checking_rate_limit')
            
            # Ищем ТОЛЬКО явные сообщения об ошибке лимита
            # Важно: ищем видимые элементы с точными фразами
            strict_error_selectors = [
                'text=/Превышено количество попыток/i',
                'text=/получить новый код можно через/i',
                'text=/слишком много попыток/i',
                'text=/too many attempts/i',
            ]
            
            for selector in strict_error_selectors:
                try:
                    error_element = auth_frame.wait_for_selector(selector, timeout=1000, state='visible')
                    if error_element and error_element.is_visible():
                        error_text = error_element.inner_text()
                        logger.warning(f"⚠️ Обнаружено ВИДИМОЕ сообщение о превышении лимита: '{error_text[:100]}'")
                        
                        # Отправляем скриншот для подтверждения
                        sync_send_photo(screenshot, f"⚠️ Обнаружено превышение лимита:\n{error_text[:200]}")
                        
                        return True
                except:
                    pass
            
            # Дополнительная проверка: ищем текст с таймером вида "11:15" или "через XX:XX"
            try:
                full_text = auth_frame.evaluate("document.body.innerText")
                if full_text:
                    # Паттерн: "Получить новый код можно через 11:15" или "Превышено"
                    timer_pattern = r'(получить новый код можно через|попыток ввода).*\d{1,2}:\d{2}'
                    if re.search(timer_pattern, full_text, re.IGNORECASE):
                        logger.warning(f"⚠️ Найден паттерн таймера в тексте")
                        
                        # Извлекаем контекст
                        match = re.search(timer_pattern, full_text, re.IGNORECASE)
                        if match:
                            context = full_text[max(0, match.start()-50):match.end()+50]
                            logger.info(f"Контекст: {context}")
                            sync_send_photo(screenshot, f"⚠️ Обнаружен таймер:\n{context}")
                            return True
            except Exception as e:
                logger.debug(f"Ошибка при проверке таймера: {e}")
            
            logger.info("✅ Превышение лимита не обнаружено")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке лимита: {e}")
            return False
    
    def enter_email(self, email: Optional[str] = None) -> bool:
        """
        Ввести email в iframe авторизации.
        
        Args:
            email: Email адрес (если None, берется из конфига)
            
        Returns:
            True если успешно
        """
        try:
            email = email or Config.OZON_EMAIL
            logger.info(f"Вводим email: {email}")
            
            # Делаем скриншот текущего состояния
            screenshot = self._take_screenshot('before_email_input')
            sync_send_photo(screenshot, "Ищем поле для ввода email")
            
            # Ищем iframe с авторизацией
            auth_frame = None
            for frame in self.page.frames:
                frame_url = frame.url
                if 'ozonid-lite' in frame_url or 'authFrame' in frame.name:
                    logger.info(f"Используем iframe авторизации: {frame_url}")
                    auth_frame = frame
                    break
            
            if not auth_frame:
                logger.warning("Iframe не найден, используем основную страницу")
                auth_frame = self.page.main_frame
            
            # Ждем загрузки формы
            time.sleep(2)
            
            # Селекторы для поля ввода
            selectors = [
                'input[type="email"]',
                'input[type="text"]',
                'input[type="tel"]',
                'input[name="email"]',
                'input[name="username"]',
                'input[placeholder*="почт"]',
                'input[placeholder*="email"]',
                'input[placeholder*="телефон"]',
                'input',  # Любой input
            ]
            
            # Логируем все input в iframe
            try:
                all_inputs = auth_frame.query_selector_all('input')
                logger.info(f"Найдено input полей в iframe: {len(all_inputs)}")
                
                for idx, inp in enumerate(all_inputs):
                    try:
                        if inp.is_visible():
                            inp_type = inp.get_attribute('type')
                            inp_placeholder = inp.get_attribute('placeholder')
                            inp_name = inp.get_attribute('name')
                            logger.info(f"Input #{idx}: type={inp_type}, name={inp_name}, placeholder={inp_placeholder}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"Ошибка при логировании input: {e}")
            
            # Пробуем найти и заполнить поле
            for selector in selectors:
                try:
                    email_input = auth_frame.wait_for_selector(selector, timeout=2000, state='visible')
                    if email_input and email_input.is_visible():
                        logger.info(f"Найдено поле email в iframe: {selector}")
                        
                        # Кликаем и очищаем
                        email_input.click()
                        time.sleep(0.5)
                        
                        # Очищаем поле (на случай если там уже что-то есть)
                        email_input.fill('')
                        time.sleep(0.3)
                        
                        # Вводим email посимвольно
                        for char in email:
                            email_input.type(char, delay=50)
                        
                        time.sleep(1)
                        
                        screenshot = self._take_screenshot('email_entered')
                        sync_send_photo(screenshot, f"✅ Email введен: {email}")
                        
                        # Ищем кнопку "Войти" или "Получить код" в iframe
                        submit_selectors = [
                            'button:has-text("Получить код")',
                            'button:has-text("Войти")',
                            'button:has-text("Продолжить")',
                            'button[type="submit"]',
                            'div:has-text("Получить код")',  # Может быть div
                            'div:has-text("Войти")',
                        ]
                        
                        for submit_selector in submit_selectors:
                            try:
                                submit_button = auth_frame.wait_for_selector(submit_selector, timeout=2000, state='visible')
                                if submit_button and submit_button.is_visible():
                                    logger.info(f"Нажимаем кнопку в iframe: {submit_selector}")
                                    submit_button.click()
                                    time.sleep(3)
                                    return True
                            except PlaywrightTimeout:
                                continue
                            except Exception as e:
                                logger.error(f"Ошибка при нажатии {submit_selector}: {e}")
                                continue
                        
                        # Если кнопка не найдена, пробуем Enter
                        logger.info("Кнопка не найдена, пробуем Enter")
                        email_input.press('Enter')
                        time.sleep(3)
                        return True
                        
                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    logger.error(f"Ошибка при обработке селектора {selector}: {e}")
                    continue
            
            # Если не нашли автоматически - просим пользователя
            logger.warning("Поле email не найдено автоматически")
            sync_send_message(f"⚠️ Не удалось найти поле для ввода email автоматически.\n\n"
                            f"Ваш email: <code>{email}</code>\n\n"
                            "Пожалуйста, введите email ВРУЧНУЮ в открытом окне и нажмите кнопку.\n\n"
                            "После этого отправьте любое сообщение в Telegram.")
            
            response = sync_wait_for_input("Введите email вручную и отправьте сообщение", timeout=120)
            
            if response:
                logger.info(f"Пользователь подтвердил ввод email")
                time.sleep(2)
                screenshot = self._take_screenshot('email_manual')
                sync_send_photo(screenshot, "Email введен вручную")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при вводе email: {e}")
            return False
    
    def handle_captcha(self) -> bool:
        """
        Обработать капчу с помощью пользователя.
        
        Returns:
            True если успешно
        """
        try:
            logger.info("Проверяем наличие капчи")
            
            # Ждем немного, чтобы капча загрузилась
            time.sleep(3)
            
            # Делаем скриншот для проверки капчи
            screenshot = self._take_screenshot('checking_captcha')
            
            # Возможные селекторы капчи
            captcha_selectors = [
                'iframe[src*="captcha"]',
                'div[class*="captcha"]',
                'div[id*="captcha"]',
                '.recaptcha',
                '#captcha',
            ]
            
            has_captcha = False
            for selector in captcha_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        has_captcha = True
                        logger.info(f"Обнаружена капча: {selector}")
                        break
                except:
                    pass
            
            if has_captcha:
                sync_send_photo(screenshot, "🤖 Обнаружена CAPTCHA! Пожалуйста, решите капчу на странице.")
                
                # Ждем, пока пользователь решит капчу
                captcha_solution = sync_wait_for_input(
                    "Введите 'OK' когда решите капчу",
                    timeout=180
                )
                
                if not captcha_solution:
                    logger.error("Таймаут ожидания решения капчи")
                    return False
                
                time.sleep(2)
                screenshot = self._take_screenshot('after_captcha')
                sync_send_photo(screenshot, "Капча решена, продолжаем")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обработке капчи: {e}")
            return False
    
    def enter_sms_code(self) -> bool:
        """
        Запросить и ввести SMS код.
        
        Returns:
            True если успешно
        """
        try:
            logger.info("Ждем поле для ввода SMS кода")
            
            # Делаем скриншот
            time.sleep(2)
            screenshot = self._take_screenshot('sms_code_request')
            sync_send_photo(screenshot, "📱 Запрошен SMS код")
            
            # Ждем код от пользователя
            sms_code = sync_wait_for_input(
                "📱 Введите SMS код, который пришел на ваш телефон:",
                timeout=180
            )
            
            if not sms_code:
                logger.error("Таймаут ожидания SMS кода")
                return False
            
            logger.info(f"Получен SMS код: {sms_code}")
            
            # Ищем iframe с авторизацией
            auth_frame = None
            for frame in self.page.frames:
                frame_url = frame.url
                if 'ozonid-lite' in frame_url or 'authFrame' in frame.name:
                    logger.info(f"Используем iframe авторизации для ввода кода: {frame_url}")
                    auth_frame = frame
                    break
            
            if not auth_frame:
                logger.warning("Iframe не найден, используем основную страницу")
                auth_frame = self.page.main_frame
            
            # Ждем появления формы ввода кода
            time.sleep(2)
            
            # ТОЧНЫЙ селектор поля кода из HTML
            code_selectors = [
                'input[name="otp"]',  # Основной селектор из HTML
                'input[type="number"][name="otp"]',
                'input[inputmode="numeric"][name="otp"]',
                'input.d5_3_7-a.d5_3_7-a5',  # По классам
                'input[maxlength="6"][name="otp"]',
                'input[inputmode="numeric"]',  # Запасные варианты
                'input[type="number"]',
                'input[name="code"]',
            ]
            
            # Логируем все input в iframe
            try:
                all_inputs = auth_frame.query_selector_all('input')
                logger.info(f"Найдено input полей в iframe для кода: {len(all_inputs)}")
                
                for idx, inp in enumerate(all_inputs):
                    try:
                        if inp.is_visible():
                            inp_type = inp.get_attribute('type')
                            inp_name = inp.get_attribute('name')
                            inp_maxlength = inp.get_attribute('maxlength')
                            inp_inputmode = inp.get_attribute('inputmode')
                            logger.info(f"Input #{idx}: type={inp_type}, name={inp_name}, maxlength={inp_maxlength}, inputmode={inp_inputmode}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"Ошибка при логировании input: {e}")
            
            # Пробуем найти и заполнить поле кода
            for selector in code_selectors:
                try:
                    code_input = auth_frame.wait_for_selector(selector, timeout=3000, state='visible')
                    if code_input and code_input.is_visible():
                        logger.info(f"✅ Найдено поле кода в iframe: {selector}")
                        
                        # Вводим код
                        code_input.click()
                        time.sleep(0.5)
                        code_input.fill('')
                        time.sleep(0.3)
                        
                        # Вводим посимвольно
                        for char in sms_code:
                            code_input.type(char, delay=100)
                        
                        time.sleep(2)
                        
                        screenshot = self._take_screenshot('sms_code_entered')
                        sync_send_photo(screenshot, "✅ SMS код введен")
                        
                        time.sleep(1)
                        
                        # Нажимаем кнопку "Войти"
                        login_button_selectors = [
                            'button[type="submit"]:has-text("Войти")',
                            'button:has-text("Войти")',
                            'button >> text="Войти"',
                            '[type="submit"]:has-text("Войти")',
                            'text="Войти"'
                        ]
                        
                        button_clicked = False
                        for btn_selector in login_button_selectors:
                            try:
                                login_btn = auth_frame.wait_for_selector(btn_selector, timeout=3000, state='visible')
                                if login_btn and login_btn.is_visible():
                                    btn_text = login_btn.inner_text().strip()
                                    if len(btn_text) < 20:  # Проверяем что это кнопка, а не контейнер
                                        logger.info(f"✅ Найдена кнопка 'Войти' после SMS: {btn_selector}")
                                        login_btn.click()
                                        time.sleep(2)
                                        screenshot = self._take_screenshot('after_sms_login_button')
                                        sync_send_photo(screenshot, "✅ Кнопка 'Войти' нажата после SMS")
                                        button_clicked = True
                                        break
                            except:
                                continue
                        
                        if not button_clicked:
                            logger.warning("⚠️ Кнопка 'Войти' после SMS не найдена, пробуем Enter")
                            try:
                                code_input.press('Enter')
                                time.sleep(2)
                            except:
                                pass
                        
                        time.sleep(2)
                        return True
                        
                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    logger.error(f"Ошибка при обработке селектора {selector}: {e}")
                    continue
            
            # Если не нашли автоматически - просим пользователя
            logger.warning("Поле кода не найдено автоматически")
            sync_send_message(f"⚠️ Не удалось найти поле для ввода кода автоматически.\n\n"
                            f"Ваш SMS код: <code>{sms_code}</code>\n\n"
                            "Пожалуйста, введите его ВРУЧНУЮ в открытом браузере и нажмите 'Войти'.\n\n"
                            "После этого отправьте 'OK' в Telegram.")
            
            response = sync_wait_for_input("Введите 'OK' после того как введете SMS код вручную", timeout=120)
            
            if response and response.upper() == 'OK':
                logger.info("Пользователь подтвердил ввод SMS кода")
                screenshot = self._take_screenshot('sms_code_manual')
                sync_send_photo(screenshot, "SMS код введен вручную")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при вводе SMS кода: {e}")
            return False
    
    def enter_email_code(self) -> bool:
        """
        Запросить и ввести код из email.
        
        Returns:
            True если успешно
        """
        try:
            logger.info("Ждем поле для ввода кода из email")
            
            # Делаем скриншот
            time.sleep(2)
            screenshot = self._take_screenshot('email_code_request')
            sync_send_photo(screenshot, "📧 Запрошен код из email")
            
            # Ждем код от пользователя
            email_code = sync_wait_for_input(
                "📧 Введите код, который пришел на ваш email:",
                timeout=300  # 5 минут на проверку почты
            )
            
            if not email_code:
                logger.error("Таймаут ожидания кода из email")
                return False
            
            logger.info(f"Получен код из email: {email_code}")
            
            # Ищем iframe с авторизацией
            auth_frame = None
            for frame in self.page.frames:
                frame_url = frame.url
                if 'ozonid-lite' in frame_url or 'authFrame' in frame.name:
                    logger.info(f"Используем iframe авторизации для ввода email кода: {frame_url}")
                    auth_frame = frame
                    break
            
            if not auth_frame:
                logger.warning("Iframe не найден, используем основную страницу")
                auth_frame = self.page.main_frame
            
            # Ждем появления формы ввода кода
            time.sleep(2)
            
            # ТОЧНЫЙ селектор поля кода из HTML
            code_selectors = [
                'input[name="otp"]',  # Основной селектор из HTML
                'input[type="number"][name="otp"]',
                'input[inputmode="numeric"][name="otp"]',
                'input.d5_3_7-a.d5_3_7-a5',  # По классам
                'input[maxlength="6"][name="otp"]',
                'input[inputmode="numeric"]',  # Запасные варианты
                'input[type="number"]',
                'input[name="code"]',
            ]
            
            # Логируем все input в iframe
            try:
                all_inputs = auth_frame.query_selector_all('input')
                logger.info(f"Найдено input полей в iframe для email кода: {len(all_inputs)}")
                
                for idx, inp in enumerate(all_inputs):
                    try:
                        if inp.is_visible():
                            inp_type = inp.get_attribute('type')
                            inp_name = inp.get_attribute('name')
                            inp_maxlength = inp.get_attribute('maxlength')
                            inp_inputmode = inp.get_attribute('inputmode')
                            logger.info(f"Input #{idx}: type={inp_type}, name={inp_name}, maxlength={inp_maxlength}, inputmode={inp_inputmode}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"Ошибка при логировании input: {e}")
            
            # Пробуем найти и заполнить поле кода
            for selector in code_selectors:
                try:
                    code_input = auth_frame.wait_for_selector(selector, timeout=3000, state='visible')
                    if code_input and code_input.is_visible():
                        logger.info(f"✅ Найдено поле email кода в iframe: {selector}")
                        
                        # Вводим код
                        code_input.click()
                        time.sleep(0.5)
                        code_input.fill('')
                        time.sleep(0.3)
                        
                        # Вводим посимвольно
                        for char in email_code:
                            code_input.type(char, delay=100)
                        
                        time.sleep(2)
                        
                        screenshot = self._take_screenshot('email_code_entered')
                        sync_send_photo(screenshot, "✅ Email код введен")
                        
                        time.sleep(1)
                        return True
                        
                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    logger.error(f"Ошибка при обработке селектора {selector}: {e}")
                    continue
            
            # Если не нашли автоматически - просим пользователя
            logger.warning("Поле кода не найдено автоматически")
            sync_send_message(f"⚠️ Не удалось найти поле для ввода кода автоматически.\n\n"
                            f"Ваш email код: <code>{email_code}</code>\n\n"
                            "Пожалуйста, введите его ВРУЧНУЮ в открытом браузере.\n\n"
                            "После этого отправьте 'OK' в Telegram.")
            
            response = sync_wait_for_input("Введите 'OK' после того как введете email код вручную", timeout=120)
            
            if response and response.upper() == 'OK':
                logger.info("Пользователь подтвердил ввод email кода")
                screenshot = self._take_screenshot('email_code_manual')
                sync_send_photo(screenshot, "Email код введен вручную")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при вводе email кода: {e}")
            return False
    
    def click_submit_code_button(self) -> bool:
        """
        Нажать кнопку 'Войти' после ввода кода.
        
        Returns:
            True если кнопка найдена и нажата
        """
        try:
            logger.info("🔘 Ищем кнопку 'Войти'...")
            
            # Ищем iframe с авторизацией
            auth_frame = None
            for frame in self.page.frames:
                frame_url = frame.url
                if 'ozonid-lite' in frame_url or 'authFrame' in frame.name:
                    logger.info(f"Используем iframe авторизации для кнопки Войти: {frame_url}")
                    auth_frame = frame
                    break
            
            if not auth_frame:
                logger.warning("Iframe не найден, используем основную страницу")
                auth_frame = self.page.main_frame
            
            # Варианты селекторов для кнопки "Войти"
            button_selectors = [
                'button:has-text("Войти")',
                'button >> text="Войти"',
                '[type="submit"]:has-text("Войти")',
                'div[role="button"]:has-text("Войти")',
                'text="Войти"'
            ]
            
            for selector in button_selectors:
                try:
                    login_button = auth_frame.wait_for_selector(selector, timeout=3000, state='visible')
                    if login_button and login_button.is_visible():
                        # Проверяем, что это кнопка с коротким текстом (не контейнер)
                        button_text = login_button.inner_text().strip()
                        if len(button_text) < 20:
                            logger.info(f"✅ Найдена кнопка 'Войти': {selector}")
                            screenshot = self._take_screenshot('before_login_button_click')
                            
                            login_button.click()
                            time.sleep(2)
                            
                            screenshot = self._take_screenshot('after_login_button_click')
                            sync_send_photo(screenshot, "✅ Кнопка 'Войти' нажата")
                            
                            logger.info("✅ Кнопка 'Войти' нажата успешно")
                            return True
                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    logger.debug(f"Селектор {selector} не сработал: {e}")
                    continue
            
            logger.warning("⚠️ Кнопка 'Войти' не найдена")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при нажатии кнопки 'Войти': {e}")
            return False
    
    def verify_login(self) -> bool:
        """
        Проверить успешность авторизации.
        
        Returns:
            True если авторизован
        """
        try:
            logger.info("Проверяем авторизацию")
            time.sleep(3)
            
            # Делаем скриншот
            screenshot = self._take_screenshot('after_login')
            
            # Сначала проверяем признаки НЕавторизации
            not_auth_indicators = [
                'text="Вы не авторизованы"',
                '[data-widget="myGuest"]',
                'text="необходимо войти"',
                '[data-widget="loginButton"]'
            ]
            
            for indicator in not_auth_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        logger.warning(f"❌ Обнаружен индикатор неавторизации: {indicator}")
                        logger.warning(f"Текст элемента: {element.inner_text()[:100]}")
                        sync_send_photo(screenshot, "❌ Авторизация не выполнена - обнаружено сообщение 'Вы не авторизованы'")
                        return False
                except:
                    pass
            
            # Проверяем признаки успешной авторизации
            success_indicators = [
                'text="Мои заказы"',
                'text="Профиль"',
                '[data-test-id="user-menu"]',
                'a[href*="/my/"]',
                'div[class*="userAvatar"]',
                '[data-widget="profileMenu"]'
            ]
            
            for indicator in success_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        logger.info(f"✅ Авторизация успешна! Найден индикатор: {indicator}")
                        sync_send_photo(screenshot, "✅ Авторизация успешна!")
                        return True
                except:
                    pass
            
            # Если не нашли ни одного индикатора, отправляем скриншот для проверки
            logger.warning("⚠️ Не удалось определить статус авторизации автоматически")
            sync_send_photo(screenshot, "⚠️ Результат авторизации не определен (проверьте вручную)")
            
            # Спрашиваем пользователя
            response = sync_wait_for_input(
                "Авторизация прошла успешно? Введите 'YES' если да, или 'NO' если нет:",
                timeout=60
            )
            
            if response and response.upper() in ['YES', 'ДА', 'Y']:
                logger.info("Пользователь подтвердил успешную авторизацию")
                return True
            
            logger.warning("Авторизация не подтверждена")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке авторизации: {e}")
            return False
    
    def login(self) -> bool:
        """
        Полный процесс авторизации через email с автоматическим переключением на телефон при превышении лимита.
        
        Returns:
            True если успешно
        """
        try:
            sync_send_message("🚀 Начинаем процесс авторизации на Ozon через email...")
            
            # Шаг 1: Открываем страницу
            if not self.open_login_page():
                sync_send_message("❌ Ошибка при открытии страницы")
                return False
            
            # Шаг 2: Нажимаем кнопку "Войти"
            if not self.click_login_button():
                sync_send_message("❌ Ошибка при открытии формы входа")
                return False
            
            # ПРОВЕРКА: Превышен ли лимит попыток?
            if self.check_rate_limit_error():
                logger.warning("⚠️ Обнаружено превышение лимита попыток входа")
                sync_send_message("⚠️ Превышен лимит попыток входа через email.\n\n"
                                "Переключаемся на альтернативный метод: вход через телефон с QR-кодом.")
                
                # Переключаемся на вход через телефон
                if not self.login_by_phone_with_qr():
                    sync_send_message("❌ Ошибка при входе через телефон с QR-кодом")
                    return False
                
                # Проверяем успешность входа
                if not self.verify_login():
                    sync_send_message("❌ Авторизация через QR-код не подтверждена")
                    return False
                
                sync_send_message("✅ Авторизация через QR-код завершена успешно!")
                return True
            
            # Шаг 3: Пытаемся выбрать "Войти по почте" (если есть такая опция)
            # Если не найдем - продолжим, т.к. форма может быть универсальной
            email_button_found = self.click_email_login_button()
            if not email_button_found:
                logger.warning("Кнопка email не найдена, проверяем лимит и пробуем альтернативы")
                
                # Ещё раз проверяем лимит после попытки нажать кнопку
                if self.check_rate_limit_error():
                    logger.warning("⚠️ Лимит превышен, переключаемся на телефон")
                    sync_send_message("⚠️ Обнаружено ограничение. Переключаемся на вход через телефон с QR-кодом.")
                    
                    if not self.login_by_phone_with_qr():
                        sync_send_message("❌ Ошибка при входе через телефон")
                        return False
                    
                    if not self.verify_login():
                        sync_send_message("❌ Авторизация не подтверждена")
                        return False
                    
                    sync_send_message("✅ Авторизация завершена успешно!")
                    return True
                
                sync_send_message("⚠️ Переключатель не найден, пробую ввести email напрямую...")
            
            # Шаг 4: Обрабатываем капчу если есть
            if not self.handle_captcha():
                sync_send_message("❌ Ошибка при обработке капчи")
                return False
            
            # Шаг 5: Вводим email
            if not self.enter_email():
                sync_send_message("❌ Ошибка при вводе email")
                return False
            
            # Шаг 6: Обрабатываем капчу после ввода email
            if not self.handle_captcha():
                sync_send_message("❌ Ошибка при обработке капчи")
                return False
            
            # Шаг 7: Вводим SMS код
            if not self.enter_sms_code():
                # Проверяем, может быть превышен лимит (ТОЛЬКО если не удалось ввести код)
                if self.check_rate_limit_error():
                    logger.warning("⚠️ Лимит превышен при вводе SMS, переключаемся на телефон")
                    sync_send_message("⚠️ Превышен лимит попыток. Переключаемся на вход через телефон с QR-кодом.")
                    
                    if not self.login_by_phone_with_qr():
                        return False
                    if not self.verify_login():
                        return False
                    sync_send_message("✅ Авторизация завершена успешно!")
                    return True
                
                sync_send_message("❌ Ошибка при вводе SMS кода")
                return False
            
            # Шаг 8: Вводим код из email
            if not self.enter_email_code():
                sync_send_message("❌ Ошибка при вводе email кода")
                return False
            
            # Шаг 9: Нажимаем кнопку "Войти" после email кода
            if not self.click_submit_code_button():
                logger.warning("⚠️ Кнопка 'Войти' после email не найдена, пробуем продолжить...")
                sync_send_message("⚠️ Кнопка 'Войти' не найдена автоматически. Проверяю авторизацию...")
            
            # Шаг 10: Проверяем успешность
            if not self.verify_login():
                sync_send_message("❌ Авторизация не подтверждена")
                return False
            
            sync_send_message("✅ Авторизация завершена успешно!")
            return True
            
        except Exception as e:
            logger.error(f"Критическая ошибка при авторизации: {e}")
            sync_send_message(f"❌ Критическая ошибка: {str(e)}")
            return False
