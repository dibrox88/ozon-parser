#!/bin/bash
# Настройка systemd service для API сервера Ozon Parser

set -e

echo "🔧 Настройка systemd service для Ozon Parser API..."

# Переменные
PROJECT_DIR="$HOME/ozon_parser"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="ozon-parser-api"
USER=$(whoami)

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Проверка наличия виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Виртуальное окружение не найдено!${NC}"
    echo "Сначала запустите deploy.sh"
    exit 1
fi

# Создание systemd service файла
echo -e "\n${YELLOW}📝 Создание systemd service...${NC}"

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=Ozon Parser API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/api_server.py
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/logs/api_server.log
StandardError=append:$PROJECT_DIR/logs/api_server_error.log

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Service файл создан: /etc/systemd/system/$SERVICE_NAME.service"

# Перезагрузка systemd
echo -e "\n${YELLOW}🔄 Перезагрузка systemd...${NC}"
sudo systemctl daemon-reload

# Включение автозапуска
echo -e "\n${YELLOW}🚀 Включение автозапуска...${NC}"
sudo systemctl enable $SERVICE_NAME

# Запуск сервиса
echo -e "\n${YELLOW}▶️  Запуск сервиса...${NC}"
sudo systemctl start $SERVICE_NAME

# Проверка статуса
sleep 2
echo -e "\n${YELLOW}📊 Статус сервиса:${NC}"
sudo systemctl status $SERVICE_NAME --no-pager

echo -e "\n${GREEN}✅ Systemd service настроен и запущен!${NC}"
echo -e "\n${YELLOW}Полезные команды:${NC}"
echo "  sudo systemctl status $SERVICE_NAME    - проверить статус"
echo "  sudo systemctl restart $SERVICE_NAME   - перезапустить"
echo "  sudo systemctl stop $SERVICE_NAME      - остановить"
echo "  sudo systemctl start $SERVICE_NAME     - запустить"
echo "  sudo journalctl -u $SERVICE_NAME -f    - смотреть логи в реальном времени"
