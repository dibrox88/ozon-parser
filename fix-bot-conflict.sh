#!/bin/bash
# Скрипт для исправления конфликта Telegram Bot

echo "========================================="
echo "🔍 Поиск всех процессов бота..."
echo "========================================="
echo ""

# Показываем все процессы связанные с ботом
echo "Найденные процессы:"
ps aux | grep -E "python.*main.py|python.*telegram_bot.py|python.*api_server.py" | grep -v grep

echo ""
echo "========================================="
echo "🛑 Останавливаем все процессы..."
echo "========================================="
echo ""

# Останавливаем systemd сервисы если запущены
sudo systemctl stop ozon-parser-api 2>/dev/null
sudo systemctl stop ozon-parser-bot 2>/dev/null
sudo systemctl stop ozon-telegram-bot 2>/dev/null

# Убиваем все Python процессы связанные с парсером
pkill -f "python.*main.py"
pkill -f "python.*telegram_bot.py"
pkill -f "python.*api_server.py"

# Ждём завершения
sleep 2

echo "Проверяем что все процессы остановлены..."
REMAINING=$(ps aux | grep -E "python.*main.py|python.*telegram_bot.py|python.*api_server.py" | grep -v grep | wc -l)

if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️  Осталось $REMAINING процессов, принудительно убиваем..."
    pkill -9 -f "python.*main.py"
    pkill -9 -f "python.*telegram_bot.py"
    pkill -9 -f "python.*api_server.py"
    sleep 1
fi

echo ""
echo "========================================="
echo "✅ Все процессы остановлены!"
echo "========================================="
echo ""
echo "Теперь можно запустить заново:"
echo "  cd ~/ozon_parser"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
