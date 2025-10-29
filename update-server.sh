#!/bin/bash
# Скрипт обновления кода на сервере (Linux/Mac версия)
# Использование: bash update-server.sh

SERVER="ozon@85.193.81.13"
REMOTE_DIR="~/ozon_parser"

echo "🚀 Обновление кода на сервере $SERVER"
echo ""

# Список файлов для обновления
files=(
    "main.py"
    "parser.py"
    "auth.py"
    "notifier.py"
    "config.py"
    "sheets_manager.py"
    "sheets_sync.py"
    "product_matcher.py"
    "bundle_manager.py"
    "excluded_manager.py"
    "session_manager.py"
    "export_data.py"
    "api_server.py"
)

echo "📦 Файлы для обновления:"
for file in "${files[@]}"; do
    echo "  - $file"
done
echo ""

# Подтверждение
read -p "Продолжить обновление? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "❌ Отменено"
    exit 1
fi

echo ""
echo "📤 Копирование файлов..."

# Копируем каждый файл
success=0
failed=0

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -n "  Копирование $file..."
        if scp "$file" "${SERVER}:${REMOTE_DIR}/" > /dev/null 2>&1; then
            echo " ✅"
            ((success++))
        else
            echo " ❌"
            ((failed++))
        fi
    else
        echo "  ⚠️  Файл $file не найден"
    fi
done

echo ""
echo "📊 Результат:"
echo "  ✅ Успешно: $success"
echo "  ❌ Ошибки: $failed"
echo ""

if [ $success -gt 0 ]; then
    echo "🔄 Перезапуск сервисов на сервере..."
    echo ""
    
    # Перезапускаем API сервер (если запущен)
    ssh $SERVER "sudo systemctl restart ozon-parser-api 2>/dev/null || echo 'Сервис не запущен'"
    
    echo ""
    echo "✅ Обновление завершено!"
    echo ""
    echo "💡 Проверьте работу:"
    echo "  ssh $SERVER"
    echo "  cd ~/ozon_parser"
    echo "  source venv/bin/activate"
    echo "  python main.py  # Тестовый запуск"
fi
