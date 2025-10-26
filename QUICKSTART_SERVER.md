# 🚀 Быстрая настройка - Выполняйте команды по порядку

## ✅ ШАГ 1: ФАЙЛЫ СКОПИРОВАНЫ!

Все файлы успешно скопированы на сервер 85.193.81.13

---

## 📋 ШАГ 2: ПОДКЛЮЧИТЕСЬ К СЕРВЕРУ

Откройте новое окно PowerShell и выполните:

```bash
ssh ozon@85.193.81.13
```

**Пароль ozon**: (тот что вы создали, или OzonParser2025!)

---

## 📦 ШАГ 3: ОРГАНИЗУЙТЕ ФАЙЛЫ

На сервере выполните:

```bash
# Создание директории проекта
mkdir -p ~/ozon_parser

# Перемещение всех файлов в проект
mv ~/*.py ~/ozon_parser/
mv ~/*.sh ~/ozon_parser/
mv ~/*.md ~/ozon_parser/
mv ~/*.txt ~/ozon_parser/
mv ~/*.js ~/ozon_parser/
mv ~/*.json ~/ozon_parser/
mv ~/*.example ~/ozon_parser/
mv ~/.env ~/ozon_parser/

# Переход в проект
cd ~/ozon_parser

# Проверка файлов
ls -la
```

**Должны увидеть**: main.py, parser.py, deploy.sh, google_credentials.json, .env и др.

---

## 🔧 ШАГ 4: ЗАПУСК АВТОМАТИЧЕСКОЙ УСТАНОВКИ

```bash
# Делаем скрипты исполняемыми
chmod +x *.sh

# ВАЖНО: Проверьте что вы в правильной директории
pwd
# Должно быть: /home/ozon/ozon_parser

# Запуск установки (займёт 5-10 минут)
bash deploy.sh
```

**Что спросит скрипт**:
- "Введите URL вашего git-репозитория" - **нажмите Enter** (пропустить)

**Что установится**:
- Python 3 и pip
- Playwright и браузеры
- Все зависимости из requirements-production.txt
- Настроится timezone на Москву
- Создастся виртуальное окружение

---

## 🔐 ШАГ 5: ПРОВЕРКА .ENV

```bash
# Просмотр .env
cat ~/ozon_parser/.env
```

**Проверьте что есть**:
- ✅ TELEGRAM_BOT_TOKEN='...'
- ✅ TELEGRAM_CHAT_ID='...'
- ✅ OZON_EMAIL='...'
- ✅ HEADLESS=True (ВАЖНО!)
- ✅ GOOGLE_SHEETS_URL='...'

Если что-то не так:
```bash
nano ~/ozon_parser/.env
# Отредактируйте, сохраните: Ctrl+O, Enter, Ctrl+X
```

---

## 🚀 ШАГ 6: ЗАПУСК API СЕРВЕРА

```bash
cd ~/ozon_parser
bash setup-systemd.sh
```

**Проверка**:
```bash
sudo systemctl status ozon-parser-api
# Должно быть: Active: active (running) зелёным цветом
```

**Тест API**:
```bash
curl http://localhost:8000/health
# Должен вернуть JSON: {"status":"healthy",...}
```

---

## ⏰ ШАГ 7: НАСТРОЙКА АВТОЗАПУСКА (CRON)

```bash
cd ~/ozon_parser
bash setup-cron.sh
```

**Проверка**:
```bash
crontab -l
# Должна быть строка: 0 9-21 * * * /home/ozon/ozon_parser/run_parser.sh
```

---

## 🧪 ШАГ 8: ТЕСТОВЫЙ ЗАПУСК ПАРСЕРА

```bash
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

**Что должно произойти**:
- ✅ Подключение к Telegram
- ✅ Загрузка сессии Ozon
- ✅ Парсинг заказов
- ✅ Отправка в Google Sheets
- ✅ Уведомления в Telegram

**Если есть ошибки** - скопируйте текст ошибки и сообщите мне!

---

## 🔍 ШАГ 9: ПРОВЕРКА ЛОГОВ

```bash
# Логи API сервера
sudo journalctl -u ozon-parser-api -n 50

# Логи парсера (после тестового запуска)
ls -la ~/ozon_parser/logs/
tail -50 ~/ozon_parser/logs/parser_*.log

# Логи cron (появятся после автозапуска)
tail -50 ~/ozon_parser/logs/cron_*.log
```

---

## ✅ ШАГ 10: ФИНАЛЬНЫЕ ПРОВЕРКИ

```bash
# Проверка timezone
timedatectl
# Должно быть: Time zone: Europe/Moscow (MSK, +0300)

# Проверка firewall
sudo ufw status
# Должны быть открыты: 22, 80, 443, 8000

# Проверка Python
python3 --version
# Должно быть: Python 3.12.x

# Проверка виртуального окружения
which python
# Должно быть: /home/ozon/ozon_parser/venv/bin/python
```

---

## 🌐 ШАГ 11: ТЕСТ API С ВНЕШНЕГО АДРЕСА

**На вашем компьютере** (в PowerShell):

```powershell
curl http://85.193.81.13:8000/health
```

Должен вернуть JSON с информацией о здоровье сервиса.

**Если не работает** - проверьте firewall на сервере:
```bash
sudo ufw status
sudo ufw allow 8000/tcp
```

---

## 🎉 ГОТОВО!

Если всё работает:
- ✅ API сервер запущен
- ✅ Cron настроен (будет запускаться каждый час с 9:00 до 21:00)
- ✅ Парсер работает
- ✅ Логи записываются

---

## 📱 ДОПОЛНИТЕЛЬНО: Google Apps Script

Чтобы управлять парсером из Google Sheets:

1. Откройте вашу таблицу
2. Расширения → Apps Script
3. Вставьте код из файла `google-apps-script.js`
4. Измените:
   ```javascript
   const API_BASE_URL = 'http://85.193.81.13:8000';
   const API_SECRET_KEY = 'ваш_ключ';
   ```
5. Получите API ключ на сервере:
   ```bash
   cat ~/ozon_parser/.env | grep API_SECRET_KEY
   ```

---

## 🆘 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

### Парсер не запускается
```bash
# Проверка логов
tail -100 ~/ozon_parser/logs/parser_*.log

# Ручной запуск для отладки
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

### API сервер не работает
```bash
# Статус сервиса
sudo systemctl status ozon-parser-api

# Перезапуск
sudo systemctl restart ozon-parser-api

# Логи
sudo journalctl -u ozon-parser-api -n 100
```

### Playwright ошибка "Browser not found"
```bash
cd ~/ozon_parser
source venv/bin/activate
playwright install chromium
playwright install-deps chromium
```

---

## 📞 Полезные команды

```bash
# Перезапуск API
sudo systemctl restart ozon-parser-api

# Просмотр логов в реальном времени
sudo journalctl -u ozon-parser-api -f

# Ручной запуск парсера
cd ~/ozon_parser && source venv/bin/activate && python main.py

# Проверка расписания cron
crontab -l

# Редактирование .env
nano ~/ozon_parser/.env

# Проверка использования ресурсов
htop  # или просто: top
free -h  # память
df -h  # диск
```

---

**Следуйте шагам по порядку и сообщайте о результатах!** 🚀
