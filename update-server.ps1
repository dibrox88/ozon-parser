# Скрипт обновления кода на сервере
# Использование: .\update-server.ps1

$SERVER = "ozon@85.193.81.13"
$REMOTE_DIR = "~/ozon_parser"

Write-Host "🚀 Обновление кода на сервере $SERVER" -ForegroundColor Cyan
Write-Host ""

# Список файлов для обновления
$files = @(
    "main.py",
    "parser.py",
    "auth.py",
    "notifier.py",
    "config.py",
    "sheets_manager.py",
    "sheets_sync.py",
    "product_matcher.py",
    "bundle_manager.py",
    "excluded_manager.py",
    "session_manager.py",
    "export_data.py",
    "api_server.py"
)

Write-Host "📦 Файлы для обновления:" -ForegroundColor Yellow
$files | ForEach-Object { Write-Host "  - $_" }
Write-Host ""

# Подтверждение
$confirm = Read-Host "Продолжить обновление? (y/n)"
if ($confirm -ne "y") {
    Write-Host "❌ Отменено" -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "📤 Копирование файлов..." -ForegroundColor Green

# Копируем каждый файл
$success = 0
$failed = 0

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  Копирование $file..." -NoNewline
        scp $file "${SERVER}:${REMOTE_DIR}/"
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅" -ForegroundColor Green
            $success++
        } else {
            Write-Host " ❌" -ForegroundColor Red
            $failed++
        }
    } else {
        Write-Host "  ⚠️  Файл $file не найден" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "📊 Результат:" -ForegroundColor Cyan
Write-Host "  ✅ Успешно: $success" -ForegroundColor Green
Write-Host "  ❌ Ошибки: $failed" -ForegroundColor Red
Write-Host ""

if ($success -gt 0) {
    Write-Host "🔄 Перезапуск сервисов на сервере..." -ForegroundColor Yellow
    Write-Host ""
    
    # Перезапускаем API сервер (если запущен)
    ssh $SERVER "sudo systemctl restart ozon-parser-api 2>/dev/null || echo 'Сервис не запущен'"
    
    Write-Host ""
    Write-Host "✅ Обновление завершено!" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 Проверьте работу:" -ForegroundColor Cyan
    Write-Host "  ssh $SERVER" -ForegroundColor Gray
    Write-Host "  cd ~/ozon_parser" -ForegroundColor Gray
    Write-Host "  source venv/bin/activate" -ForegroundColor Gray
    Write-Host "  python main.py  # Тестовый запуск" -ForegroundColor Gray
}
