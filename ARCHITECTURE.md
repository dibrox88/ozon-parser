# Архитектура Ozon Parser на Amvera.ru

```
┌─────────────────────────────────────────────────────────────┐
│                    AMVERA.RU CLOUD                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Docker Container (Python 3.12)             │  │
│  │                                                      │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │         FastAPI Server (port 8000)         │     │  │
│  │  │                                            │     │  │
│  │  │  GET  /health   - Health check            │     │  │
│  │  │  GET  /status   - Parser status           │     │  │
│  │  │  POST /trigger  - Run parser              │     │  │
│  │  │  GET  /logs     - Get logs                │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  │                        │                            │  │
│  │                        ▼                            │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │           main.py (Parser Core)            │     │  │
│  │  │                                            │     │  │
│  │  │  • Playwright (Chromium headless)         │     │  │
│  │  │  • playwright-stealth v2.0                │     │  │
│  │  │  • OzonAuth (авторизация)                 │     │  │
│  │  │  • OzonParser (парсинг заказов)           │     │  │
│  │  │  • SheetsManager (Google Sheets API)      │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  │                                                      │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │           Persistent Storage               │     │  │
│  │  │                                            │     │  │
│  │  │  • logs/          - Логи приложения       │     │  │
│  │  │  • screenshots/   - Скриншоты страниц     │     │  │
│  │  │  • browser_state/ - Сессии браузера       │     │  │
│  │  │  • ozon_cookies.json - Cookies авториз.   │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Environment Variables:                                     │
│  • TELEGRAM_BOT_TOKEN                                       │
│  • TELEGRAM_CHAT_ID                                         │
│  • OZON_EMAIL / OZON_USER_ID                                │
│  • GOOGLE_SHEETS_URL                                        │
│  • API_SECRET_KEY                                           │
│  • HEADLESS=true                                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Google     │  │   Telegram   │  │  Ozon.ru     │
│   Sheets     │  │     Bot      │  │   (парсинг)  │
│              │  │              │  │              │
│ • Получает   │  │ • Отправляет │  │ • Авторизация│
│   данные     │  │   уведомления│  │   через      │
│   заказов    │  │   о статусе  │  │   cookies    │
│ • Обновляет  │  │ • Логирует   │  │ • Парсинг    │
│   таблицы    │  │   ошибки     │  │   заказов    │
└──────────────┘  └──────────────┘  └──────────────┘
        ▲                                   ▲
        │                                   │
        └───────────────────────────────────┘
              Data Flow (Orders → Sheets)


┌─────────────────────────────────────────────────────────────┐
│              AUTOMATION TRIGGER OPTIONS                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Google Apps Script (Рекомендуется)                     │
│     ┌───────────────────────────────────────────┐          │
│     │  function triggerParser() {               │          │
│     │    UrlFetchApp.fetch(API_URL, {           │          │
│     │      method: 'POST',                      │          │
│     │      headers: {                           │          │
│     │        'Authorization': 'Bearer KEY'      │          │
│     │      }                                     │          │
│     │    });                                    │          │
│     │  }                                        │          │
│     └───────────────────────────────────────────┘          │
│     • Триггер: Каждый час                                  │
│     • Бесплатно                                            │
│     • Интеграция с Google Sheets                           │
│                                                             │
│  2. External Cron Service                                   │
│     • cron-job.org                                          │
│     • easycron.com                                          │
│     • POST https://ваш-проект.amvera.app/trigger           │
│                                                             │
│  3. Manual Trigger (для тестирования)                      │
│     curl -X POST https://ваш-проект.amvera.app/trigger \   │
│       -H "Authorization: Bearer API_KEY"                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT FLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Local Development                                          │
│       │                                                     │
│       ▼                                                     │
│  git commit & push                                          │
│       │                                                     │
│       ▼                                                     │
│  GitHub Repository                                          │
│       │                                                     │
│       ▼                                                     │
│  Amvera Auto-Deploy                                         │
│       │                                                     │
│       ├─── Build Docker Image                              │
│       │    • Install system dependencies                   │
│       │    • pip install -r requirements.txt               │
│       │    • playwright install chromium                   │
│       │                                                     │
│       ├─── Run Container                                   │
│       │    • Start FastAPI server on :8000                 │
│       │    • Health check                                  │
│       │                                                     │
│       └─── Production Ready                                │
│            • HTTPS enabled                                 │
│            • Auto-restart on crash                         │
│            • Logs available                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. API Authentication                                      │
│     • Bearer token (API_SECRET_KEY)                        │
│     • HMAC comparison (timing-safe)                        │
│                                                             │
│  2. Browser Anti-Detection                                  │
│     • playwright-stealth v2.0                              │
│     • add_init_script (navigator.webdriver)                │
│     • Human-like delays                                    │
│                                                             │
│  3. Environment Variables                                   │
│     • Secrets stored in Amvera                             │
│     • Never committed to Git                               │
│                                                             │
│  4. HTTPS/TLS                                              │
│     • Provided by Amvera                                   │
│     • Auto-renewed certificates                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                    DATA FLOW DIAGRAM                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Trigger Received                                        │
│     API receives POST /trigger                              │
│           ▼                                                 │
│  2. Authentication                                          │
│     Verify API_SECRET_KEY                                   │
│           ▼                                                 │
│  3. Start Background Task                                   │
│     Launch main.py as subprocess                            │
│           ▼                                                 │
│  4. Browser Automation                                      │
│     • Load cookies (ozon_cookies.json)                     │
│     • Navigate to Ozon orders page                         │
│     • Verify authentication                                │
│           ▼                                                 │
│  5. Parse Orders                                            │
│     • Extract order numbers                                │
│     • Parse each order details                             │
│     • Extract items, prices, statuses                      │
│           ▼                                                 │
│  6. Data Processing                                         │
│     • Match products with catalog                          │
│     • Calculate bundles                                    │
│     • Filter excluded orders                               │
│           ▼                                                 │
│  7. Sync to Google Sheets                                   │
│     • Update orders sheet                                  │
│     • Maintain product catalog                             │
│           ▼                                                 │
│  8. Notifications                                           │
│     • Send Telegram messages                               │
│     • Log results                                          │
│           ▼                                                 │
│  9. Cleanup                                                 │
│     • Close browser                                        │
│     • Update task status                                   │
│     • Return API response                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Компоненты системы

### Backend (Python)
- **FastAPI** - REST API сервер
- **Playwright** - Автоматизация браузера
- **playwright-stealth** - Обход антибот защиты
- **gspread** - Работа с Google Sheets
- **python-telegram-bot** - Telegram уведомления

### Frontend/Triggers
- **Google Apps Script** - Автоматический запуск
- **cron-job.org** - Альтернативный триггер

### Infrastructure
- **Amvera.ru** - Хостинг контейнеров
- **Docker** - Контейнеризация
- **GitHub** - CI/CD через Git push

### External Services
- **Ozon.ru** - Источник данных
- **Google Sheets** - Хранилище данных
- **Telegram** - Уведомления

## Преимущества архитектуры

✅ **Масштабируемость** - контейнер можно легко реплицировать  
✅ **Автоматизация** - деплой по git push  
✅ **Надёжность** - auto-restart при падении  
✅ **Мониторинг** - логи и метрики в реальном времени  
✅ **Безопасность** - secrets в переменных окружения  
✅ **Гибкость** - легко добавить новые endpoints  

## Ограничения

⚠️ **Cookies** - требуют периодического обновления  
⚠️ **Headless** - нет GUI для интерактивной авторизации  
⚠️ **Rate limits** - нужно контролировать частоту запросов  
⚠️ **Memory** - Playwright требует ~500MB RAM  
