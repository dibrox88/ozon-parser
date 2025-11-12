"""
Telegram бот для управления парсером Ozon.
Позволяет запускать парсинг вручную через команды.
"""

import asyncio
import subprocess
import os
import signal
import io
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from loguru import logger
from config import Config

# Глобальные переменные для отслеживания статуса парсинга
parsing_in_progress = False
last_parse_time = None
current_parser_process = None  # Текущий процесс парсера для остановки

# Состояния для ConversationHandler (parse_range)
WAITING_LAST_ORDER, WAITING_COUNT = range(2)


def check_update(update: Update) -> bool:
    """Проверка что update содержит сообщение и пользователя."""
    return update.message is not None and update.effective_user is not None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие и список команд."""
    if not update.message:
        return
    
    welcome_message = (
        "🤖 <b>Ozon Parser Bot</b>\n\n"
        "Доступные команды:\n\n"
        "/parse - Запустить парсинг вручную\n"
        "/parse_range - 📊 Парсинг диапазона заказов\n"
        "/stop - Остановить парсинг\n"
        "/status - Показать статус парсера\n"
        "/test_antidetect - 🧪 Тест обхода блокировок\n"
        "/cron_on - ⏰ Включить автозапуск\n"
        "/cron_off - ⏸️ Отключить автозапуск\n"
        "/cron_status - 📋 Статус автозапуска\n"
        "/help - Показать эту справку\n\n"
        "⏰ Автоматический запуск: каждые 15 минут (9:00-21:00 МСК)"
    )
    await update.message.reply_text(welcome_message, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка."""
    if not update.message:
        return
    
    help_message = (
        "ℹ️ <b>Справка по командам:</b>\n\n"
        "<b>/parse</b> - Запустить парсинг Ozon заказов вручную\n"
        "  • Парсит новые заказы\n"
        "  • Обновляет Google Sheets\n"
        "  • Отправляет уведомления о ходе работы\n\n"
        "<b>/parse_range</b> - 📊 Парсинг диапазона заказов\n"
        "  • Запрашивает номер последнего заказа (например, 0710)\n"
        "  • Запрашивает количество заказов (например, 30)\n"
        "  • Парсит заказы от (710-30=680) до 710\n"
        "  • Формат: 46206571-0680 по 46206571-0710\n"
        "  • Для отмены: /cancel\n\n"
        "<b>/stop</b> - Остановить текущий парсинг\n"
        "  • Принудительно завершает работающий процесс\n"
        "  • Закрывает браузер и освобождает ресурсы\n\n"
        "<b>/test_antidetect</b> - 🧪 Тестирование обхода блокировок\n"
        "  • Проверяет 7 различных методов обхода защиты\n"
        "  • Отправляет результаты с рекомендациями\n"
        "  • Помогает найти рабочую стратегию\n\n"
        "<b>/cron_on</b> - ⏰ Включить автоматический запуск\n"
        "  • Активирует cron-задачу\n"
        "  • Парсер будет запускаться каждые 15 мин (9:00-21:00)\n\n"
        "<b>/cron_off</b> - ⏸️ Отключить автоматический запуск\n"
        "  • Деактивирует cron-задачу\n"
        "  • Парсер больше не будет запускаться автоматически\n\n"
        "<b>/cron_status</b> - 📋 Проверить статус автозапуска\n"
        "  • Показывает, включен ли cron\n"
        "  • Последние записи из лога автозапуска\n\n"
        "<b>/status</b> - Проверить статус парсера\n"
        "  • Показывает, запущен ли парсер сейчас\n"
        "  • Время последнего запуска\n\n"
        "<b>/help</b> - Показать эту справку\n\n"
        "⚠️ <b>Важно:</b>\n"
        "• Парсер нельзя запустить, если он уже работает\n"
        "• Cookies нужно обновлять каждые 3-7 дней\n"
        "• При блокировках используйте /test_antidetect"
    )
    await update.message.reply_text(help_message, parse_mode='HTML')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - показать статус парсера."""
    if not update.message:
        return
    
    global parsing_in_progress, last_parse_time
    
    if parsing_in_progress:
        status_message = (
            "⏳ <b>Парсер РАБОТАЕТ</b>\n\n"
            "Дождитесь завершения текущего парсинга."
        )
    else:
        if last_parse_time:
            time_ago = datetime.now() - last_parse_time
            hours = int(time_ago.total_seconds() // 3600)
            minutes = int((time_ago.total_seconds() % 3600) // 60)
            time_str = f"{hours}ч {minutes}мин назад" if hours > 0 else f"{minutes}мин назад"
            
            status_message = (
                "✅ <b>Парсер готов к работе</b>\n\n"
                f"Последний запуск: {time_str}\n"
                f"Время: {last_parse_time.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                "Используйте /parse для запуска."
            )
        else:
            status_message = (
                "✅ <b>Парсер готов к работе</b>\n\n"
                "Ещё не запускался с момента старта бота.\n\n"
                "Используйте /parse для запуска."
            )
    
    await update.message.reply_text(status_message, parse_mode='HTML')


async def monitor_parser_process(update: Update, process: subprocess.Popen):
    """
    Мониторинг процесса парсера в фоновом режиме.
    Позволяет боту обрабатывать другие команды (например /stop).
    """
    global parsing_in_progress, current_parser_process
    
    try:
        # Ждем завершения процесса с проверкой каждые 5 секунд
        max_wait_time = 1800  # 30 минут максимум
        elapsed = 0
        
        while elapsed < max_wait_time:
            # Проверяем завершился ли процесс
            returncode = process.poll()
            
            if returncode is not None:
                # Процесс завершен
                if returncode == 0:
                    logger.info("✅ Парсинг завершен успешно")
                    # Уведомление уже отправлено из main.py
                else:
                    logger.error(f"❌ Парсинг завершился с ошибкой: {returncode}")
                break
            
            # Ждем 5 секунд перед следующей проверкой
            await asyncio.sleep(5)
            elapsed += 5
        
        else:
            # Таймаут - убиваем процесс
            logger.error("⏱️ Парсинг превысил лимит времени (30 мин)")
            process.kill()
            if update.message:
                await update.message.reply_text(
                    "⏱️ <b>Превышено время выполнения</b>\n\n"
                    "Парсинг занял более 30 минут и был остановлен.",
                    parse_mode='HTML'
                )
    
    except Exception as e:
        logger.error(f"❌ Ошибка мониторинга процесса: {e}")
    
    finally:
        parsing_in_progress = False
        current_parser_process = None


async def parse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /parse - запустить парсинг вручную."""
    if not update.message or not update.effective_user:
        return
    
    global parsing_in_progress, last_parse_time, current_parser_process
    
    if parsing_in_progress:
        await update.message.reply_text(
            "⚠️ <b>Парсер уже запущен!</b>\n\n"
            "Дождитесь завершения текущего парсинга или используйте /stop для остановки.",
            parse_mode='HTML'
        )
        return
    
    parsing_in_progress = True
    last_parse_time = datetime.now()
    
    await update.message.reply_text(
        "🚀 <b>Запускаю парсер...</b>\n\n"
        "Следите за обновлениями в этом чате.",
        parse_mode='HTML'
    )
    
    logger.info(f"Парсинг запущен вручную пользователем {update.effective_user.id}")
    
    try:
        # Запускаем парсер как subprocess в фоновом режиме
        # ИСПОЛЬЗУЕМ main.py с Strategy #3 (Desktop Linux UA) и защитой от concurrent runs
        current_parser_process = subprocess.Popen(
            ['python', 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ Процесс парсера запущен (PID: {current_parser_process.pid})")
        
        # НЕ ждем завершения здесь - позволяем боту обрабатывать другие команды
        # Запускаем фоновую задачу для мониторинга процесса
        asyncio.create_task(monitor_parser_process(update, current_parser_process))
    
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске парсера: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
        parsing_in_progress = False
        current_parser_process = None


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stop - остановить парсинг."""
    if not check_update(update):
        return
    
    assert update.message is not None
    assert update.effective_user is not None
    
    global parsing_in_progress, current_parser_process
    
    if not parsing_in_progress and current_parser_process is None:
        # Дополнительная проверка: может быть зависший процесс
        try:
            result = subprocess.run(
                ["pgrep", "-f", "python.*main.py"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                await update.message.reply_text(
                    f"⚠️ <b>Обнаружены зависшие процессы парсера</b>\n\n"
                    f"PID: {', '.join(pids)}\n\n"
                    f"Нажмите /stop еще раз для принудительного завершения.",
                    parse_mode='HTML'
                )
                # Устанавливаем флаг для следующего вызова
                parsing_in_progress = True
                return
        except Exception as e:
            logger.error(f"Ошибка при проверке процессов: {e}")
        
        await update.message.reply_text(
            "ℹ️ <b>Парсер не запущен</b>\n\n"
            "Нечего останавливать. Используйте /status для проверки состояния.",
            parse_mode='HTML'
        )
        return
    
    # Если current_parser_process None, но parsing_in_progress = True
    # (это значит был вызван /stop после обнаружения зависшего процесса)
    if current_parser_process is None:
        try:
            result = subprocess.run(
                ["pkill", "-9", "-f", "python.*main.py"],
                capture_output=True,
                text=True,
                timeout=5
            )
            parsing_in_progress = False
            
            await update.message.reply_text(
                "✅ <b>Зависшие процессы парсера убиты</b>\n\n"
                "Использована команда: pkill -9 -f 'python.*main.py'",
                parse_mode='HTML'
            )
            logger.info("✅ Зависшие процессы парсера убиты через pkill")
            return
        except Exception as e:
            logger.error(f"Ошибка при убийстве процессов: {e}")
            await update.message.reply_text(
                f"❌ <b>Ошибка при остановке процессов</b>\n\n{str(e)}",
                parse_mode='HTML'
            )
            return
    
    try:
        logger.info(f"Остановка парсера запрошена пользователем {update.effective_user.id}")
        
        await update.message.reply_text(
            "⏹️ <b>Останавливаю парсер...</b>",
            parse_mode='HTML'
        )
        
        # Пытаемся корректно завершить процесс
        current_parser_process.terminate()
        
        # Даем 5 секунд на завершение
        try:
            current_parser_process.wait(timeout=5)
            logger.info("✅ Парсер остановлен корректно")
            
            await update.message.reply_text(
                "✅ <b>Парсер остановлен</b>\n\n"
                "Процесс завершен корректно.",
                parse_mode='HTML'
            )
        
        except subprocess.TimeoutExpired:
            # Если не завершился - убиваем принудительно
            logger.warning("⚠️ Процесс не завершился за 5 секунд, принудительное завершение")
            current_parser_process.kill()
            current_parser_process.wait()
            
            await update.message.reply_text(
                "✅ <b>Парсер остановлен принудительно</b>\n\n"
                "Процесс был завершен жестко (kill signal).",
                parse_mode='HTML'
            )
    
    except Exception as e:
        logger.error(f"❌ Ошибка при остановке парсера: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка при остановке</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
    
    finally:
        parsing_in_progress = False
        current_parser_process = None


async def parse_range_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало conversation для /parse_range - запрос последнего номера заказа."""
    if not check_update(update):
        return ConversationHandler.END
    
    assert update.message is not None
    assert update.effective_user is not None
    
    global parsing_in_progress
    
    if parsing_in_progress:
        await update.message.reply_text(
            "⚠️ <b>Парсер уже работает</b>\n\n"
            "Дождитесь завершения текущего парсинга.",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "⏳ 📋 <b>Парсинг диапазона заказов</b>\n\n"
        "Введите номер <b>последнего</b> заказа после дефиса.\n"
        "Например: <code>0710</code> для заказа 46206571-0710\n\n"
        "Для отмены отправьте /cancel",
        parse_mode='HTML'
    )
    
    return WAITING_LAST_ORDER


async def parse_range_last_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка последнего номера заказа."""
    if not check_update(update):
        return ConversationHandler.END
    
    assert update.message is not None
    assert update.message.text is not None
    
    last_order_input = update.message.text.strip()
    
    # Парсим номер последнего заказа
    try:
        last_order_num = int(last_order_input.lstrip('0') or '0')
        if last_order_num <= 0:
            await update.message.reply_text(
                "❌ <b>Некорректный номер</b>\n\n"
                "Номер должен быть положительным числом.\n"
                "Попробуйте еще раз:",
                parse_mode='HTML'
            )
            return WAITING_LAST_ORDER
    except ValueError:
        await update.message.reply_text(
            f"❌ <b>Некорректный формат</b>\n\n"
            f"Не удалось распознать номер: {last_order_input}\n"
            f"Попробуйте еще раз:",
            parse_mode='HTML'
        )
        return WAITING_LAST_ORDER
    
    # Сохраняем в контексте
    if context.user_data is not None:
        context.user_data['last_order_num'] = last_order_num
    
    await update.message.reply_text(
        f"✅ Последний заказ: <code>{last_order_num:04d}</code>\n\n"
        f"Теперь введите <b>количество</b> заказов для парсинга.\n"
        f"Например: <code>30</code> (от 1 до 1000)",
        parse_mode='HTML'
    )
    
    return WAITING_COUNT


async def parse_range_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка количества заказов и запуск парсинга."""
    if not check_update(update):
        return ConversationHandler.END
    
    assert update.message is not None
    assert update.message.text is not None
    
    count_input = update.message.text.strip()
    
    # Парсим количество
    try:
        count = int(count_input)
        if count <= 0 or count > 1000:
            await update.message.reply_text(
                "❌ <b>Некорректное количество</b>\n\n"
                "Должно быть от 1 до 1000.\n"
                "Попробуйте еще раз:",
                parse_mode='HTML'
            )
            return WAITING_COUNT
    except ValueError:
        await update.message.reply_text(
            f"❌ <b>Некорректный формат</b>\n\n"
            f"Не удалось распознать число: {count_input}\n"
            f"Попробуйте еще раз:",
            parse_mode='HTML'
        )
        return WAITING_COUNT
    
    # Получаем last_order_num из контекста
    last_order_num = None
    if context.user_data is not None:
        last_order_num = context.user_data.get('last_order_num')
    
    if last_order_num is None:
        await update.message.reply_text(
            "❌ <b>Ошибка</b>\n\nСессия истекла. Начните заново с /parse_range",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    # Вычисляем диапазон
    first_order_num = last_order_num - count + 1
    if first_order_num < 0:
        first_order_num = 0
    
    first_order = f"46206571-{first_order_num:04d}"
    last_order = f"46206571-{last_order_num:04d}"
    
    # Подтверждение
    await update.message.reply_text(
        f"📊 <b>Параметры парсинга:</b>\n\n"
        f"• Первый заказ: <code>{first_order}</code>\n"
        f"• Последний заказ: <code>{last_order}</code>\n"
        f"• Всего заказов: <b>{count}</b>\n\n"
        f"🚀 Запускаю парсинг...",
        parse_mode='HTML'
    )
    
    # Запускаем парсинг
    global parsing_in_progress, last_parse_time, current_parser_process
    parsing_in_progress = True
    last_parse_time = datetime.now()
    
    logger.info(f"Запуск парсинга диапазона {first_order} - {last_order}")
    
    # Запускаем main.py с параметрами диапазона
    import sys
    python_executable = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), "main.py")
    
    try:
        process = subprocess.Popen(
            [python_executable, script_path, "--range", first_order, last_order],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        current_parser_process = process
        
        # Запускаем мониторинг в фоновом режиме
        asyncio.create_task(monitor_parser_process(update, process))
        
        logger.info(f"Парсер запущен с PID: {process.pid}")
    
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске парсинга диапазона: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка запуска</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
        parsing_in_progress = False
    
    # Очищаем контекст
    if context.user_data is not None:
        context.user_data.clear()
    
    return ConversationHandler.END


async def parse_range_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена conversation."""
    if not check_update(update):
        return ConversationHandler.END
    
    assert update.message is not None
    
    await update.message.reply_text(
        "❌ <b>Отменено</b>\n\nПарсинг диапазона отменён.",
        parse_mode='HTML'
    )
    
    if context.user_data is not None:
        context.user_data.clear()
    
    return ConversationHandler.END


async def test_antidetect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test_antidetect - тестирование стратегий обхода блокировок."""
    if not check_update(update):
        return
    
    assert update.message is not None
    assert update.effective_user is not None
    
    try:
        logger.info(f"Тестирование антидетекта запрошено пользователем {update.effective_user.id}")
        
        await update.message.reply_text(
            "🧪 <b>Запускаю тестирование антидетект стратегий...</b>\n\n"
            "Это займет 1-2 минуты.\n"
            "Протестирую 7 различных методов обхода блокировок.",
            parse_mode='HTML'
        )
        
        # Запускаем тестирование в subprocess
        result = subprocess.run(
            ['python', 'test_antidetect.py'],
            capture_output=True,
            text=True,
            timeout=180  # 3 минуты максимум
        )
        
        if result.returncode == 0:
            # Успешно протестировано
            logger.info("✅ Тестирование антидетекта завершено")
            
            # Отправляем результаты
            if result.stdout:
                await update.message.reply_text(
                    f"✅ <b>Тестирование завершено!</b>\n\n<pre>{result.stdout}</pre>",
                    parse_mode='HTML'
                )
        else:
            logger.error(f"❌ Ошибка тестирования: {result.returncode}")
            await update.message.reply_text(
                f"❌ <b>Ошибка при тестировании</b>\n\n"
                f"Код ошибки: {result.returncode}\n"
                f"Проверьте логи для деталей.",
                parse_mode='HTML'
            )
    
    except subprocess.TimeoutExpired:
        logger.error("⏱️ Тестирование превысило лимит времени")
        await update.message.reply_text(
            "⏱️ <b>Превышено время тестирования</b>\n\n"
            "Процесс занял более 3 минут и был остановлен.",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка</b>\n\n{str(e)}",
            parse_mode='HTML'
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок бота."""
    logger.error(f"❌ Ошибка в боте: {context.error}")
    
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"❌ <b>Произошла ошибка</b>\n\n"
                f"Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")


async def cron_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cron_status - проверить статус автозапуска."""
    if not check_update(update):
        return
    
    assert update.message is not None
    assert update.effective_user is not None
    
    try:
        logger.info(f"Проверка статуса cron запрошена пользователем {update.effective_user.id}")
        
        # Проверяем есть ли активная задача в crontab
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            await update.message.reply_text(
                "⚠️ <b>Ошибка проверки cron</b>\n\n"
                "Не удалось получить список задач crontab.",
                parse_mode='HTML'
            )
            return
        
        # Ищем строку с парсером
        cron_lines = result.stdout.strip().split('\n')
        parser_cron = None
        is_active = False
        
        for line in cron_lines:
            # Ищем по run_parser.sh или main.py в ozon_parser
            if ('run_parser.sh' in line or 'main.py' in line) and 'ozon_parser' in line:
                parser_cron = line
                # Проверяем, закомментирована ли строка
                is_active = not line.strip().startswith('#')
                break
        
        if parser_cron is None:
            status_message = (
                "❌ <b>Автозапуск НЕ настроен</b>\n\n"
                "Задача cron для парсера не найдена.\n"
                "Используйте setup-cron.sh для настройки."
            )
        elif is_active:
            status_message = (
                "✅ <b>Автозапуск ВКЛЮЧЕН</b>\n\n"
                "📋 Расписание:\n"
                "<code>*/15 9-21 * * *</code>\n\n"
                "⏰ Каждые 15 минут с 9:00 до 21:00 МСК\n"
                "(48 запусков в день)\n\n"
                "Используйте /cron_off для отключения."
            )
        else:
            status_message = (
                "⏸️ <b>Автозапуск ОТКЛЮЧЕН</b>\n\n"
                "Задача cron существует, но закомментирована.\n\n"
                "Используйте /cron_on для включения."
            )
        
        # Добавляем информацию о последних запусках из лога
        try:
            log_result = subprocess.run(
                ['tail', '-5', os.path.expanduser('~/ozon_parser/logs/cron.log')],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if log_result.returncode == 0 and log_result.stdout.strip():
                status_message += "\n\n📝 <b>Последние запуски:</b>\n"
                log_lines = log_result.stdout.strip().split('\n')
                for line in log_lines[-3:]:  # Последние 3 строки
                    if line.strip():
                        status_message += f"<code>{line[:80]}</code>\n"
        except:
            pass  # Игнорируем ошибки чтения лога
        
        await update.message.reply_text(status_message, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке статуса cron: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка</b>\n\n{str(e)}",
            parse_mode='HTML'
        )


async def cron_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cron_on - включить автозапуск."""
    if not check_update(update):
        return
    
    assert update.message is not None
    assert update.effective_user is not None
    
    try:
        logger.info(f"Включение cron запрошено пользователем {update.effective_user.id}")
        
        await update.message.reply_text(
            "⏰ <b>Включаю автозапуск...</b>",
            parse_mode='HTML'
        )
        
        # Получаем текущий crontab
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            await update.message.reply_text(
                "⚠️ <b>Ошибка</b>\n\n"
                "Не удалось получить crontab. Возможно, cron не настроен.\n"
                "Используйте setup-cron.sh для первоначальной настройки.",
                parse_mode='HTML'
            )
            return
        
        cron_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        modified = False
        new_cron_lines = []
        
        for line in cron_lines:
            # Ищем по run_parser.sh или main.py в ozon_parser
            if ('run_parser.sh' in line or 'main.py' in line) and 'ozon_parser' in line:
                # Раскомментируем строку
                if line.strip().startswith('#'):
                    new_line = line.lstrip('#').lstrip()
                    new_cron_lines.append(new_line)
                    modified = True
                    logger.info(f"Раскомментирована строка: {new_line}")
                else:
                    new_cron_lines.append(line)
                    # Уже включено
                    await update.message.reply_text(
                        "ℹ️ <b>Автозапуск уже включен</b>\n\n"
                        "Задача cron уже активна.",
                        parse_mode='HTML'
                    )
                    return
            else:
                new_cron_lines.append(line)
        
        if not modified:
            await update.message.reply_text(
                "⚠️ <b>Задача не найдена</b>\n\n"
                "Не найдена задача cron для парсера.\n"
                "Используйте setup-cron.sh для настройки.",
                parse_mode='HTML'
            )
            return
        
        # Записываем обновленный crontab
        new_crontab = '\n'.join(new_cron_lines) + '\n'
        
        write_result = subprocess.run(
            ['crontab', '-'],
            input=new_crontab,
            text=True,
            capture_output=True
        )
        
        if write_result.returncode != 0:
            await update.message.reply_text(
                f"❌ <b>Ошибка записи crontab</b>\n\n{write_result.stderr}",
                parse_mode='HTML'
            )
            return
        
        logger.info("✅ Cron включен успешно")
        await update.message.reply_text(
            "✅ <b>Автозапуск ВКЛЮЧЕН</b>\n\n"
            "⏰ Парсер будет запускаться:\n"
            "• Каждые 15 минут\n"
            "• С 9:00 до 21:00 МСК\n"
            "• 48 раз в день\n\n"
            "Используйте /cron_status для проверки.",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка при включении cron: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка</b>\n\n{str(e)}",
            parse_mode='HTML'
        )


async def cron_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cron_off - отключить автозапуск."""
    if not check_update(update):
        return
    
    assert update.message is not None
    assert update.effective_user is not None
    
    try:
        logger.info(f"Отключение cron запрошено пользователем {update.effective_user.id}")
        
        await update.message.reply_text(
            "⏸️ <b>Отключаю автозапуск...</b>",
            parse_mode='HTML'
        )
        
        # Получаем текущий crontab
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            await update.message.reply_text(
                "⚠️ <b>Ошибка</b>\n\n"
                "Не удалось получить crontab.",
                parse_mode='HTML'
            )
            return
        
        cron_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        modified = False
        new_cron_lines = []
        
        for line in cron_lines:
            # Ищем по run_parser.sh или main.py в ozon_parser
            if ('run_parser.sh' in line or 'main.py' in line) and 'ozon_parser' in line:
                # Комментируем строку
                if not line.strip().startswith('#'):
                    new_line = f"# {line}"
                    new_cron_lines.append(new_line)
                    modified = True
                    logger.info(f"Закомментирована строка: {new_line}")
                else:
                    new_cron_lines.append(line)
                    # Уже отключено
                    await update.message.reply_text(
                        "ℹ️ <b>Автозапуск уже отключен</b>\n\n"
                        "Задача cron уже неактивна.",
                        parse_mode='HTML'
                    )
                    return
            else:
                new_cron_lines.append(line)
        
        if not modified:
            await update.message.reply_text(
                "⚠️ <b>Задача не найдена</b>\n\n"
                "Не найдена задача cron для парсера.",
                parse_mode='HTML'
            )
            return
        
        # Записываем обновленный crontab
        new_crontab = '\n'.join(new_cron_lines) + '\n'
        
        write_result = subprocess.run(
            ['crontab', '-'],
            input=new_crontab,
            text=True,
            capture_output=True
        )
        
        if write_result.returncode != 0:
            await update.message.reply_text(
                f"❌ <b>Ошибка записи crontab</b>\n\n{write_result.stderr}",
                parse_mode='HTML'
            )
            return
        
        logger.info("✅ Cron отключен успешно")
        await update.message.reply_text(
            "✅ <b>Автозапуск ОТКЛЮЧЕН</b>\n\n"
            "⏸️ Парсер больше не будет запускаться автоматически.\n\n"
            "Используйте:\n"
            "• /parse - для ручного запуска\n"
            "• /cron_on - для повторного включения автозапуска",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка при отключении cron: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка</b>\n\n{str(e)}",
            parse_mode='HTML'
        )


async def post_init(application: Application):
    """Настройка бота после инициализации - установка меню команд и проверка процессов."""
    global parsing_in_progress, current_parser_process
    
    # Проверяем, есть ли реально запущенный парсер
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*main.py"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Нет запущенных процессов парсера - сбрасываем флаги
            if parsing_in_progress or current_parser_process is not None:
                logger.warning("⚠️ Обнаружены некорректные флаги при старте (нет процессов парсера)")
                parsing_in_progress = False
                current_parser_process = None
                logger.info("✅ Флаги parsing_in_progress и current_parser_process сброшены")
        else:
            # Есть запущенные процессы парсера
            pids = result.stdout.strip().split('\n')
            logger.warning(f"⚠️ Обнаружены запущенные процессы парсера: {', '.join(pids)}")
            parsing_in_progress = True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки процессов парсера: {e}")
    
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("parse", "🚀 Запустить парсинг"),
        BotCommand("parse_range", "📊 Парсить диапазон"),
        BotCommand("stop", "⏹️ Остановить парсинг"),
        BotCommand("test_antidetect", "🧪 Тест антидетекта"),
        BotCommand("cron_on", "⏰ Включить автозапуск"),
        BotCommand("cron_off", "⏸️ Отключить автозапуск"),
        BotCommand("cron_status", "📋 Статус автозапуска"),
        BotCommand("status", "📊 Статус парсера"),
        BotCommand("help", "❓ Справка"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Меню команд установлено")


def main():
    """Запуск бота."""
    logger.info("🤖 Запуск Telegram бота для управления парсером...")
    
    # Создаем приложение
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("parse", parse_command))
    
    # ConversationHandler для /parse_range
    parse_range_handler = ConversationHandler(
        entry_points=[CommandHandler("parse_range", parse_range_start)],
        states={
            WAITING_LAST_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, parse_range_last_order)],
            WAITING_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, parse_range_count)],
        },
        fallbacks=[CommandHandler("cancel", parse_range_cancel)],
        conversation_timeout=600  # 10 минут таймаут
    )
    application.add_handler(parse_range_handler)
    
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("test_antidetect", test_antidetect_command))
    application.add_handler(CommandHandler("cron_status", cron_status_command))
    application.add_handler(CommandHandler("cron_on", cron_on_command))
    application.add_handler(CommandHandler("cron_off", cron_off_command))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("✅ Бот запущен и готов к работе")
    logger.info("Доступные команды: /start, /help, /status, /parse, /stop, /test_antidetect, /cron_on, /cron_off, /cron_status")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
