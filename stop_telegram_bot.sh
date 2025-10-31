#!/bin/bash
# Скрипт для остановки Telegram бота

if pgrep -f "python.*telegram_bot.py" > /dev/null; then
    PID=$(pgrep -f "python.*telegram_bot.py")
    echo "🛑 Остановка Telegram бота (PID: $PID)..."
    kill $PID
    
    # Ждем завершения
    sleep 2
    
    # Проверяем, что процесс завершился
    if pgrep -f "python.*telegram_bot.py" > /dev/null; then
        echo "⚠️  Процесс не завершился, принудительная остановка..."
        kill -9 $PID
    fi
    
    echo "✅ Telegram бот остановлен"
else
    echo "ℹ️  Telegram бот не запущен"
fi
