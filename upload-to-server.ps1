$SERVER = "ozon@85.193.81.13"
$REMOTE_DIR = "~/ozon_parser"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Upload Fixed Files to Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $SERVER" -ForegroundColor Gray
Write-Host "Remote: $REMOTE_DIR" -ForegroundColor Gray
Write-Host ""

# Файлы для загрузки (только исправленные)
$files = @("notifier.py", "auth.py")

$success = 0
$failed = 0

foreach ($file in $files) {
    Write-Host "Uploading: $file" -ForegroundColor Yellow
    
    if (-not (Test-Path $file)) {
        Write-Host "  [ERROR] File not found!" -ForegroundColor Red
        $failed++
        continue
    }
    
    $localSize = (Get-Item $file).Length
    Write-Host "  [INFO] Local size: $localSize bytes" -ForegroundColor Gray
    
    # Загружаем файл
    scp $file "${SERVER}:${REMOTE_DIR}/$file" 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [SUCCESS] Uploaded successfully" -ForegroundColor Green
        $success++
    } else {
        Write-Host "  [FAILED] Upload error" -ForegroundColor Red
        $failed++
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Results:" -ForegroundColor White
Write-Host "  Success: $success files" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "  Failed:  $failed files" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($success -gt 0) {
    Write-Host "✅ Files uploaded successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps on server:" -ForegroundColor Yellow
    Write-Host "  1. ssh ozon@85.193.81.13" -ForegroundColor Gray
    Write-Host "  2. cd ~/ozon_parser" -ForegroundColor Gray
    Write-Host "  3. python main.py" -ForegroundColor Gray
    Write-Host ""
}
