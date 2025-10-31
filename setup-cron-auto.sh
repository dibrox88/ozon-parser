#!/bin/bash
# Скрипт для настройки автоматического запуска парсера каждые 15 минут (9:00-21:00 МСК)

echo "🔧 Настройка cron для автоматического запуска парсера..."
echo ""

# Путь к парсеру
PARSER_DIR="$HOME/ozon_parser"
VENV_PATH="$PARSER_DIR/venv/bin/activate"
LOG_FILE="$PARSER_DIR/logs/cron.log"

# Создаем директорию для логов, если её нет
mkdir -p "$PARSER_DIR/logs"

# Создаем скрипт запуска
cat > "$PARSER_DIR/run_parser.sh" << 'EOF'
#!/bin/bash
# Скрипт запуска парсера для cron

cd ~/ozon_parser
source venv/bin/activate

# Добавляем timestamp в лог
echo "$(date '+%Y-%m-%d %H:%M:%S') - Запуск парсера..." >> logs/cron.log

# Запускаем парсер и логируем вывод
python main.py >> logs/cron.log 2>&1

# Код завершения
EXIT_CODE=$?
echo "$(date '+%Y-%m-%d %H:%M:%S') - Завершено с кодом: $EXIT_CODE" >> logs/cron.log
echo "----------------------------------------" >> logs/cron.log

exit $EXIT_CODE
EOF

# Делаем скрипт исполняемым
chmod +x "$PARSER_DIR/run_parser.sh"

echo "✅ Создан скрипт: $PARSER_DIR/run_parser.sh"
echo ""

# Создаем cron задачу
# Запуск каждые 15 минут с 9:00 до 21:00 (МСК)
CRON_ENTRY="*/15 9-21 * * * $PARSER_DIR/run_parser.sh"

# Проверяем, есть ли уже такая задача
if crontab -l 2>/dev/null | grep -q "run_parser.sh"; then
    echo "⚠️  Cron задача уже существует. Обновляем..."
    # Удаляем старую задачу
    crontab -l 2>/dev/null | grep -v "run_parser.sh" | crontab -
fi

# Добавляем новую задачу
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron задача добавлена:"
echo "   $CRON_ENTRY"
echo ""
echo "📋 Расписание:"
echo "   - Запуск каждые 15 минут"
echo "   - Время работы: 9:00 - 21:00 МСК"
echo "   - Логи: $LOG_FILE"
echo ""
echo "🔍 Проверить cron задачи: crontab -l"
echo "📄 Посмотреть логи: tail -f $LOG_FILE"
echo ""
echo "✅ Настройка завершена!"
