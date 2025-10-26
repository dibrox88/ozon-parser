# 🚀 Развёртывание на Timeweb - Краткая инструкция

## Что было создано?

Полная инфраструктура для развёртывания Ozon Parser на сервере Timeweb:

### 📦 Основные компоненты

1. **API Server** (`api_server.py`)
   - FastAPI сервер для удалённого запуска парсера
   - REST API endpoints: `/health`, `/status`, `/trigger`, `/logs`
   - Защита через Bearer token
   - Background tasks для асинхронного выполнения

2. **Автоматическое развёртывание** (`deploy.sh`)
   - Установка всех зависимостей
   - Настройка Python окружения
   - Установка Playwright браузеров
   - Настройка timezone (Москва)

3. **Автозапуск парсера**
   - **systemd** (`setup-systemd.sh`) - API сервер работает постоянно
   - **cron** (`setup-cron.sh`) - запуск парсера каждый час с 9:00 до 21:00 МСК

4. **Google Apps Script** (`google-apps-script.js`)
   - Кнопка в Google Sheets для ручного запуска
   - Проверка статуса парсера
   - Просмотр логов
   - Автоматические триггеры (опционально)

5. **Nginx** (`setup-nginx.sh`, `nginx-config.example`)
   - Reverse proxy для API
   - SSL сертификат (Let's Encrypt)
   - HTTPS поддержка

---

## ⚡ Быстрый старт

### Шаг 1: Подключитесь к серверу Timeweb

```bash
ssh root@YOUR_SERVER_IP
```

### Шаг 2: Создайте пользователя

```bash
adduser ozon
usermod -aG sudo ozon
su - ozon
```

### Шаг 3: Скопируйте файлы на сервер

```powershell
# На вашем Windows компьютере
cd "C:\Users\фф\Documents\Apps\Ozon_Parser"
scp -r * ozon@YOUR_SERVER_IP:~/ozon_parser/
```

### Шаг 4: Запустите автоматическую установку

```bash
# На сервере
cd ~/ozon_parser
chmod +x *.sh
bash deploy.sh
```

### Шаг 5: Настройте переменные окружения

```bash
nano ~/ozon_parser/.env
```

Заполните все значения и сохраните (`Ctrl+O`, `Enter`, `Ctrl+X`).

### Шаг 6: Скопируйте Google credentials

```bash
# На вашем компьютере
scp google_credentials.json ozon@YOUR_SERVER_IP:~/ozon_parser/
```

### Шаг 7: Запустите сервисы

```bash
# API сервер (постоянно работающий)
bash setup-systemd.sh

# Автозапуск по расписанию
bash setup-cron.sh
```

### Шаг 8: Настройте Google Sheets (опционально)

1. Откройте Google Таблицу
2. Расширения → Apps Script
3. Вставьте код из `google-apps-script.js`
4. Измените `API_BASE_URL` и `API_SECRET_KEY`
5. Сохраните и разрешите доступ

---

## 📚 Документация

- **[DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)** - Полная инструкция по развёртыванию
- **[QUICKSTART_DEPLOY.md](QUICKSTART_DEPLOY.md)** - Шпаргалка с командами

---

## 🔑 Важные моменты

1. **API Secret Key** - сгенерирован автоматически в `.env`
   ```bash
   cat ~/ozon_parser/.env | grep API_SECRET_KEY
   ```

2. **Порт 8000** должен быть открыт в firewall
   ```bash
   sudo ufw allow 8000/tcp
   ```

3. **Timezone** должен быть Europe/Moscow
   ```bash
   timedatectl
   ```

4. **Расписание cron** - каждый час с 9:00 до 21:00
   ```bash
   crontab -l
   ```

---

## 🛠️ Управление

### Проверка статуса

```bash
# API сервер
sudo systemctl status ozon-parser-api

# Логи API
sudo journalctl -u ozon-parser-api -f

# Логи парсера
tail -f ~/ozon_parser/logs/parser_*.log

# Логи cron
tail -f ~/ozon_parser/logs/cron_*.log
```

### Управление сервисами

```bash
# Перезапуск API
sudo systemctl restart ozon-parser-api

# Ручной запуск парсера
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

---

## 🌐 API Endpoints

```bash
# Health check
curl http://YOUR_SERVER_IP:8000/health

# Статус (требует авторизацию)
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://YOUR_SERVER_IP:8000/status

# Запуск парсера (требует авторизацию)
curl -X POST \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"source":"manual","force":false}' \
     http://YOUR_SERVER_IP:8000/trigger
```

---

## 🔒 Безопасность

- ✅ API защищён Bearer token
- ✅ .env файл не коммитится в Git
- ✅ google_credentials.json в .gitignore
- ✅ Рекомендуется настроить Nginx + SSL
- ✅ Рекомендуется ограничить доступ по IP

---

## 📞 Troubleshooting

### API не отвечает
- Проверьте статус: `sudo systemctl status ozon-parser-api`
- Проверьте порт: `sudo netstat -tulpn | grep 8000`
- Проверьте firewall: `sudo ufw status`

### Парсер не запускается через cron
- Проверьте логи: `tail -100 ~/ozon_parser/logs/cron_*.log`
- Проверьте права: `ls -la ~/ozon_parser/run_parser.sh`
- Ручной запуск: `bash ~/ozon_parser/run_parser.sh`

### Playwright ошибка
- Переустановите: `playwright install chromium`
- Установите зависимости: `playwright install-deps chromium`

---

## ✅ Что дальше?

1. Протестируйте ручной запуск парсера
2. Дождитесь автоматического запуска по cron
3. Настройте Nginx + SSL для продакшна
4. Настройте мониторинг (Telegram уведомления)
5. Настройте резервное копирование

---

**Версия**: 1.9.0  
**Дата**: 26 октября 2025
