$SERVER = "ozon@85.193.81.13"
$REMOTE_DIR = "~/ozon_parser"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Download Files from Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $SERVER" -ForegroundColor Gray
Write-Host "Remote: $REMOTE_DIR" -ForegroundColor Gray
Write-Host ""

$files = @("ozon_orders.json", "product_mappings.json")

$success = 0
$failed = 0

foreach ($file in $files) {
    Write-Host "Downloading: $file" -ForegroundColor Yellow
    
    if (Test-Path $file) {
        $oldSize = (Get-Item $file).Length
        Copy-Item $file "$file.backup" -Force
        Write-Host "  [BACKUP] Created backup (old size: $oldSize bytes)" -ForegroundColor Gray
    }
    
    scp "${SERVER}:${REMOTE_DIR}/$file" . 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        $newSize = (Get-Item $file).Length
        Write-Host "  [SUCCESS] Downloaded ($newSize bytes)" -ForegroundColor Green
        $success++
    } else {
        Write-Host "  [FAILED] Could not download" -ForegroundColor Red
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
