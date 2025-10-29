# 🛡️ Защита от детектирования бота

Ozon использует антибот-системы для выявления автоматизации. Вот что мы сделали и что можно улучшить.

---

## ✅ Что уже реализовано

### 1. **Stealth аргументы браузера** (`main.py`):
```python
args=[
    '--disable-blink-features=AutomationControlled',  # Главное!
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process',
    '--disable-infobars',
    '--ignore-certificate-errors',
]
```

### 2. **JavaScript инъекции**:
- Подмена `navigator.webdriver` → `undefined`
- Фальшивые плагины браузера
- Правильные языки и локаль
- Canvas fingerprint защита
- WebGL fingerprint защита
- Chrome runtime объект

### 3. **Реальные параметры браузера**:
```python
viewport={'width': 1920, 'height': 1080}
locale='ru-RU'
timezone_id='Europe/Moscow'
geolocation={'longitude': 37.6173, 'latitude': 55.7558}  # Москва
```

### 4. **Человекоподобное поведение** (`stealth.py`):
- Случайные задержки между действиями
- Имитация печати с задержками
- Случайные движения мыши
- Плавная прокрутка страницы

---

## 🚀 Что нужно сделать СЕЙЧАС

### Вариант 1: Запустите в неголовном режиме (с GUI) ✅

На локальной машине (не на сервере):

```powershell
# В .env измените:
HEADLESS=False
```

Затем запустите:
```powershell
python main.py
```

**Преимущества**:
- Видите что происходит
- Браузер выглядит как обычный Chrome
- Меньше вероятность детекта
- Можете вручную пройти капчу если появится

---

### Вариант 2: Используйте Firefox вместо Chromium

Ozon может детектировать Playwright Chromium. Firefox детектируется реже:

**Измените в `main.py`:**

```python
# Было:
browser = p.chromium.launch(...)

# Стало:
browser = p.firefox.launch(
    headless=Config.HEADLESS,
    firefox_user_prefs={
        "geo.enabled": True,
        "geo.provider.use_corelocation": True,
        "geo.prompt.testing": True,
        "geo.prompt.testing.allow": True,
        "intl.accept_languages": "ru-RU, ru, en-US, en",
    }
)
```

Также установите Firefox для Playwright:
```bash
playwright install firefox
```

---

### Вариант 3: Добавьте playwright-stealth (Python библиотека)

**Установите:**
```bash
pip install playwright-stealth
```

**Измените `main.py`:**
```python
from playwright_stealth import stealth_sync

# После создания страницы:
page = context.new_page()
stealth_sync(page)  # Применить все stealth техники
```

---

### Вариант 4: Используйте прокси с российским IP

Если запускаете с сервера за границей, Ozon может блокировать.

**Добавьте прокси:**
```python
context = browser.new_context(
    ...
    proxy={
        'server': 'http://proxy.example.com:8080',
        'username': 'user',
        'password': 'pass'
    }
)
```

**Бесплатные российские прокси**:
- https://www.proxy-list.download/RUSSIA
- https://free-proxy-list.net/

---

### Вариант 5: Увеличьте задержки

Слишком быстрые действия = бот.

**Измените в `config.py`:**
```python
DEFAULT_TIMEOUT = 60000  # Было 30000
NAVIGATION_TIMEOUT = 60000  # Было 45000
```

**Добавьте задержки в `auth.py` и `parser.py`:**
```python
from stealth import StealthHelper

# Перед каждым действием:
StealthHelper.human_delay(1, 3)  # 1-3 секунды

# Перед вводом текста:
StealthHelper.human_type(page, selector, text)

# Перед кликом:
StealthHelper.human_click(page, selector)

# Случайные движения мыши:
StealthHelper.random_mouse_movement(page, 5)

# Случайная прокрутка:
StealthHelper.random_scroll(page, 'down')
```

---

## 🔍 Диагностика проблемы

### 1. Проверьте детект через онлайн сервис:

Добавьте в начало `main.py`:
```python
page.goto('https://bot.sannysoft.com/')
page.wait_for_timeout(10000)
page.screenshot(path='bot_detection_test.png', full_page=True)
```

Откройте скриншот - **зеленые** = хорошо, **красные** = детектирует.

### 2. Проверьте что видит Ozon:

```python
page.goto('https://www.ozon.ru/')
result = page.evaluate('''() => {
    return {
        webdriver: navigator.webdriver,
        plugins: navigator.plugins.length,
        languages: navigator.languages,
        chrome: !!window.chrome,
        userAgent: navigator.userAgent
    }
}''')
print(result)
```

**Должно быть**:
- `webdriver`: `undefined` или `False` (не `True`!)
- `plugins`: > 0
- `languages`: `['ru-RU', 'ru', ...]`
- `chrome`: `True`

---

## 🎯 Рекомендуемый план действий

### Шаг 1: Локальное тестирование
```bash
# .env
HEADLESS=False
```
```bash
python main.py
```
Смотрим что происходит, на каком этапе блокирует.

### Шаг 2: Применить playwright-stealth
```bash
pip install playwright-stealth
```
Добавить `stealth_sync(page)` после создания страницы.

### Шаг 3: Попробовать Firefox
```python
browser = p.firefox.launch(...)
playwright install firefox
```

### Шаг 4: Добавить больше человекоподобности
- Импортировать `StealthHelper`
- Добавить случайные задержки
- Использовать `human_type()` и `human_click()`

### Шаг 5: Если ничего не помогает - использовать Selenium
Playwright детектируется легче чем Selenium с undetected-chromedriver.

---

## 📦 Обновление на сервере

После внесения изменений:

### 1. Обновите файлы:
```powershell
.\update-server.ps1
```

Или вручную:
```powershell
scp main.py stealth.py ozon@85.193.81.13:~/ozon_parser/
```

### 2. Установите зависимости (если добавили playwright-stealth):
```bash
ssh ozon@85.193.81.13
cd ~/ozon_parser
source venv/bin/activate
pip install playwright-stealth
```

### 3. Тест:
```bash
python main.py
```

---

## 🚨 Признаки детекта

**Что говорит о том, что вас детектят:**

1. ❌ Страница перезагружается сама
2. ❌ Появляется капча/проверка безопасности
3. ❌ Бесконечная загрузка
4. ❌ Сообщение "Доступ запрещен"
5. ❌ Редирект на другой домен
6. ❌ Пустая страница / ошибка 403

**Решение**: Применить методы выше ☝️

---

## 💡 Дополнительные трюки

### Использовать реальный Chrome профиль:

```python
context = browser.new_context(
    user_data_dir='/path/to/chrome/profile',
    channel='chrome'  # Использовать установленный Chrome вместо Chromium
)
```

### Эмулировать мобильное устройство:

```python
device = p.devices['iPhone 12']
context = browser.new_context(**device)
```

Мобильные браузеры детектируются реже.

### Отключить automation в Chrome напрямую:

```python
browser = p.chromium.launch(
    channel='chrome',  # Использовать Google Chrome
    args=['--disable-blink-features=AutomationControlled']
)
```

---

## ❓ FAQ

**Q: Почему headless=True детектируется?**
A: В headless режиме браузер имеет специфичные параметры (размер экрана, отсутствие GPU и т.д.). Используйте `headless=False` для локальных тестов.

**Q: Может ли Ozon забанить мой аккаунт?**
A: Маловероятно. Обычно просто блокируют доступ для конкретной сессии. Но всё же используйте разумные задержки.

**Q: Поможет ли смена user-agent?**
A: Частично. Но современные антибот-системы проверяют десятки параметров, не только user-agent.

**Q: Стоит ли использовать VPN?**
A: Да, если сервер находится не в России. Российский IP снижает подозрительность.

---

**Начните с локального теста в неголовном режиме (HEADLESS=False)!** 🎯
