#!/bin/bash
# Настройка cron для автоматического запуска парсера
# Запуск каждый час с 9:00 до 21:00 по Москве

set -e

echo "⏰ Настройка cron для автоматического запуска..."

# Переменные
PROJECT_DIR="$HOME/ozon_parser"
VENV_DIR="$PROJECT_DIR/venv"
USER=$(whoami)

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Создание скрипта для запуска через cron
echo -e "\n${YELLOW}📝 Создание скрипта для cron...${NC}"

cat > "$PROJECT_DIR/run_parser.sh" << 'EOF'
#!/bin/bash
# Скрипт для запуска парсера через cron

# Определение путей
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_FILE="$SCRIPT_DIR/logs/cron_$(date +\%Y\%m\%d).log"

# Активация виртуального окружения
source "$VENV_DIR/bin/activate"

# Переход в директорию проекта
cd "$SCRIPT_DIR"

# Логирование
echo "$(date '+%Y-%m-%d %H:%M:%S') - Запуск парсера через cron" >> "$LOG_FILE"

# Запуск парсера
python main.py >> "$LOG_FILE" 2>&1

# Логирование завершения
EXIT_CODE=$?
echo "$(date '+%Y-%m-%d %H:%M:%S') - Парсер завершён с кодом: $EXIT_CODE" >> "$LOG_FILE"

exit $EXIT_CODE
EOF

# Делаем скрипт исполняемым
chmod +x "$PROJECT_DIR/run_parser.sh"

echo -e "${GREEN}✓${NC} Скрипт создан: $PROJECT_DIR/run_parser.sh"

# Добавление задачи в cron
echo -e "\n${YELLOW}📅 Добавление задачи в crontab...${NC}"

# Создание временного файла с новым cron расписанием
CRON_TEMP=$(mktemp)

# Экспорт текущего crontab (если есть)
crontab -l > "$CRON_TEMP" 2>/dev/null || true

# Удаление старых записей Ozon Parser (если есть)
sed -i '/# Ozon Parser/d' "$CRON_TEMP"
sed -i '/run_parser.sh/d' "$CRON_TEMP"

# Добавление новых записей
cat >> "$CRON_TEMP" << EOF

# Ozon Parser - автоматический запуск каждый час с 9:00 до 21:00 (MSK)
# Часовой пояс сервера должен быть настроен на Europe/Moscow
0 9-21 * * * $PROJECT_DIR/run_parser.sh
EOF

# Установка нового crontab
crontab "$CRON_TEMP"
rm "$CRON_TEMP"

echo -e "${GREEN}✓${NC} Задача добавлена в crontab"

# Показать текущий crontab
echo -e "\n${YELLOW}📋 Текущее расписание cron:${NC}"
crontab -l | grep -A 2 "Ozon Parser" || echo "Записи не найдены"

echo -e "\n${GREEN}✅ Cron настроен успешно!${NC}"
echo -e "\n${YELLOW}Расписание:${NC}"
echo "  - Запуск каждый час с 9:00 до 21:00 (МСК)"
echo "  - Логи: $PROJECT_DIR/logs/cron_YYYYMMDD.log"
echo -e "\n${YELLOW}Полезные команды:${NC}"
echo "  crontab -l                    - показать текущее расписание"
echo "  crontab -e                    - редактировать расписание"
echo "  tail -f $PROJECT_DIR/logs/cron_*.log - смотреть логи"
