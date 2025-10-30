# Руководство по деплою на Amvera.ru

## 📋 Оглавление
1. [Подготовка проекта](#подготовка-проекта)
2. [Регистрация на Amvera](#регистрация-на-amvera)
3. [Создание проекта](#создание-проекта)
4. [Настройка переменных окружения](#настройка-переменных-окружения)
5. [Деплой приложения](#деплой-приложения)
6. [Проверка работы](#проверка-работы)
7. [Настройка автоматического запуска](#настройка-автоматического-запуска)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Подготовка проекта

### Файлы для деплоя
В проекте уже созданы необходимые файлы:

- ✅ `Dockerfile` - конфигурация контейнера
- ✅ `.dockerignore` - исключения для Docker
- ✅ `amvera.yml` - конфигурация для Amvera
- ✅ `requirements.txt` - Python зависимости (обновлён с fastapi и uvicorn)
- ✅ `api_server.py` - API сервер на FastAPI

### Что будет работать на Amvera
- ✅ API сервер на порту 8000
- ✅ Headless режим Playwright (без GUI)
- ✅ Автоматический парсинг по расписанию (через cron или App Script)
- ✅ Telegram уведомления
- ✅ Синхронизация с Google Sheets

### Что НЕ будет работать
- ❌ Интерактивная авторизация (нужно экспортировать cookies локально)
- ❌ QR-код сканирование (только email авторизация)
- ❌ Графический интерфейс браузера

---

## 🔐 Регистрация на Amvera

1. Перейдите на https://amvera.ru/
2. Зарегистрируйтесь через GitHub, GitLab или Email
3. Подтвердите email если требуется
4. Войдите в личный кабинет

---

## 📦 Создание проекта

### Вариант 1: Через GitHub (рекомендуется)

1. **Создайте репозиторий на GitHub**:
   ```bash
   # Если ещё не создан репозиторий
   git init
   git add .
   git commit -m "feat: подготовка к деплою на Amvera"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ozon-parser.git
   git push -u origin main
   ```

2. **В Amvera**:
   - Нажмите "Создать проект"
   - Выберите "Из Git репозитория"
   - Подключите GitHub аккаунт
   - Выберите репозиторий `ozon-parser`
   - Выберите ветку `main`

### Вариант 2: Через CLI

1. **Установите Amvera CLI**:
   ```bash
   npm install -g @amvera/cli
   # или
   curl -fsSL https://cli.amvera.io/install.sh | sh
   ```

2. **Авторизуйтесь**:
   ```bash
   amvera login
   ```

3. **Инициализируйте проект**:
   ```bash
   cd C:\Users\фф\Documents\Apps\Ozon_Parser
   amvera init
   ```

4. **Задеплойте**:
   ```bash
   amvera deploy
   ```

---

## ⚙️ Настройка переменных окружения

В веб-интерфейсе Amvera перейдите в раздел **"Переменные окружения"** и добавьте:

### Обязательные переменные:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Ozon
OZON_EMAIL=your@email.com
OZON_USER_ID=46206571

# Google Sheets
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit

# API Security
API_SECRET_KEY=your_very_secret_key_here_min_32_chars

# Browser
HEADLESS=true
```

### Опциональные переменные:

```env
# Ozon телефон (опционально)
OZON_PHONE=+79991234567

# Google Credentials (если нужно)
GOOGLE_CREDENTIALS_FILE=google_credentials.json
```

### Важно! Google Credentials

Если у вас есть файл `google_credentials.json`, его нужно добавить как **секрет**:

1. В Amvera перейдите в **"Секреты"**
2. Создайте секрет с именем `GOOGLE_CREDENTIALS_JSON`
3. Скопируйте содержимое файла `google_credentials.json` в значение секрета
4. В коде (если нужно) можно получить через:
   ```python
   import os
   import json
   
   credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
   if credentials_json:
       credentials = json.loads(credentials_json)
   ```

---

## 🚀 Деплой приложения

### Автоматический деплой (через GitHub)

1. Сделайте commit и push в GitHub:
   ```bash
   git add .
   git commit -m "feat: добавлена конфигурация для Amvera"
   git push origin main
   ```

2. Amvera автоматически запустит деплой при push в `main` ветку

3. Следите за логами в веб-интерфейсе Amvera

### Ручной деплой (через CLI)

```bash
cd C:\Users\фф\Documents\Apps\Ozon_Parser
amvera deploy
```

### Проверка статуса деплоя

```bash
# Через CLI
amvera logs

# Или в веб-интерфейсе Amvera
# Вкладка "Логи" -> "Деплой"
```

---

## ✅ Проверка работы

### 1. Проверка API сервера

После успешного деплоя получите URL вашего приложения (например, `https://ozon-parser.amvera.app`)

```bash
# Проверка health endpoint
curl https://ozon-parser.amvera.app/health

# Должен вернуть:
{
  "status": "healthy",
  "service": "Ozon Parser API",
  "version": "1.0.0"
}
```

### 2. Проверка статуса парсера

```bash
curl https://ozon-parser.amvera.app/status

# Вернёт текущий статус выполнения
```

### 3. Запуск парсинга через API

```bash
curl -X POST https://ozon-parser.amvera.app/trigger \
  -H "Authorization: Bearer YOUR_API_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source": "manual", "force": false}'
```

### 4. Проверка в Telegram

После запуска парсера вы должны получить уведомления в Telegram.

---

## ⏰ Настройка автоматического запуска

### Вариант 1: Через Google Apps Script (рекомендуется)

Используйте уже существующий файл `google-apps-script.js`:

1. Откройте Google Sheets
2. Перейдите в **Расширения → Apps Script**
3. Скопируйте код из `google-apps-script.js`
4. Замените `API_URL` на URL вашего Amvera приложения
5. Замените `API_SECRET_KEY` на ваш секретный ключ
6. Настройте триггер:
   - Нажмите "Триггеры" (⏰ значок слева)
   - Нажмите "+ Добавить триггер"
   - Функция: `triggerParser`
   - События: "Временной триггер"
   - Тип: "Ежечасный таймер"
   - Сохраните

### Вариант 2: Через Amvera Cron (если поддерживается)

Создайте файл `.amvera/cron.yml`:

```yaml
cron:
  - schedule: "0 * * * *"  # Каждый час
    command: "python -c 'import requests; requests.post(\"http://localhost:8000/trigger\", json={\"source\": \"cron\"}, headers={\"Authorization\": \"Bearer $API_SECRET_KEY\"})'"
```

### Вариант 3: Внешний cron сервис

Используйте https://cron-job.org/ или https://easycron.com/:

1. Создайте задание
2. URL: `https://ozon-parser.amvera.app/trigger`
3. Method: POST
4. Headers:
   - `Authorization: Bearer YOUR_API_SECRET_KEY`
   - `Content-Type: application/json`
5. Body: `{"source": "external_cron"}`
6. Schedule: каждый час

---

## 🔧 Troubleshooting

### Проблема: "Module not found"

**Решение**: Убедитесь что все зависимости в `requirements.txt`:
```bash
# Локально протестируйте установку
pip install -r requirements.txt
```

### Проблема: "Playwright browser not found"

**Решение**: Проверьте что в `Dockerfile` есть:
```dockerfile
RUN playwright install chromium
RUN playwright install-deps chromium
```

### Проблема: "Connection closed" при парсинге

**Решение**: 
1. Убедитесь что `HEADLESS=true` в переменных окружения
2. Проверьте что cookies актуальны (экспортируйте свежие локально)
3. Загрузите cookies на сервер (см. ниже)

### Проблема: "Cookies expired"

**Решение**: Экспортируйте cookies локально и загрузите на Amvera:

1. **Локально**:
   ```bash
   python export_cookies.py
   ```

2. **Загрузите на Amvera**:
   
   Через CLI:
   ```bash
   # Если есть SSH доступ
   amvera ssh
   cat > ozon_cookies.json
   # Вставьте содержимое файла, нажмите Ctrl+D
   ```
   
   Или создайте endpoint для загрузки cookies:
   ```python
   # Добавьте в api_server.py
   @app.post("/upload-cookies")
   async def upload_cookies(cookies: dict, authorization: str = Header(None)):
       if not verify_api_key(authorization):
           raise HTTPException(status_code=401, detail="Unauthorized")
       
       with open('ozon_cookies.json', 'w') as f:
           json.dump(cookies, f)
       return {"status": "success"}
   ```

### Проблема: "Out of memory"

**Решение**: 
1. Увеличьте ресурсы в Amvera (тариф с большей памятью)
2. Ограничьте количество одновременных парсингов
3. Добавьте очистку кэша:
   ```python
   # В конце парсинга
   import gc
   gc.collect()
   ```

### Проблема: "API timeout"

**Решение**: Увеличьте timeout в uvicorn:
```yaml
# В amvera.yml
run:
  command: python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
```

---

## 📊 Мониторинг

### Логи в реальном времени

```bash
# Через CLI
amvera logs -f

# Или в веб-интерфейсе Amvera
# Вкладка "Логи" -> "Runtime"
```

### Метрики

В Amvera веб-интерфейсе:
- CPU usage
- Memory usage
- Network traffic
- Response time

---

## 🔄 Обновление приложения

### Через Git

```bash
git add .
git commit -m "feat: обновление кода"
git push origin main
```

Amvera автоматически задеплоит новую версию.

### Через CLI

```bash
amvera deploy --force
```

---

## 🔒 Безопасность

### Важные рекомендации:

1. **Никогда не коммитьте**:
   - `.env` файлы
   - `ozon_cookies.json`
   - `google_credentials.json`
   - API ключи в коде

2. **Используйте сильные API ключи**:
   ```bash
   # Генерация секретного ключа
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Ограничьте доступ к API**:
   - Используйте IP whitelist (если доступно в Amvera)
   - Проверяйте токены на каждом запросе
   - Логируйте все API вызовы

4. **Регулярно обновляйте зависимости**:
   ```bash
   pip list --outdated
   ```

---

## 📞 Поддержка

- **Amvera документация**: https://amvera.ru/docs
- **Amvera Discord**: https://discord.gg/amvera
- **Email**: support@amvera.ru

---

## ✅ Чеклист перед деплоем

- [ ] Все файлы созданы (Dockerfile, amvera.yml, .dockerignore)
- [ ] requirements.txt содержит все зависимости
- [ ] Переменные окружения настроены в Amvera
- [ ] API_SECRET_KEY сгенерирован и добавлен
- [ ] Google credentials добавлены как секрет
- [ ] Cookies экспортированы локально
- [ ] Git репозиторий создан и запушен
- [ ] Amvera проект создан и подключён к GitHub
- [ ] Автоматический деплой настроен

---

**Готово к деплою! 🚀**
