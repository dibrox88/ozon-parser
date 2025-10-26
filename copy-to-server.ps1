# PowerShell скрипт для копирования файлов на сервер Timeweb
# Запускайте из директории проекта: .\copy-to-server.ps1

$SERVER_IP = "85.193.81.13"
$SERVER_USER = "ozon"

Write-Host "🚀 Копирование файлов на сервер Timeweb..." -ForegroundColor Green
Write-Host "Сервер: $SERVER_IP" -ForegroundColor Cyan
Write-Host "Пользователь: $SERVER_USER" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия важных файлов
Write-Host "📋 Проверка файлов..." -ForegroundColor Yellow

$requiredFiles = @(
    "main.py",
    "parser.py",
    "deploy.sh",
    "google_credentials.json"
)

$missing = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missing += $file
    }
}

if ($missing.Count -gt 0) {
    Write-Host "❌ Отсутствуют файлы:" -ForegroundColor Red
    foreach ($file in $missing) {
        Write-Host "   - $file" -ForegroundColor Red
    }
    exit 1
}

Write-Host "✅ Все важные файлы найдены" -ForegroundColor Green
Write-Host ""

# Копирование файлов
Write-Host "📦 Копирование Python файлов..." -ForegroundColor Yellow
scp *.py ${SERVER_USER}@${SERVER_IP}:~/

Write-Host "📦 Копирование скриптов..." -ForegroundColor Yellow
scp *.sh ${SERVER_USER}@${SERVER_IP}:~/

Write-Host "📦 Копирование документации..." -ForegroundColor Yellow
scp *.md ${SERVER_USER}@${SERVER_IP}:~/

Write-Host "📦 Копирование конфигов..." -ForegroundColor Yellow
scp *.txt *.yaml *.example *.js ${SERVER_USER}@${SERVER_IP}:~/

Write-Host "📦 Копирование Google credentials..." -ForegroundColor Yellow
scp google_credentials.json ${SERVER_USER}@${SERVER_IP}:~/

Write-Host "📦 Копирование .env для сервера..." -ForegroundColor Yellow
scp .env.server ${SERVER_USER}@${SERVER_IP}:~/.env

Write-Host ""
Write-Host "✅ Все файлы скопированы!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Подключитесь к серверу: ssh $SERVER_USER@$SERVER_IP" -ForegroundColor White
Write-Host "2. Создайте директорию: mkdir -p ~/ozon_parser" -ForegroundColor White
Write-Host "3. Переместите файлы: mv ~/*.py ~/*.sh ~/*.md ~/*.txt ~/*.json ~/ozon_parser/" -ForegroundColor White
Write-Host "4. Запустите установку: cd ~/ozon_parser && bash deploy.sh" -ForegroundColor White
Write-Host ""
Write-Host "📚 Подробная инструкция в файле: SETUP_STEPS.md" -ForegroundColor Cyan
