# 🚀 Развёртывание Ozon Parser на Timeweb

Подробная инструкция по развёртыванию парсера на сервере Timeweb с автоматическим запуском и возможностью вызова через Google Apps Script.

---

## 📋 Содержание

1. [Требования](#требования)
2. [Подготовка сервера Timeweb](#подготовка-сервера-timeweb)
3. [Установка проекта](#установка-проекта)
4. [Настройка автоматического запуска](#настройка-автоматического-запуска)
5. [Настройка API для App Script](#настройка-api-для-app-script)
6. [Интеграция с Google Sheets](#интеграция-с-google-sheets)
7. [Мониторинг и обслуживание](#мониторинг-и-обслуживание)
8. [Troubleshooting](#troubleshooting)

---

## 🔧 Требования

### На стороне Timeweb:
- **VPS**: минимум 2 ГБ RAM, 2 CPU
- **ОС**: Ubuntu 20.04/22.04 LTS или Debian 11/12
- **Диск**: минимум 10 ГБ свободного места
- **SSH доступ**: с правами sudo

### Предварительная подготовка:
- Telegram Bot Token (от @BotFather)
- Google Sheets API credentials (google_credentials.json)
- Данные для входа в Ozon

---

## 🖥️ Подготовка сервера Timeweb

### 1. Заказ VPS на Timeweb

1. Перейдите на [timeweb.cloud](https://timeweb.cloud/)
2. Выберите "Cloud серверы" → "Создать сервер"
3. Рекомендуемая конфигурация:
   - **ОС**: Ubuntu 22.04 LTS
   - **RAM**: 2 ГБ (минимум)
   - **CPU**: 2 ядра
   - **Диск**: 20 ГБ SSD
   - **Регион**: Москва (для минимальной задержки)

4. Дождитесь создания сервера и получите:
   - IP-адрес сервера
   - Пароль root (придёт на email)

### 2. Первое подключение к серверу

```bash
# Подключение по SSH (замените YOUR_SERVER_IP на ваш IP)
ssh root@YOUR_SERVER_IP

# При первом подключении согласитесь добавить сервер в known_hosts (yes)
```

### 3. Создание нового пользователя (рекомендуется)

```bash
# Создание пользователя ozon
adduser ozon

# Добавление пользователя в группу sudo
usermod -aG sudo ozon

# Переключение на нового пользователя
su - ozon
```

**Важно**: Все дальнейшие действия выполняем от имени пользователя `ozon` (не root)!

---

## 📦 Установка проекта

### 1. Копирование файлов на сервер

#### Вариант А: Через Git (рекомендуется)

```bash
# На сервере
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git ozon_parser
cd ozon_parser
```

#### Вариант Б: Через SCP (с вашего компьютера)

```powershell
# На вашем Windows компьютере (PowerShell)
cd "C:\Users\фф\Documents\Apps\Ozon_Parser"

# Копирование всех файлов на сервер
scp -r * ozon@YOUR_SERVER_IP:~/ozon_parser/
```

### 2. Запуск автоматической установки

```bash
# На сервере
cd ~/ozon_parser
chmod +x deploy.sh
bash deploy.sh
```

Скрипт автоматически установит:
- ✅ Python 3 и зависимости
- ✅ Playwright и браузеры
- ✅ Nginx, Supervisor
- ✅ Настройку часового пояса (МСК)
- ✅ Создаст виртуальное окружение
- ✅ Установит все Python пакеты

### 3. Настройка переменных окружения

```bash
# Редактирование .env файла
nano ~/ozon_parser/.env
```

Замените значения на свои:

```env
# API Secret Key (НЕ МЕНЯЙТЕ - автоматически сгенерирован)
API_SECRET_KEY=ваш_автоматически_сгенерированный_ключ

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Google Sheets
GOOGLE_CREDENTIALS_FILE=google_credentials.json
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit

# Ozon credentials
OZON_EMAIL=your_email@example.com
OZON_PASSWORD=your_secure_password
```

**Сохранение**: `Ctrl+O` → `Enter` → `Ctrl+X`

### 4. Копирование Google Credentials

```bash
# На вашем Windows компьютере
scp google_credentials.json ozon@YOUR_SERVER_IP:~/ozon_parser/

# На сервере - проверка
ls -la ~/ozon_parser/google_credentials.json
```

---

## ⏰ Настройка автоматического запуска

### 1. Настройка API сервера (systemd)

API сервер будет постоянно работать и принимать запросы на запуск парсера.

```bash
cd ~/ozon_parser
chmod +x setup-systemd.sh
bash setup-systemd.sh
```

**Проверка работы**:

```bash
# Статус сервиса
sudo systemctl status ozon-parser-api

# Должно быть: Active: active (running)

# Проверка доступности API
curl http://localhost:8000/
# Ответ: {"service":"Ozon Parser API","version":"1.0.0",...}
```

### 2. Настройка расписания (cron)

Автоматический запуск парсера каждый час с 9:00 до 21:00 по Москве.

```bash
cd ~/ozon_parser
chmod +x setup-cron.sh
bash setup-cron.sh
```

**Проверка расписания**:

```bash
# Просмотр crontab
crontab -l

# Должна быть строка:
# 0 9-21 * * * /home/ozon/ozon_parser/run_parser.sh
```

**Логи cron**:

```bash
# Просмотр логов
tail -f ~/ozon_parser/logs/cron_$(date +%Y%m%d).log
```

---

## 🌐 Настройка API для App Script

### 1. Получение API ключа

```bash
# Просмотр вашего секретного ключа
cat ~/ozon_parser/.env | grep API_SECRET_KEY

# Скопируйте значение - оно понадобится для App Script
```

### 2. Открытие порта 8000 (если используется firewall)

```bash
# Проверка firewall
sudo ufw status

# Если активен - открываем порт
sudo ufw allow 8000/tcp
sudo ufw reload
```

### 3. Тестирование API

```bash
# Локальный тест
curl http://localhost:8000/health

# Тест с другого компьютера (замените YOUR_SERVER_IP)
curl http://YOUR_SERVER_IP:8000/health
```

**Важно**: Для продакшна рекомендуется настроить:
- ✅ Nginx reverse proxy
- ✅ SSL сертификат (Let's Encrypt)
- ✅ Ограничение доступа по IP

---

## 📊 Интеграция с Google Sheets

### 1. Открытие Apps Script

1. Откройте вашу Google Таблицу
2. Меню: **Расширения** → **Apps Script**
3. Удалите весь существующий код

### 2. Вставка кода

1. Скопируйте содержимое файла `google-apps-script.js`
2. Вставьте в редактор Apps Script
3. Измените настройки в начале файла:

```javascript
// URL вашего API сервера на Timeweb
const API_BASE_URL = 'http://YOUR_SERVER_IP:8000';

// API секретный ключ (из .env файла)
const API_SECRET_KEY = 'ваш_секретный_ключ_из_env';
```

4. Сохраните: `Ctrl+S` или иконка дискеты

### 3. Разрешение доступа

1. Нажмите **▶️ Выполнить** (любую функцию)
2. Google попросит разрешение - нажмите **Проверить разрешения**
3. Выберите ваш аккаунт Google
4. Нажмите **Дополнительные** → **Перейти на страницу...**
5. Разрешите доступ

### 4. Использование меню

После настройки в Google Sheets появится меню **🤖 Ozon Parser**:

- **▶️ Запустить парсинг** - запуск парсера вручную
- **📊 Проверить статус** - проверка текущего статуса
- **📋 Показать логи** - просмотр последних логов
- **⚙️ Настройки API** - просмотр настроек

### 5. Автоматический запуск через триггеры (опционально)

1. В Apps Script: **Триггеры** (иконка будильника слева)
2. **+ Добавить триггер**
3. Настройки:
   - Функция: `scheduledTrigger`
   - Источник события: **По времени**
   - Тип триггера: **Таймер на определённый час**
   - Выберите часы: 9, 10, 11, ..., 21 (по одному триггеру на каждый час)
4. Сохраните

---

## 🔍 Мониторинг и обслуживание

### Проверка статуса сервисов

```bash
# Статус API сервера
sudo systemctl status ozon-parser-api

# Логи API сервера в реальном времени
sudo journalctl -u ozon-parser-api -f

# Логи парсера
tail -f ~/ozon_parser/logs/parser_*.log

# Логи cron
tail -f ~/ozon_parser/logs/cron_*.log
```

### Перезапуск сервисов

```bash
# Перезапуск API сервера
sudo systemctl restart ozon-parser-api

# Ручной запуск парсера
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

### Обновление кода

```bash
cd ~/ozon_parser

# Через Git
git pull origin master

# Перезапуск API сервера после обновления
sudo systemctl restart ozon-parser-api
```

### Резервное копирование

```bash
# Создание бэкапа
tar -czf ~/ozon_parser_backup_$(date +%Y%m%d).tar.gz \
    ~/ozon_parser/.env \
    ~/ozon_parser/google_credentials.json \
    ~/ozon_parser/*.json \
    ~/ozon_parser/logs/

# Скачивание бэкапа на локальный компьютер
scp ozon@YOUR_SERVER_IP:~/ozon_parser_backup_*.tar.gz ./
```

---

## 🐛 Troubleshooting

### Проблема: API сервер не запускается

```bash
# Проверка логов
sudo journalctl -u ozon-parser-api -n 50

# Проверка занятости порта
sudo netstat -tulpn | grep 8000

# Проверка переменных окружения
sudo systemctl show ozon-parser-api | grep Environment
```

### Проблема: Парсер не запускается через cron

```bash
# Проверка прав на скрипт
ls -la ~/ozon_parser/run_parser.sh

# Должно быть: -rwxr-xr-x

# Ручной запуск скрипта для проверки
bash ~/ozon_parser/run_parser.sh

# Проверка логов cron
grep CRON /var/log/syslog
```

### Проблема: Playwright не может запустить браузер

```bash
# Переустановка браузеров Playwright
cd ~/ozon_parser
source venv/bin/activate
playwright install chromium
playwright install-deps chromium
```

### Проблема: Google Apps Script не может подключиться

1. Проверьте, открыт ли порт 8000:
   ```bash
   sudo ufw status
   sudo ufw allow 8000/tcp
   ```

2. Проверьте API ключ в Apps Script совпадает с .env

3. Используйте внешний IP (не localhost) в `API_BASE_URL`

### Проблема: Timezone неправильный

```bash
# Проверка текущего времени
date

# Настройка timezone на МСК
sudo timedatectl set-timezone Europe/Moscow

# Проверка
timedatectl
```

---

## 📚 Дополнительные рекомендации

### Безопасность

1. **Смените SSH порт**:
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Измените Port 22 на Port 2222
   sudo systemctl restart sshd
   ```

2. **Настройте firewall**:
   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 2222/tcp  # SSH
   sudo ufw allow 8000/tcp  # API
   sudo ufw enable
   ```

3. **Используйте SSH ключи** вместо паролей

### Производительность

1. **Ограничьте количество одновременных запусков** в cron
2. **Настройте ротацию логов**:
   ```bash
   # Создать /etc/logrotate.d/ozon-parser
   sudo nano /etc/logrotate.d/ozon-parser
   ```

   Содержимое:
   ```
   /home/ozon/ozon_parser/logs/*.log {
       daily
       rotate 7
       compress
       missingok
       notifempty
   }
   ```

### Мониторинг

Настройте уведомления о сбоях через Telegram:
- Добавьте в cron скрипт проверки статуса API
- Отправляйте уведомления при ошибках

---

## 🎯 Итоговая проверка

После завершения всех шагов проверьте:

- [ ] API сервер работает: `curl http://YOUR_SERVER_IP:8000/health`
- [ ] Cron настроен: `crontab -l`
- [ ] Systemd сервис активен: `sudo systemctl status ozon-parser-api`
- [ ] Timezone = Europe/Moscow: `timedatectl`
- [ ] Google Apps Script подключается к API
- [ ] Меню появилось в Google Sheets
- [ ] Тестовый запуск парсера работает

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи (см. раздел "Мониторинг")
2. Убедитесь, что все переменные окружения заполнены
3. Проверьте сетевое подключение и firewall
4. Создайте issue в репозитории GitHub

---

**Версия**: 1.0.0  
**Дата**: 26 октября 2025  
**Автор**: Ozon Parser Team
