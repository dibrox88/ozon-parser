$SERVER = "ozon@85.193.81.13"
Write-Host "🔄 Restarting Telegram Bot on $SERVER..." -ForegroundColor Yellow
ssh -t $SERVER "sudo systemctl restart ozon-telegram-bot"
Write-Host "✅ Done!" -ForegroundColor Green
