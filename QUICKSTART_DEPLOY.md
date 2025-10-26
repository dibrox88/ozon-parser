# 🚀 Быстрый старт на Timeweb

Краткая шпаргалка для развёртывания Ozon Parser на сервере Timeweb.

---

## ⚡ За 5 минут

### 1. Подключение к серверу

```bash
ssh root@YOUR_SERVER_IP
```

### 2. Создание пользователя

```bash
adduser ozon
usermod -aG sudo ozon
su - ozon
```

### 3. Копирование файлов

```bash
# На вашем компьютере (PowerShell)
scp -r * ozon@YOUR_SERVER_IP:~/ozon_parser/
```

### 4. Автоматическая установка

```bash
# На сервере
cd ~/ozon_parser
chmod +x *.sh
bash deploy.sh
```

### 5. Настройка .env

```bash
nano ~/ozon_parser/.env
```

Заполните:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GOOGLE_SHEETS_URL`
- `OZON_EMAIL`
- `OZON_PASSWORD`

Сохраните: `Ctrl+O` → `Enter` → `Ctrl+X`

### 6. Копирование Google Credentials

```bash
# На вашем компьютере
scp google_credentials.json ozon@YOUR_SERVER_IP:~/ozon_parser/
```

### 7. Запуск сервисов

```bash
# API сервер (systemd)
bash setup-systemd.sh

# Автозапуск по расписанию (cron)
bash setup-cron.sh
```

### 8. Проверка

```bash
# Проверка API
curl http://localhost:8000/health

# Проверка статуса
sudo systemctl status ozon-parser-api

# Проверка cron
crontab -l
```

---

## 📝 Основные команды

### Управление API сервером

```bash
# Статус
sudo systemctl status ozon-parser-api

# Перезапуск
sudo systemctl restart ozon-parser-api

# Остановка
sudo systemctl stop ozon-parser-api

# Логи
sudo journalctl -u ozon-parser-api -f
```

### Управление cron

```bash
# Просмотр расписания
crontab -l

# Редактирование
crontab -e

# Логи cron
tail -f ~/ozon_parser/logs/cron_*.log
```

### Ручной запуск парсера

```bash
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

---

## 🔑 Получение API ключа для App Script

```bash
cat ~/ozon_parser/.env | grep API_SECRET_KEY
```

Скопируйте значение и используйте в Google Apps Script.

---

## 🌐 Настройка в Google Sheets

1. Откройте Google Таблицу
2. **Расширения** → **Apps Script**
3. Вставьте код из `google-apps-script.js`
4. Измените:
   ```javascript
   const API_BASE_URL = 'http://YOUR_SERVER_IP:8000';
   const API_SECRET_KEY = 'ваш_ключ_из_env';
   ```
5. Сохраните (`Ctrl+S`)
6. Разрешите доступ при первом запуске

---

## 🛡️ Nginx + SSL (опционально)

```bash
# Установка Nginx reverse proxy
bash setup-nginx.sh

# Следуйте инструкциям на экране
```

После настройки:
- HTTP: `http://your-domain.com`
- HTTPS: `https://your-domain.com` (если установлен SSL)

Измените в Apps Script:
```javascript
const API_BASE_URL = 'https://your-domain.com';
```

---

## 🐛 Проблемы?

### API не отвечает

```bash
# Проверка порта
sudo netstat -tulpn | grep 8000

# Проверка firewall
sudo ufw status
sudo ufw allow 8000/tcp
```

### Парсер не запускается

```bash
# Проверка логов
tail -100 ~/ozon_parser/logs/parser_*.log

# Ручной запуск для отладки
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

### Google Apps Script не подключается

1. Проверьте API_SECRET_KEY совпадает с .env
2. Используйте внешний IP (не localhost)
3. Откройте порт 8000 в firewall

---

## 📊 Мониторинг

### Просмотр логов в реальном времени

```bash
# API сервер
sudo journalctl -u ozon-parser-api -f

# Парсер
tail -f ~/ozon_parser/logs/parser_*.log

# Cron
tail -f ~/ozon_parser/logs/cron_*.log
```

### Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Статус парсера (нужен API ключ)
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/status
```

---

## 🔄 Обновление

```bash
cd ~/ozon_parser
git pull
sudo systemctl restart ozon-parser-api
```

---

## 📅 Расписание запуска

По умолчанию: **каждый час с 9:00 до 21:00 (МСК)**

Изменить расписание:
```bash
crontab -e
```

Примеры расписаний:
```bash
# Каждые 2 часа с 9:00 до 21:00
0 9-21/2 * * * ~/ozon_parser/run_parser.sh

# Только в будние дни
0 9-21 * * 1-5 ~/ozon_parser/run_parser.sh

# Каждый день в 10:00
0 10 * * * ~/ozon_parser/run_parser.sh
```

---

## ✅ Чеклист после установки

- [ ] API сервер работает
- [ ] Cron настроен
- [ ] .env заполнен
- [ ] google_credentials.json скопирован
- [ ] Timezone = Europe/Moscow
- [ ] Firewall настроен
- [ ] Google Apps Script подключён
- [ ] Тестовый запуск прошёл успешно

---

**Полная документация**: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)
