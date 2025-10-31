# ✅ Чеклист деплоя на Amvera.ru

## Статус выполнения:

### ✅ Шаг 1: Подготовка проекта
- [x] Создан Dockerfile
- [x] Создан .dockerignore
- [x] Создан amvera.yml
- [x] Обновлён requirements.txt (fastapi + uvicorn)
- [x] Создана документация
- [x] Сгенерирован API ключ

### ✅ Шаг 2: GitHub репозиторий
- [x] Создан репозиторий: https://github.com/dibrox88/ozon-parser
- [x] Код запушен на GitHub
- [x] Теги загружены (v1.0.0 - v1.9.5)

---

## 🚀 Следующие шаги:

### ⏭️ Шаг 3: Экспорт cookies (ВАЖНО!)

Перед деплоем нужно экспортировать свежие cookies:

```bash
python export_cookies.py
```

**Почему это важно:**
- На Amvera нет графического интерфейса для интерактивной авторизации
- Cookies будут использоваться для автоматической авторизации
- Без актуальных cookies парсер не сможет работать

**Что делать:**
1. Запустите команду выше
2. В открывшемся браузере авторизуйтесь на Ozon
3. После авторизации нажмите Enter в терминале
4. Файл `ozon_cookies.json` будет создан

---

### ⏭️ Шаг 4: Регистрация на Amvera

1. Перейдите на **https://amvera.ru/**
2. Нажмите **"Войти"**
3. Выберите **"Войти через GitHub"**
4. Авторизуйте Amvera доступ к вашему GitHub аккаунту

---

### ⏭️ Шаг 5: Создание проекта на Amvera

1. В личном кабинете Amvera нажмите **"Создать проект"**
2. Выберите **"Из Git репозитория"**
3. Выберите репозиторий: **dibrox88/ozon-parser**
4. Выберите ветку: **main**
5. Нажмите **"Создать"**

Amvera автоматически:
- Определит тип проекта (Python)
- Прочитает `amvera.yml` для конфигурации
- Начнёт процесс сборки

---

### ⏭️ Шаг 6: Настройка переменных окружения

В настройках проекта Amvera добавьте следующие переменные:

#### Обязательные:

```
TELEGRAM_BOT_TOKEN = <ваш_токен_от_BotFather>
TELEGRAM_CHAT_ID = <ваш_chat_id>
OZON_EMAIL = <ваш_email_на_озон>
OZON_USER_ID = 46206571
GOOGLE_SHEETS_URL = <ссылка_на_вашу_таблицу>
API_SECRET_KEY = FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws
HEADLESS = true
```

**📝 Где взять значения:**

- `TELEGRAM_BOT_TOKEN` - из вашего `.env` файла или от @BotFather
- `TELEGRAM_CHAT_ID` - из `.env` или используйте @userinfobot
- `OZON_EMAIL` - email для входа на Ozon
- `OZON_USER_ID` - первые 8 цифр номера любого заказа
- `GOOGLE_SHEETS_URL` - ссылка на вашу Google таблицу
- `API_SECRET_KEY` - сгенерированный ключ (см. выше)

#### Опционально (если используете):

```
OZON_PHONE = <ваш_телефон>
GOOGLE_CREDENTIALS_FILE = google_credentials.json
```

---

### ⏭️ Шаг 7: Google Credentials (если нужно)

Если используете Google Sheets API:

1. В Amvera перейдите в **"Секреты"** (или "Переменные окружения")
2. Создайте переменную `GOOGLE_CREDENTIALS_JSON`
3. Откройте файл `google_credentials.json` локально
4. Скопируйте **всё содержимое** файла
5. Вставьте в значение переменной `GOOGLE_CREDENTIALS_JSON`

---

### ⏭️ Шаг 8: Дождитесь деплоя

После добавления переменных:

1. Amvera начнёт процесс сборки (Build)
2. Следите за логами в разделе **"Логи" → "Деплой"**
3. Процесс займёт ~5-10 минут (установка Playwright занимает время)

**Что происходит:**
- Установка системных зависимостей
- `pip install -r requirements.txt`
- `playwright install chromium`
- Запуск контейнера с FastAPI сервером

---

### ⏭️ Шаг 9: Проверка работы

После успешного деплоя:

1. **Скопируйте URL вашего проекта** (например, `https://ozon-parser-xxxxx.amvera.app`)

2. **Проверьте health check:**
   ```bash
   curl https://ваш-проект.amvera.app/health
   ```
   Должен вернуть:
   ```json
   {
     "status": "healthy",
     "timestamp": "...",
     "parser_running": false
   }
   ```

3. **Проверьте главную страницу:**
   ```bash
   curl https://ваш-проект.amvera.app/
   ```

---

### ⏭️ Шаг 10: Загрузка cookies на сервер

Нужно загрузить ранее экспортированные cookies на Amvera.

**Вариант A: Через API endpoint (если добавите)**

Добавьте в `api_server.py` endpoint для загрузки cookies:

```python
import json
from fastapi import UploadFile, File

@app.post("/upload-cookies")
async def upload_cookies(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    content = await file.read()
    cookies = json.loads(content)
    
    with open('ozon_cookies.json', 'w') as f:
        json.dump(cookies, f, indent=2)
    
    return {"status": "success", "message": "Cookies uploaded"}
```

Затем:
```bash
curl -X POST https://ваш-проект.amvera.app/upload-cookies \
  -H "Authorization: Bearer FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws" \
  -F "file=@ozon_cookies.json"
```

**Вариант B: Через переменную окружения**

Добавьте содержимое `ozon_cookies.json` как переменную окружения в Amvera:
```
OZON_COOKIES_JSON = <содержимое файла ozon_cookies.json>
```

Обновите `main.py` для чтения cookies из переменной окружения:
```python
import os
import json

# В начале функции main()
cookies_env = os.getenv('OZON_COOKIES_JSON')
if cookies_env:
    cookies = json.loads(cookies_env)
    with open('ozon_cookies.json', 'w') as f:
        json.dump(cookies, f)
```

---

### ⏭️ Шаг 11: Тестовый запуск парсера

Запустите парсер через API:

```bash
curl -X POST https://ваш-проект.amvera.app/trigger \
  -H "Authorization: Bearer FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws" \
  -H "Content-Type: application/json" \
  -d '{"source": "manual", "force": false}'
```

**Что проверить:**
- ✅ API вернул `{"status": "accepted", ...}`
- ✅ В Telegram пришли уведомления
- ✅ Логи Amvera показывают прогресс парсинга
- ✅ Google Sheets обновились (если настроены)

**Посмотреть логи:**
```bash
curl https://ваш-проект.amvera.app/logs \
  -H "Authorization: Bearer FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws"
```

---

### ⏭️ Шаг 12: Настройка автозапуска (Google Apps Script)

Настроим автоматический запуск каждый час:

1. **Откройте Google Sheets** с вашими заказами
2. **Расширения → Apps Script**
3. **Создайте новый файл** или используйте существующий
4. **Скопируйте код** из `google-apps-script.js`
5. **Замените переменные:**
   ```javascript
   const API_URL = 'https://ваш-проект.amvera.app/trigger';
   const API_SECRET_KEY = 'FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws';
   ```

6. **Настройте триггер:**
   - Нажмите на значок часов ⏰ слева (Триггеры)
   - **"+ Добавить триггер"**
   - Выберите функцию: `triggerParser`
   - Тип источника события: **"Временной триггер"**
   - Выберите тип таймера: **"Ежечасный таймер"**
   - Нажмите **"Сохранить"**

7. **Дайте разрешения:**
   - При первом запуске Google попросит разрешить доступ
   - Нажмите "Разрешить"
   - Выберите аккаунт
   - Нажмите "Разрешить" (Advanced → Unsafe)

**Теперь парсер будет запускаться автоматически каждый час!**

---

## ✅ Финальная проверка

### Убедитесь что всё работает:

- [ ] Проект задеплоен на Amvera
- [ ] Health check возвращает `"healthy"`
- [ ] Переменные окружения настроены
- [ ] Cookies загружены на сервер
- [ ] Тестовый запуск парсера успешен
- [ ] Telegram уведомления приходят
- [ ] Google Sheets обновляются
- [ ] Google Apps Script триггер настроен
- [ ] Автозапуск каждый час работает

---

## 📚 Полезные ссылки

- **GitHub репозиторий**: https://github.com/dibrox88/ozon-parser
- **Amvera панель**: https://amvera.ru/
- **Документация**:
  - `AMVERA_DEPLOY_GUIDE.md` - полное руководство
  - `AMVERA_QUICKSTART.md` - быстрый старт
  - `ARCHITECTURE.md` - архитектура системы

---

## 🆘 Если что-то пошло не так

### Проблема: Деплой не запускается
- Проверьте что `amvera.yml` корректен
- Проверьте логи деплоя в Amvera

### Проблема: "Module not found"
- Проверьте что все зависимости в `requirements.txt`
- Посмотрите логи установки пакетов

### Проблема: "Playwright browser not found"
- Проверьте что в `Dockerfile` есть `playwright install chromium`

### Проблема: Парсер не работает
- Проверьте что cookies актуальны (`python export_cookies.py`)
- Проверьте переменные окружения в Amvera
- Посмотрите логи runtime в Amvera

### Проблема: Telegram не присылает уведомления
- Проверьте `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`
- Убедитесь что бот не заблокирован

---

## 🎉 Успех!

Когда всё заработает:
- Парсер будет автоматически запускаться каждый час
- Данные будут синхронизироваться с Google Sheets
- Вы будете получать уведомления в Telegram
- Вся инфраструктура работает в облаке

**Поздравляю с успешным деплоем! 🚀**
