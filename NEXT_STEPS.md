# ✅ Следующие шаги для деплоя на Amvera.ru

## Что уже сделано:

✅ Создан `Dockerfile` для контейнеризации приложения  
✅ Создан `.dockerignore` для оптимизации образа  
✅ Создан `amvera.yml` для конфигурации Amvera  
✅ Обновлён `requirements.txt` (добавлены fastapi, uvicorn)  
✅ Создано подробное руководство `AMVERA_DEPLOY_GUIDE.md`  
✅ Создан quick start `AMVERA_QUICKSTART.md`  
✅ Создан генератор API ключей `generate_api_key.py`  
✅ Коммит создан: `225b057`  
✅ Тег создан: `v1.9.5`  

---

## 🚀 Что делать дальше:

### 1. Экспортируйте свежие cookies (ВАЖНО!)

```bash
python export_cookies.py
```

Это необходимо для работы парсера на сервере, т.к. интерактивная авторизация недоступна.

---

### 2. Создайте GitHub репозиторий (если ещё не создан)

```bash
git remote add origin https://github.com/YOUR_USERNAME/ozon-parser.git
git branch -M main
git push -u origin main --tags
```

Замените `YOUR_USERNAME` на ваш username в GitHub.

---

### 3. Зарегистрируйтесь на Amvera

1. Перейдите на https://amvera.ru/
2. Нажмите "Войти" → "Войти через GitHub"
3. Авторизуйте Amvera доступ к вашему GitHub

---

### 4. Создайте проект на Amvera

1. В личном кабинете нажмите **"Создать проект"**
2. Выберите **"Из Git репозитория"**
3. Выберите репозиторий: `ozon-parser`
4. Выберите ветку: `main`
5. Нажмите **"Создать"**

---

### 5. Настройте переменные окружения

В настройках проекта добавьте:

```env
TELEGRAM_BOT_TOKEN=<ваш_токен_бота>
TELEGRAM_CHAT_ID=<ваш_chat_id>
OZON_EMAIL=<ваш_email@ozon.ru>
OZON_USER_ID=46206571
GOOGLE_SHEETS_URL=<ссылка_на_вашу_таблицу>
API_SECRET_KEY=<сгенерированный_ключ>
HEADLESS=true
```

**Сгенерированный API ключ (средний, 32 байта):**
```
FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws
```
⚠️ **ВАЖНО**: Скопируйте этот ключ, он понадобится!

---

### 6. Добавьте Google Credentials (опционально)

Если используете Google Sheets:

1. В Amvera перейдите в **"Секреты"**
2. Создайте секрет: `GOOGLE_CREDENTIALS_JSON`
3. Скопируйте содержимое файла `google_credentials.json`
4. Вставьте в значение секрета

---

### 7. Загрузите cookies на Amvera

После первого деплоя, загрузите cookies через API:

```bash
# Замените URL на ваш URL Amvera проекта
curl -X POST https://ваш-проект.amvera.app/upload-cookies \
  -H "Authorization: Bearer FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws" \
  -H "Content-Type: application/json" \
  -d @ozon_cookies.json
```

Или добавьте endpoint в `api_server.py` (см. AMVERA_DEPLOY_GUIDE.md).

---

### 8. Проверьте деплой

После завершения деплоя:

```bash
# Проверка здоровья API
curl https://ваш-проект.amvera.app/health

# Проверка статуса парсера
curl https://ваш-проект.amvera.app/status
```

---

### 9. Запустите парсер

```bash
curl -X POST https://ваш-проект.amvera.app/trigger \
  -H "Authorization: Bearer FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws" \
  -H "Content-Type: application/json" \
  -d '{"source": "manual", "force": false}'
```

Проверьте Telegram - должны прийти уведомления.

---

### 10. Настройте автозапуск через Google Apps Script

1. Откройте вашу Google Sheets таблицу
2. Перейдите **Расширения → Apps Script**
3. Скопируйте код из `google-apps-script.js`
4. Замените переменные:
   ```javascript
   const API_URL = 'https://ваш-проект.amvera.app/trigger';
   const API_SECRET_KEY = 'FqShCKtbaTPuRBimexak4radXxWUs7M_orOjSX3uXws';
   ```
5. Настройте триггер:
   - Нажмите ⏰ "Триггеры"
   - "+ Добавить триггер"
   - Функция: `triggerParser`
   - События: "Временной триггер"
   - Тип: "Ежечасный таймер"
   - Сохраните

---

## 📖 Дополнительная информация

- **Полное руководство**: `AMVERA_DEPLOY_GUIDE.md`
- **Quick Start**: `AMVERA_QUICKSTART.md`
- **Генератор ключей**: `python generate_api_key.py`

---

## 🆘 Если возникли проблемы

1. **Проверьте логи в Amvera**: вкладка "Логи" → "Runtime"
2. **Убедитесь что cookies актуальны**: `python export_cookies.py`
3. **Проверьте переменные окружения**: все ли добавлены?
4. **Посмотрите в Telegram**: приходят ли уведомления?

---

## ✅ Чеклист

- [ ] Cookies экспортированы локально
- [ ] GitHub репозиторий создан и запушен
- [ ] Зарегистрирован на Amvera.ru
- [ ] Проект создан на Amvera
- [ ] Переменные окружения настроены
- [ ] API_SECRET_KEY скопирован
- [ ] Google Credentials добавлены (если нужно)
- [ ] Деплой завершён успешно
- [ ] API health check работает
- [ ] Cookies загружены на сервер
- [ ] Тестовый запуск парсера выполнен
- [ ] Google Apps Script настроен
- [ ] Автозапуск каждый час работает

---

**Удачи с деплоем! 🚀**
