# Quick Start: Деплой на Amvera.ru

## 🚀 За 5 минут

### 1. Подготовьте cookies (локально)
```bash
python export_cookies.py
```
Авторизуйтесь в браузере, экспортируйте cookies.

### 2. Создайте репозиторий на GitHub
```bash
git add .
git commit -m "feat: готовность к деплою на Amvera"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ozon-parser.git
git push -u origin main
```

### 3. Зарегистрируйтесь на Amvera
- Перейдите на https://amvera.ru/
- Зарегистрируйтесь через GitHub
- Подключите GitHub репозиторий

### 4. Настройте переменные окружения
В Amvera веб-интерфейсе добавьте:
```
TELEGRAM_BOT_TOKEN=ваш_токен
TELEGRAM_CHAT_ID=ваш_chat_id
OZON_EMAIL=ваш@email.com
OZON_USER_ID=46206571
GOOGLE_SHEETS_URL=ваша_ссылка
API_SECRET_KEY=сгенерируйте_32_символа
HEADLESS=true
```

### 5. Задеплойте
Amvera автоматически запустит деплой после push.

### 6. Проверьте
```bash
curl https://ваш-проект.amvera.app/health
```

### 7. Настройте автозапуск
Используйте Google Apps Script (см. `google-apps-script.js`) для запуска каждый час.

---

## 📋 Файлы созданы:
- ✅ `Dockerfile` - конфигурация контейнера
- ✅ `.dockerignore` - исключения
- ✅ `amvera.yml` - настройки Amvera
- ✅ `requirements.txt` - обновлён (добавлены fastapi, uvicorn)

## 📖 Полная документация
См. `AMVERA_DEPLOY_GUIDE.md`

## 🆘 Проблемы?
1. Убедитесь что cookies актуальны
2. Проверьте переменные окружения
3. Посмотрите логи в Amvera: вкладка "Логи"

**Готово! 🎉**
