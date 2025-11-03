#!/bin/bash
# Скрипт для настройки Telegram Bot как systemd сервис

echo "========================================="
echo "🤖 Настройка Telegram Bot Service"
echo "========================================="
echo ""

# Создаём systemd unit file
echo "Создаём /etc/systemd/system/ozon-telegram-bot.service..."

sudo tee /etc/systemd/system/ozon-telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Ozon Parser Telegram Bot
After=network.target

[Service]
Type=simple
User=ozon
WorkingDirectory=/home/ozon/ozon_parser
Environment="PATH=/home/ozon/ozon_parser/venv/bin"
ExecStart=/home/ozon/ozon_parser/venv/bin/python telegram_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ozon/ozon_parser/logs/telegram_bot.log
StandardError=append:/home/ozon/ozon_parser/logs/telegram_bot_error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Файл сервиса создан"
echo ""

# Перезагружаем systemd
echo "Перезагружаем systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Daemon перезагружен"
echo ""

# Запускаем сервис
echo "Запускаем Telegram Bot..."
sudo systemctl start ozon-telegram-bot
sleep 2

# Проверяем статус
echo ""
echo "========================================="
echo "📊 Статус сервиса:"
echo "========================================="
sudo systemctl status ozon-telegram-bot --no-pager -l
echo ""

# Включаем автозапуск
echo "Включаем автозапуск при загрузке сервера..."
sudo systemctl enable ozon-telegram-bot
echo "✅ Автозапуск включен"
echo ""

echo "========================================="
echo "✅ TELEGRAM BOT НАСТРОЕН!"
echo "========================================="
echo ""
echo "Полезные команды:"
echo "  sudo systemctl status ozon-telegram-bot   # Статус"
echo "  sudo systemctl restart ozon-telegram-bot  # Перезапуск"
echo "  sudo systemctl stop ozon-telegram-bot     # Остановка"
echo "  tail -f ~/ozon_parser/logs/telegram_bot.log  # Логи"
echo ""
