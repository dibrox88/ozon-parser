# 🚀 Развёртывание на Amvera.ru - Пошаговая инструкция

## ✅ Подготовка завершена

- ✅ GitHub репозиторий: `https://github.com/dibrox88/ozon-parser`
- ✅ Код запушен (последний коммит: `7305277`)
- ✅ `Dockerfile` настроен
- ✅ `amvera.yml` исправлен для Docker
- ✅ `requirements.txt` содержит все зависимости
- ✅ `.dockerignore` настроен

---

## 📝 Шаг 1: Регистрация и вход

1. Перейдите на **https://amvera.ru/**
2. Нажмите **"Войти"** → **"Войти через GitHub"**
3. Авторизуйте Amvera доступ к вашему GitHub аккаунту

---

## 📦 Шаг 2: Создание приложения

1. В личном кабинете нажмите **"Создать"**
2. Укажите:
   - **Название**: `ozon-parser` (или любое другое)
   - **Тип сервиса**: `Приложение`
   - **Тарифный план**: Выберите подходящий (рекомендую начать с базового)
3. Нажмите **"Далее"**

---

## 🔗 Шаг 3: Подключение GitHub репозитория

### Вариант A: Через веб-интерфейс

1. На странице "Загрузка данных" выберите **"Загрузка через Git"**
2. Выберите **"GitHub"** как источник
3. Авторизуйте доступ к GitHub (если ещё не сделано)
4. Выберите репозиторий: **`dibrox88/ozon-parser`**
5. Выберите ветку: **`main`**
6. Нажмите **"Подключить"**

### Вариант B: Через Git URL (если GitHub интеграция недоступна)

1. Используйте URL: `https://github.com/dibrox88/ozon-parser.git`
2. Ветка: `main`

**Важно**: После подключения GitHub, при каждом `git push` в ветку `main` Amvera автоматически запустит новый деплой.

---

## ⚙️ Шаг 4: Настройка переменных окружения

На странице "Конфигурация" или в настройках проекта добавьте переменные:

### Обязательные переменные:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
TELEGRAM_CHAT_ID=ваш_chat_id
OZON_EMAIL=ваш@email.com
OZON_USER_ID=46206571
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
API_SECRET_KEY=FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws
HEADLESS=true
```

### Опциональные:

```env
OZON_PHONE=+79991234567
```

**Где взять значения:**

- `TELEGRAM_BOT_TOKEN` - от [@BotFather](https://t.me/BotFather)
- `TELEGRAM_CHAT_ID` - ваш ID (можно узнать через [@userinfobot](https://t.me/userinfobot))
- `OZON_EMAIL` - email для входа на Ozon
- `OZON_USER_ID` - первые 8 цифр номера заказа (например, `46206571`)
- `GOOGLE_SHEETS_URL` - ссылка на вашу таблицу
- `API_SECRET_KEY` - уже сгенерирован выше

---

## 🔐 Шаг 5: Google Credentials (если используете Google Sheets)

1. В Amvera перейдите в раздел **"Секреты"** (Secrets)
2. Нажмите **"Добавить секрет"**
3. Имя: `GOOGLE_CREDENTIALS_JSON`
4. Значение: **Скопируйте полностью содержимое файла `google_credentials.json`**
5. Сохраните

---

## 🚀 Шаг 6: Подтверждение конфигурации

1. Amvera автоматически обнаружит файл `amvera.yml` в корне репозитория
2. Проверьте что конфигурация правильная:
   - Environment: `docker`
   - Dockerfile: `Dockerfile`
   - Port: `8000`
3. Нажмите **"Завершить"** или **"Развернуть"**

---

## 📊 Шаг 7: Мониторинг сборки

После запуска деплоя:

1. Перейдите в раздел **"Логи"** → **"Сборка"**
2. Следите за процессом:
   ```
   ✅ Клонирование репозитория
   ✅ Сборка Docker образа
   ✅ Установка системных зависимостей
   ✅ pip install -r requirements.txt
   ✅ playwright install chromium
   ✅ Запуск контейнера
   ```
3. Дождитесь сообщения **"Приложение запущено"**

**Время сборки**: ~3-5 минут (первый раз), ~1-2 минуты (последующие)

---

## ✅ Шаг 8: Проверка работы

### 8.1. Получите URL приложения

В личном кабинете Amvera найдите URL вашего приложения, например:
```
https://ozon-parser-xxxxx.amvera.app
```

### 8.2. Проверьте health endpoint

Откройте в браузере или выполните:
```bash
curl https://ozon-parser-xxxxx.amvera.app/health
```

**Ожидаемый ответ:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-30T...",
  "parser_running": false
}
```

### 8.3. Проверьте API документацию

Откройте в браузере:
```
https://ozon-parser-xxxxx.amvera.app/docs
```

Вы увидите автоматическую документацию FastAPI (Swagger UI).

---

## 🍪 Шаг 9: Загрузка cookies (ОБЯЗАТЕЛЬНО!)

Для работы парсера нужны актуальные cookies от Ozon.

### 9.1. Экспортируйте cookies локально

```bash
python export_cookies.py
```

Авторизуйтесь в открывшемся браузере и нажмите Enter.

### 9.2. Загрузите cookies на Amvera

Есть несколько способов:

#### Способ 1: Через API (рекомендуется)

Добавьте endpoint в `api_server.py`:

```python
@app.post("/upload-cookies")
async def upload_cookies(
    cookies: list,
    authorization: Optional[str] = Header(None)
):
    """Загрузка cookies через API"""
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    import json
    with open('ozon_cookies.json', 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    
    return {"status": "success", "cookies_count": len(cookies)}
```

Затем загрузите:
```bash
curl -X POST https://ozon-parser-xxxxx.amvera.app/upload-cookies \
  -H "Authorization: Bearer FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws" \
  -H "Content-Type: application/json" \
  -d @ozon_cookies.json
```

#### Способ 2: Через переменную окружения

1. Откройте `ozon_cookies.json`
2. Скопируйте всё содержимое
3. В Amvera создайте секрет `OZON_COOKIES_JSON` с этим содержимым
4. Обновите код для чтения из переменной окружения

---

## 🧪 Шаг 10: Тестовый запуск

Запустите парсер через API:

```bash
curl -X POST https://ozon-parser-xxxxx.amvera.app/trigger \
  -H "Authorization: Bearer FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws" \
  -H "Content-Type: application/json" \
  -d '{"source": "manual", "force": false}'
```

**Ожидаемый ответ:**
```json
{
  "status": "accepted",
  "message": "Parser task started",
  "source": "manual",
  "started_at": "2025-10-30T..."
}
```

### Проверьте Telegram

Вы должны получить уведомления в Telegram о процессе парсинга.

### Проверьте логи

В Amvera: **"Логи"** → **"Runtime"**

---

## ⏰ Шаг 11: Настройка автоматического запуска

### Вариант 1: Google Apps Script (рекомендуется)

1. Откройте вашу Google Sheets таблицу
2. **Расширения** → **Apps Script**
3. Создайте новый скрипт:

```javascript
function triggerParser() {
  const API_URL = 'https://ozon-parser-xxxxx.amvera.app/trigger';
  const API_SECRET_KEY = 'FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws';
  
  const options = {
    'method': 'post',
    'contentType': 'application/json',
    'headers': {
      'Authorization': 'Bearer ' + API_SECRET_KEY
    },
    'payload': JSON.stringify({
      'source': 'app_script',
      'force': false
    }),
    'muteHttpExceptions': true
  };
  
  try {
    const response = UrlFetchApp.fetch(API_URL, options);
    const result = JSON.parse(response.getContentText());
    Logger.log('Parser triggered: ' + JSON.stringify(result));
  } catch (error) {
    Logger.log('Error: ' + error);
  }
}
```

4. Настройте триггер:
   - Нажмите ⏰ **"Триггеры"**
   - **"+ Добавить триггер"**
   - Функция: `triggerParser`
   - Тип события: **"Временной триггер"**
   - Интервал: **"Ежечасный таймер"**
   - Сохраните

### Вариант 2: Amvera Cron Jobs

Если Amvera поддерживает Cron Jobs (см. документацию), создайте задание в интерфейсе.

### Вариант 3: Внешний сервис

Используйте https://cron-job.org/:
- URL: `https://ozon-parser-xxxxx.amvera.app/trigger`
- Method: POST
- Headers: `Authorization: Bearer ...`
- Schedule: каждый час

---

## 🔄 Шаг 12: Обновление кода

После любых изменений в коде:

```bash
git add .
git commit -m "feat: описание изменений"
git push origin main
```

Amvera автоматически:
1. Обнаружит push в GitHub
2. Запустит новую сборку
3. Развернёт обновлённую версию
4. Перезапустит приложение

---

## 📊 Мониторинг

### Логи в реальном времени

В Amvera:
- **"Логи"** → **"Runtime"** - логи приложения
- **"Логи"** → **"Сборка"** - логи деплоя

### Метрики

В разделе **"Метрики"**:
- CPU usage
- Memory usage
- Network traffic
- Request count

### Alerts

Настройте уведомления о сбоях:
- **"Настройки"** → **"Уведомления"**
- Добавьте email или Telegram

---

## 🆘 Troubleshooting

### Проблема: "Build failed"

**Проверьте:**
1. Логи сборки в Amvera
2. Все ли зависимости в `requirements.txt`
3. Правильно ли настроен `Dockerfile`

**Решение:**
```bash
# Локально протестируйте сборку
docker build -t ozon-parser-test .
docker run -p 8000:8000 ozon-parser-test
```

### Проблема: "Application crashed"

**Проверьте:**
1. Runtime логи
2. Переменные окружения установлены?
3. Порт 8000 указан правильно?

**Решение:**
- Проверьте что uvicorn запускается на порту 8000
- Убедитесь что все env переменные установлены

### Проблема: "Playwright browser not found"

**Проверьте Dockerfile:**
```dockerfile
RUN playwright install chromium
RUN playwright install-deps chromium
```

### Проблема: "Cookies expired"

Переэкспортируйте и загрузите свежие cookies (Шаг 9).

---

## ✅ Чеклист готовности

- [ ] Зарегистрирован на Amvera.ru
- [ ] Создан проект в Amvera
- [ ] Подключён GitHub репозиторий
- [ ] Настроены переменные окружения
- [ ] Google credentials загружены (если нужно)
- [ ] Сборка завершилась успешно
- [ ] Health check отвечает
- [ ] Cookies экспортированы и загружены
- [ ] Тестовый запуск выполнен успешно
- [ ] Telegram уведомления работают
- [ ] Google Sheets синхронизация работает
- [ ] Настроен автозапуск (Apps Script/Cron)

---

## 📞 Поддержка

- **Документация Amvera**: https://docs.amvera.ru/
- **Email поддержки**: support@amvera.ru
- **Обычное время ответа**: 5 минут - 24 часа
- **CEO (если срочно)**: kkosolapov@amvera.ru

---

**Готово! Теперь у вас полностью автоматизированный парсер на облаке! 🎉**
