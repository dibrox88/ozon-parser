"""
Telegram бот для управления парсером Ozon.
Позволяет запускать парсинг вручную через команды.
"""

import asyncio
import subprocess
import os
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from loguru import logger
from config import Config

# Глобальная переменная для отслеживания статуса парсинга
parsing_in_progress = False
last_parse_time = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие и список команд."""
    welcome_message = (
        "🤖 <b>Ozon Parser Bot</b>\n\n"
        "Доступные команды:\n\n"
        "/parse - Запустить парсинг вручную\n"
        "/status - Показать статус парсера\n"
        "/help - Показать эту справку\n\n"
        "⏰ Автоматический запуск: каждые 15 минут (9:00-21:00 МСК)"
    )
    await update.message.reply_text(welcome_message, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка."""
    help_message = (
        "ℹ️ <b>Справка по командам:</b>\n\n"
        "<b>/parse</b> - Запустить парсинг Ozon заказов вручную\n"
        "  • Парсит новые заказы\n"
        "  • Обновляет Google Sheets\n"
        "  • Отправляет уведомления о ходе работы\n\n"
        "<b>/status</b> - Проверить статус парсера\n"
        "  • Показывает, запущен ли парсер сейчас\n"
        "  • Время последнего запуска\n\n"
        "<b>/help</b> - Показать эту справку\n\n"
        "⚠️ <b>Важно:</b>\n"
        "• Парсер нельзя запустить, если он уже работает\n"
        "• Cookies нужно обновлять каждые 3-7 дней"
    )
    await update.message.reply_text(help_message, parse_mode='HTML')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - показать статус парсера."""
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


async def parse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /parse - запустить парсинг вручную."""
    global parsing_in_progress, last_parse_time
    
    if parsing_in_progress:
        await update.message.reply_text(
            "⚠️ <b>Парсер уже запущен!</b>\n\n"
            "Дождитесь завершения текущего парсинга.",
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
        # Запускаем парсер как subprocess
        result = subprocess.run(
            ['python', 'main.py'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 минут максимум
        )
        
        if result.returncode == 0:
            logger.info("✅ Парсинг завершен успешно")
        else:
            logger.error(f"❌ Парсинг завершился с ошибкой: {result.returncode}")
            await update.message.reply_text(
                f"❌ <b>Ошибка при выполнении парсинга</b>\n\n"
                f"Код ошибки: {result.returncode}\n"
                f"Проверьте логи для деталей.",
                parse_mode='HTML'
            )
    
    except subprocess.TimeoutExpired:
        logger.error("⏱️ Парсинг превысил лимит времени (30 мин)")
        await update.message.reply_text(
            "⏱️ <b>Превышено время выполнения</b>\n\n"
            "Парсинг занял более 30 минут и был остановлен.\n"
            "Проверьте логи для деталей.",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске парсера: {e}")
        await update.message.reply_text(
            f"❌ <b>Ошибка</b>\n\n{str(e)}",
            parse_mode='HTML'
        )
    
    finally:
        parsing_in_progress = False


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"Ошибка в боте: {context.error}")


async def post_init(application: Application):
    """Настройка бота после инициализации - установка меню команд."""
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("parse", "🚀 Запустить парсинг"),
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
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("✅ Бот запущен и готов к работе")
    logger.info("Доступные команды: /start, /help, /status, /parse")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
