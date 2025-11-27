"""Модуль уведомлений через Telegram."""
import asyncio
import threading
from typing import Awaitable, Optional, TypeVar, List, Tuple

from loguru import logger
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import Config
from prompt_manager import PromptManager

PROMPT_MANAGER = PromptManager()
_T = TypeVar("_T")


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
        # Получаем список всех пользователей для отправки сообщений
        self.chat_ids = [uid for uid in Config.ALLOWED_USERS if uid and uid != 0]
        # Если список пуст - используем основной chat_id
        if not self.chat_ids:
            self.chat_ids = [int(Config.TELEGRAM_CHAT_ID)] if Config.TELEGRAM_CHAT_ID else []
        self.prompt_manager = PROMPT_MANAGER
        logger.info(f"📬 Notifier инициализирован для {len(self.chat_ids)} пользователей: {self.chat_ids}")
        
    async def send_message(self, message: str) -> bool:
        """
        Отправить текстовое сообщение всем пользователям.
        
        Args:
            message: Текст сообщения
            
        Returns:
            True если успешно отправлено хотя бы одному, False иначе
        """
        success = False
        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML'
                )
                success = True
            except TelegramError as e:
                logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")
        
        if success:
            logger.info(f"Сообщение отправлено: {message[:50]}...")
        return success
    
    async def send_photo(self, photo_path: str, caption: Optional[str] = None) -> bool:
        """
        Отправить фото всем пользователям.
        
        Args:
            photo_path: Путь к фото
            caption: Подпись к фото
            
        Returns:
            True если успешно отправлено хотя бы одному, False иначе
        """
        success = False
        for chat_id in self.chat_ids:
            try:
                with open(photo_path, 'rb') as photo:
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=caption
                    )
                success = True
            except (TelegramError, FileNotFoundError) as e:
                logger.error(f"Ошибка отправки фото пользователю {chat_id}: {e}")
        
        if success:
            logger.info(f"Фото отправлено: {photo_path}")
        return success
    
    async def wait_for_user_input(
        self, 
        prompt: str, 
        timeout: int = 0, 
        options: Optional[List[Tuple[str, str]]] = None
    ) -> Optional[str]:
        """
        Отправить запрос и дождаться ответа без getUpdates-конфликтов.
        
        Args:
            prompt: Текст запроса
            timeout: Таймаут ожидания в секундах
            options: Список кнопок [(значение_ответа, текст_кнопки), ...]
                    Например: [("1", "1️⃣ Вариант 1"), ("2", "2️⃣ Вариант 2")]
        """
        prompt_id = self.prompt_manager.create_prompt(prompt, timeout if timeout > 0 else None)
        
        # Формируем сообщение
        message_parts = [
            f"⏳ {prompt}",
        ]
        
        # Если есть кнопки - не добавляем инструкцию по ответу
        if not options:
            message_parts.extend([
                "✍️ Ответьте на ЭТО сообщение или начните ответ с кода запроса",
                f"🆔 Код запроса: <b>{prompt_id}</b>",
            ])
        else:
            message_parts.append(f"🆔 Код: <b>{prompt_id}</b>")
        
        message = "\n".join(message_parts)
        
        # Создаем inline-кнопки если они переданы
        reply_markup = None
        if options:
            keyboard = []
            # Группируем кнопки по 2 в ряд
            for i in range(0, len(options), 2):
                row = []
                for j in range(i, min(i + 2, len(options))):
                    value, text = options[j]  # options передаются как (value, text)
                    # callback_data = значение ответа для автоматической отправки
                    row.append(InlineKeyboardButton(text, callback_data=f"prompt:{prompt_id}:{value}"))
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение с кнопками всем пользователям
        sent = False
        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                sent = True
            except TelegramError as e:
                logger.error(f"Ошибка отправки промпта пользователю {chat_id}: {e}")
        
        if not sent:
            logger.error("Не удалось отправить промпт ни одному пользователю")
            return None
        
        logger.info(f"📤 Промпт {prompt_id} отправлен, ожидаем ответ пользователя")

        loop = asyncio.get_event_loop()
        use_timeout = timeout > 0
        start_time = loop.time()

        while True:
            response = self.prompt_manager.get_response_text(prompt_id)
            if response is not None:
                logger.info(f"✅ Получен ответ для промпта {prompt_id}: {response}")
                return response

            if use_timeout and (loop.time() - start_time) >= timeout:
                logger.warning(f"Таймаут ожидания ответа по промпту {prompt_id}")
                self.prompt_manager.mark_expired(prompt_id)
                await self.send_message("❌ Время ожидания истекло")
                return None

            await asyncio.sleep(1.5)


def _run_in_thread(coro: Awaitable[_T]) -> _T:
    """Выполнить корутину в отдельном event loop и вернуть результат."""
    result: list[_T] = []

    def runner():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            value = new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
        result.append(value)

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    return result[0]


def _run_async(coro: Awaitable[_T]) -> _T:
    loop = get_or_create_eventloop()
    if loop.is_running():
        return _run_in_thread(coro)
    return loop.run_until_complete(coro)


def sync_send_message(message: str) -> bool:
    """Синхронная отправка сообщения."""
    notifier = TelegramNotifier()
    return _run_async(notifier.send_message(message))


def sync_send_photo(photo_path: str, caption: Optional[str] = None) -> bool:
    """Синхронная отправка фото."""
    notifier = TelegramNotifier()
    return _run_async(notifier.send_photo(photo_path, caption))


def sync_wait_for_input(
    prompt: str, 
    timeout: int = 0, 
    options: Optional[List[Tuple[str, str]]] = None
) -> Optional[str]:
    """
    Синхронное ожидание ответа пользователя.
    
    Args:
        prompt: Текст запроса
        timeout: Таймаут ожидания в секундах
        options: Список кнопок [(значение_ответа, текст_кнопки), ...]
                Например: [("yes", "✅ Да"), ("no", "❌ Нет")]
    """
    notifier = TelegramNotifier()
    return _run_async(notifier.wait_for_user_input(prompt, timeout, options))
