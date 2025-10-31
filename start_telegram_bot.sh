#!/bin/bash
# Скрипт для запуска Telegram бота в фоне

cd ~/ozon_parser
source venv/bin/activate

# Проверяем, не запущен ли уже бот
if pgrep -f "python.*telegram_bot.py" > /dev/null; then
    echo "⚠️  Telegram бот уже запущен!"
    echo "PID: $(pgrep -f 'python.*telegram_bot.py')"
    echo ""
    echo "Для перезапуска сначала остановите бота:"
    echo "./stop_telegram_bot.sh"
    exit 1
fi

# Запускаем бота
echo "🤖 Запуск Telegram бота..."
nohup python telegram_bot.py > logs/telegram_bot.log 2>&1 &

# Ждем секунду
sleep 1

# Проверяем, запустился ли бот
if pgrep -f "python.*telegram_bot.py" > /dev/null; then
    PID=$(pgrep -f "python.*telegram_bot.py")
    echo "✅ Telegram бот запущен! PID: $PID"
    echo ""
    echo "📋 Управление:"
    echo "   ./stop_telegram_bot.sh - остановить бота"
    echo "   tail -f logs/telegram_bot.log - смотреть логи"
    echo ""
    echo "💬 Откройте Telegram и отправьте /start боту"
else
    echo "❌ Ошибка запуска бота!"
    echo "Проверьте логи: tail logs/telegram_bot.log"
    exit 1
fi
