#!/bin/bash
# Скрипт для настройки systemd сервиса Telegram бота

echo "🤖 Настройка Telegram бота как systemd сервис..."
echo ""

# Проверяем, что мы в правильной директории
if [ ! -f "telegram_bot.py" ]; then
    echo "❌ Ошибка: файл telegram_bot.py не найден"
    echo "Запустите скрипт из директории ozon_parser"
    exit 1
fi

PARSER_DIR="$(pwd)"
VENV_PYTHON="$PARSER_DIR/venv/bin/python"

# Проверяем venv
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Ошибка: виртуальное окружение не найдено в $PARSER_DIR/venv"
    exit 1
fi

# Создаем systemd service файл
SERVICE_FILE="/tmp/ozon-bot.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Ozon Parser Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PARSER_DIR
Environment="PATH=$PARSER_DIR/venv/bin:/usr/bin:/bin"
ExecStart=$VENV_PYTHON $PARSER_DIR/telegram_bot.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=append:$PARSER_DIR/logs/telegram_bot.log
StandardError=append:$PARSER_DIR/logs/telegram_bot_error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Создан файл сервиса: $SERVICE_FILE"
echo ""

# Копируем в systemd (требует sudo)
echo "📋 Для установки сервиса выполните:"
echo ""
echo "sudo cp $SERVICE_FILE /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable ozon-bot"
echo "sudo systemctl start ozon-bot"
echo ""
echo "🔍 Проверить статус:"
echo "sudo systemctl status ozon-bot"
echo ""
echo "📄 Посмотреть логи:"
echo "tail -f $PARSER_DIR/logs/telegram_bot.log"
echo ""

# Спрашиваем, установить ли сейчас
read -p "❓ Установить сервис сейчас? (требуется sudo) [y/N]: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 Устанавливаем сервис..."
    
    sudo cp "$SERVICE_FILE" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable ozon-bot
    sudo systemctl start ozon-bot
    
    echo ""
    echo "✅ Сервис установлен и запущен!"
    echo ""
    
    # Показываем статус
    sudo systemctl status ozon-bot --no-pager
    
    echo ""
    echo "🎉 Telegram бот готов к работе!"
    echo "Отправьте /start боту в Telegram для проверки."
else
    echo "ℹ️  Установите сервис вручную командами выше."
fi
