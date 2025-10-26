# 🚀 Пошаговая настройка Ozon Parser на Timeweb
# Сервер: 85.193.81.13
# Дата: 27 октября 2025

# ============================================
# ШАГ 1: Создание пользователя на сервере
# ============================================

# В ОТДЕЛЬНОМ PowerShell выполните:
ssh root@85.193.81.13
# Пароль: z7WcXt-QAEkr@L

# На сервере выполните:
adduser ozon
# Придумайте пароль (например: OzonParser2025!)
# Остальные поля - Enter, Enter, Enter...

usermod -aG sudo ozon
id ozon
# Должно быть: groups=1000(ozon),27(sudo)

# Выход
exit

# ============================================
# ШАГ 2: Копирование файлов на сервер
# ============================================

# В ЭТОМ PowerShell (C:\Users\фф\Documents\Apps\Ozon_Parser):

# 2.1. Копирование всех файлов проекта
scp -r *.py *.sh *.md *.txt *.yaml *.example ozon@85.193.81.13:~/

# 2.2. Копирование Google credentials
scp google_credentials.json ozon@85.193.81.13:~/

# 2.3. Копирование .env (если нужно)
# scp .env ozon@85.193.81.13:~/

# ============================================
# ШАГ 3: Подключение как пользователь ozon
# ============================================

ssh ozon@85.193.81.13
# Пароль: тот, что вы создали для ozon

# ============================================
# ШАГ 4: Создание директории проекта
# ============================================

mkdir -p ~/ozon_parser
mv ~/*.py ~/ozon_parser/
mv ~/*.sh ~/ozon_parser/
mv ~/*.md ~/ozon_parser/
mv ~/*.txt ~/ozon_parser/
mv ~/*.yaml ~/ozon_parser/
mv ~/*.json ~/ozon_parser/ 2>/dev/null || true
mv ~/*.example ~/ozon_parser/ 2>/dev/null || true

cd ~/ozon_parser
ls -la

# ============================================
# ШАГ 5: Запуск автоматической установки
# ============================================

chmod +x *.sh
bash deploy.sh

# ВАЖНО: Скрипт спросит Git URL - нажмите Enter, чтобы пропустить
# Установка займёт 5-10 минут

# ============================================
# ШАГ 6: Настройка переменных окружения
# ============================================

nano ~/ozon_parser/.env

# Заполните ВСЕ переменные:
# - API_SECRET_KEY (уже заполнен автоматически)
# - TELEGRAM_BOT_TOKEN=ваш_токен
# - TELEGRAM_CHAT_ID=ваш_chat_id
# - GOOGLE_SHEETS_URL=ваша_ссылка
# - OZON_EMAIL=ваш_email
# - OZON_PASSWORD=ваш_пароль

# Сохранение: Ctrl+O, Enter, Ctrl+X

# ============================================
# ШАГ 7: Проверка Google credentials
# ============================================

ls -la ~/ozon_parser/google_credentials.json
# Должен быть файл размером ~2-3 KB

cat ~/ozon_parser/google_credentials.json | head -5
# Должен показать JSON с ключами

# ============================================
# ШАГ 8: Запуск API сервера (systemd)
# ============================================

bash setup-systemd.sh

# Проверка
sudo systemctl status ozon-parser-api
# Должно быть: Active: active (running)

# Тест API
curl http://localhost:8000/health
# Должен вернуть: {"status":"healthy",...}

# ============================================
# ШАГ 9: Настройка автозапуска (cron)
# ============================================

bash setup-cron.sh

# Проверка
crontab -l
# Должна быть строка: 0 9-21 * * * .../run_parser.sh

# ============================================
# ШАГ 10: Тестовый запуск парсера
# ============================================

cd ~/ozon_parser
source venv/bin/activate
python main.py

# Если всё работает - увидите логи парсинга!

# ============================================
# ШАГ 11: Проверка логов
# ============================================

# Логи API сервера
sudo journalctl -u ozon-parser-api -n 50

# Логи парсера
tail -50 ~/ozon_parser/logs/parser_*.log

# Логи cron (появятся после первого автозапуска)
tail -50 ~/ozon_parser/logs/cron_*.log

# ============================================
# ШАГ 12: Финальные проверки
# ============================================

# Проверка timezone
timedatectl
# Должно быть: Time zone: Europe/Moscow (MSK, +0300)

# Проверка firewall
sudo ufw status
# Должны быть открыты: 22, 80, 443, 8000

# Проверка API с внешнего адреса
curl http://85.193.81.13:8000/health
# Должен работать!

# ============================================
# 🎉 ГОТОВО! Парсер настроен и работает!
# ============================================

# Следующие шаги:
# 1. Настройте Google Apps Script (CLOUD_INIT_GUIDE.md)
# 2. Настройте Nginx + SSL (опционально): bash setup-nginx.sh
# 3. Мониторинг: tail -f ~/ozon_parser/logs/*.log

# Полезные команды:
# - Перезапуск API: sudo systemctl restart ozon-parser-api
# - Проверка статуса: sudo systemctl status ozon-parser-api
# - Логи в реальном времени: sudo journalctl -u ozon-parser-api -f
# - Ручной запуск парсера: cd ~/ozon_parser && source venv/bin/activate && python main.py
