$SERVER = "ozon@85.193.81.13"
Write-Host "🔄 Restarting Telegram Bot on $SERVER..." -ForegroundColor Yellow
ssh -t $SERVER "cd ~/ozon_parser && ./stop_telegram_bot.sh && ./start_telegram_bot.sh"
Write-Host "✅ Done!" -ForegroundColor Green
