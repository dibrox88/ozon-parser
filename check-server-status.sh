#!/bin/bash
# Скрипт проверки текущего состояния сервера

echo "=========================================="
echo "🔍 ПРОВЕРКА СОСТОЯНИЯ СЕРВЕРА"
echo "=========================================="
echo ""

# Проверка текущей директории
echo "📍 Текущая директория:"
pwd
echo ""

# Проверка домашней директории
echo "📂 Содержимое домашней директории:"
ls -lah ~ | head -20
echo ""

# Проверка директории проекта
echo "📦 Проверка директории ozon_parser:"
if [ -d ~/ozon_parser ]; then
    echo "✅ Директория ~/ozon_parser существует"
    echo ""
    echo "📋 Содержимое директории ozon_parser:"
    ls -lah ~/ozon_parser | head -30
else
    echo "❌ Директория ~/ozon_parser НЕ найдена"
    echo "⚠️  Нужно выполнить: mkdir -p ~/ozon_parser"
fi
echo ""

# Проверка важных файлов
echo "🔍 Проверка важных файлов:"
files=("main.py" "parser.py" "deploy.sh" ".env" "google_credentials.json")
for file in "${files[@]}"; do
    if [ -f ~/$file ]; then
        echo "✅ ~/$file найден"
    elif [ -f ~/ozon_parser/$file ]; then
        echo "✅ ~/ozon_parser/$file найден"
    else
        echo "❌ $file НЕ найден"
    fi
done
echo ""

# Проверка Python
echo "🐍 Проверка Python:"
which python3
python3 --version
echo ""

# Проверка виртуального окружения
echo "📦 Проверка виртуального окружения:"
if [ -d ~/ozon_parser/venv ]; then
    echo "✅ Виртуальное окружение создано"
else
    echo "❌ Виртуальное окружение НЕ создано"
    echo "⚠️  Нужно запустить: bash deploy.sh"
fi
echo ""

# Проверка timezone
echo "⏰ Timezone:"
timedatectl | grep "Time zone"
echo ""

echo "=========================================="
echo "✅ ПРОВЕРКА ЗАВЕРШЕНА"
echo "=========================================="
