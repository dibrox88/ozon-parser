"""Модуль уведомлений через Telegram."""
import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from loguru import logger
from config import Config


def get_or_create_eventloop():
    """Получить или создать event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


class TelegramNotifier:
    """Класс для отправки уведомлений через Telegram."""
    
    def __init__(self):
        """Инициализация."""
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
    async def send_message(self, message: str) -> bool:
        """
        Отправить текстовое сообщение.
        
        Args:
            message: Текст сообщения
            
        Returns:
            True если успешно, False иначе
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Сообщение отправлено: {message[:50]}...")
            return True
        except TelegramError as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    async def send_photo(self, photo_path: str, caption: Optional[str] = None) -> bool:
        """
        Отправить фото.
        
        Args:
            photo_path: Путь к фото
            caption: Подпись к фото
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with open(photo_path, 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=caption
                )
            logger.info(f"Фото отправлено: {photo_path}")
            return True
        except (TelegramError, FileNotFoundError) as e:
            logger.error(f"Ошибка отправки фото: {e}")
            return False
    
    async def wait_for_user_input(self, prompt: str, timeout: int = 300) -> Optional[str]:
        """
        Отправить запрос и ждать ответа от пользователя.
        
        Args:
            prompt: Текст запроса
            timeout: Таймаут ожидания в секундах (0 = без таймаута)
            
        Returns:
            Ответ пользователя или None
        """
        # СНАЧАЛА очищаем старые updates ДО отправки промпта
        try:
            # Одна попытка с большим лимитом
            updates = await self.bot.get_updates(limit=100, timeout=1)
            if updates:
                last_update_id = updates[-1].update_id
                # Подтверждаем все updates
                await self.bot.get_updates(offset=last_update_id + 1, timeout=1)
                logger.info(f"✅ Очищено {len(updates)} старых updates перед отправкой промпта")
            else:
                last_update_id = 0
                logger.info(f"✅ Нет старых updates")
        except Exception as e:
            logger.warning(f"Не удалось очистить старые updates: {e}")
            last_update_id = 0
        
        # ТЕПЕРЬ отправляем промпт - пользователь увидит его только после очистки
        await self.send_message(f"⏳ {prompt}")
        logger.info(f"📤 Промпт отправлен, ожидаем ответа с update_id > {last_update_id}")
        
        # Если timeout=0, ждем бесконечно
        use_timeout = timeout > 0
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Проверяем таймаут только если он задан
            if use_timeout and (asyncio.get_event_loop().time() - start_time) >= timeout:
                logger.warning("Таймаут ожидания ответа от пользователя")
                await self.send_message("❌ Время ожидания истекло")
                return None
            try:
                # Проверяем новые сообщения
                updates = await self.bot.get_updates(
                    offset=last_update_id + 1,
                    timeout=10
                )
                
                for update in updates:
                    if (update.message and 
                        update.message.chat_id == int(self.chat_id) and
                        update.message.text):
                        
                        response = update.message.text.strip()
                        logger.info(f"Получен ответ от пользователя: {response}")
                        
                        # ВАЖНО: Обновляем last_update_id ПЕРЕД подтверждением
                        last_update_id = update.update_id
                        
                        # Подтверждаем получение всех updates до этого момента
                        await self.bot.get_updates(offset=last_update_id + 1, timeout=1)
                        
                        # НЕ отправляем подтверждение здесь - это сделает вызывающий код
                        # чтобы избежать дублирования сообщений
                        logger.info(f"✅ Получен и подтвержден ответ: {response}")
                        
                        return response
                    
                    last_update_id = update.update_id
                    
            except TelegramError as e:
                logger.error(f"Ошибка при ожидании ответа: {e}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Неожиданная ошибка при ожидании ответа: {e}")
                await asyncio.sleep(1)


def sync_send_message(message: str) -> bool:
    """
    Синхронная обертка для отправки сообщения.
    
    Args:
        message: Текст сообщения
        
    Returns:
        True если успешно
    """
    notifier = TelegramNotifier()
    loop = get_or_create_eventloop()
    
    if loop.is_running():
        # Создаем новый event loop в отдельном потоке
        import threading
        result = [False]
        
        def run_async():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            result[0] = new_loop.run_until_complete(notifier.send_message(message))
            new_loop.close()
        
        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join()
        return result[0]
    else:
        return loop.run_until_complete(notifier.send_message(message))


def sync_send_photo(photo_path: str, caption: Optional[str] = None) -> bool:
    """
    Синхронная обертка для отправки фото.
    
    Args:
        photo_path: Путь к фото
        caption: Подпись
        
    Returns:
        True если успешно
    """
    notifier = TelegramNotifier()
    loop = get_or_create_eventloop()
    
    if loop.is_running():
        # Создаем новый event loop в отдельном потоке
        import threading
        result = [False]
        
        def run_async():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            result[0] = new_loop.run_until_complete(notifier.send_photo(photo_path, caption))
            new_loop.close()
        
        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join()
        return result[0]
    else:
        return loop.run_until_complete(notifier.send_photo(photo_path, caption))


def sync_wait_for_input(prompt: str, timeout: int = 300) -> Optional[str]:
    """
    Синхронная обертка для ожидания ввода.
    
    Args:
        prompt: Текст запроса
        timeout: Таймаут в секундах
        
    Returns:
        Ответ пользователя
    """
    notifier = TelegramNotifier()
    loop = get_or_create_eventloop()
    
    if loop.is_running():
        # Создаем новый event loop в отдельном потоке
        import threading
        result: list[Optional[str]] = [None]
        
        def run_async():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            result[0] = new_loop.run_until_complete(notifier.wait_for_user_input(prompt, timeout))
            new_loop.close()
        
        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join()
        return result[0]
    else:
        return loop.run_until_complete(notifier.wait_for_user_input(prompt, timeout))
