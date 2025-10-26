#!/bin/bash
# Скрипт для развёртывания Ozon Parser на сервере Timeweb
# Запускать от имени обычного пользователя (не root)

set -e  # Остановка при ошибке

echo "🚀 Начало развёртывания Ozon Parser на Timeweb..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Переменные
PROJECT_DIR="$HOME/ozon_parser"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="ozon-parser-api"
USER=$(whoami)

# Проверка, что скрипт не запущен от root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}❌ Не запускайте этот скрипт от root!${NC}"
   echo "Запустите от обычного пользователя: bash deploy.sh"
   exit 1
fi

echo -e "${GREEN}✓${NC} Пользователь: $USER"

# 1. Обновление системы
echo -e "\n${YELLOW}📦 Обновление системы...${NC}"
sudo apt update
sudo apt upgrade -y

# 2. Установка необходимых пакетов
echo -e "\n${YELLOW}📦 Установка зависимостей...${NC}"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    nginx \
    supervisor \
    tzdata

# 3. Установка Playwright системных зависимостей
echo -e "\n${YELLOW}🎭 Установка зависимостей Playwright...${NC}"
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2

# 4. Создание директории проекта
echo -e "\n${YELLOW}📁 Создание директории проекта...${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 5. Клонирование репозитория (если ещё не клонирован)
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo -e "\n${YELLOW}📥 Клонирование репозитория...${NC}"
    echo "Введите URL вашего git-репозитория (или нажмите Enter, чтобы пропустить):"
    read -r GIT_REPO_URL
    
    if [ -n "$GIT_REPO_URL" ]; then
        git clone "$GIT_REPO_URL" .
    else
        echo -e "${YELLOW}⚠️  Репозиторий не клонирован. Скопируйте файлы вручную в $PROJECT_DIR${NC}"
    fi
fi

# 6. Создание виртуального окружения
echo -e "\n${YELLOW}🐍 Создание виртуального окружения Python...${NC}"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 7. Установка Python зависимостей
echo -e "\n${YELLOW}📦 Установка Python пакетов...${NC}"
if [ -f "requirements-production.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements-production.txt
else
    echo -e "${RED}❌ Файл requirements-production.txt не найден!${NC}"
    exit 1
fi

# 8. Установка браузеров Playwright
echo -e "\n${YELLOW}🎭 Установка браузеров Playwright...${NC}"
playwright install chromium
playwright install-deps chromium

# 9. Настройка timezone на Moscow
echo -e "\n${YELLOW}⏰ Настройка часового пояса (Europe/Moscow)...${NC}"
sudo timedatectl set-timezone Europe/Moscow

# 10. Создание .env файла (если не существует)
echo -e "\n${YELLOW}🔐 Настройка переменных окружения...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "Создание .env файла..."
    cat > "$PROJECT_DIR/.env" << EOF
# API Secret Key (ИЗМЕНИТЕ НА СВОЙ!)
API_SECRET_KEY=$(openssl rand -hex 32)

# Telegram Bot (заполните свои данные)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Google Sheets
GOOGLE_CREDENTIALS_FILE=google_credentials.json
GOOGLE_SHEETS_URL=your_sheets_url_here

# Ozon credentials
OZON_EMAIL=your_email@example.com
OZON_PASSWORD=your_password_here
EOF
    
    echo -e "${YELLOW}⚠️  Файл .env создан с дефолтными значениями${NC}"
    echo -e "${YELLOW}⚠️  ОБЯЗАТЕЛЬНО отредактируйте $PROJECT_DIR/.env перед запуском!${NC}"
else
    echo -e "${GREEN}✓${NC} Файл .env уже существует"
fi

# 11. Создание директорий для логов и скриншотов
echo -e "\n${YELLOW}📁 Создание рабочих директорий...${NC}"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/screenshots"
mkdir -p "$PROJECT_DIR/browser_state"

# 12. Настройка прав доступа
echo -e "\n${YELLOW}🔒 Настройка прав доступа...${NC}"
chmod 700 "$PROJECT_DIR/.env"
chmod 700 "$PROJECT_DIR/google_credentials.json" 2>/dev/null || true

echo -e "\n${GREEN}✅ Базовая установка завершена!${NC}"
echo -e "\n${YELLOW}📝 Следующие шаги:${NC}"
echo "1. Отредактируйте $PROJECT_DIR/.env с вашими данными"
echo "2. Скопируйте google_credentials.json в $PROJECT_DIR/"
echo "3. Запустите скрипт настройки systemd: bash setup-systemd.sh"
echo "4. Запустите скрипт настройки cron: bash setup-cron.sh"
