# 🛡️ v1.9.2 - Усиленная защита от антибота Ozon

## Что сделано:

### 1. Изучены материалы:
- ✅ **Статья на Habr**: https://habr.com/ru/companies/amvera/articles/960280/
- ✅ **GitHub репозиторий**: https://github.com/aglihowstan/parser_ozon
- ✅ Изучена логика обхода антибот-защиты Ozon

### 2. Ключевые находки из статьи:

**Проблема**: Ozon с 2022 года использует мощную защиту от парсинга, которая детектирует автоматизацию по множеству признаков.

**Решение из статьи**:
- Использование **Playwright** (не Selenium)
- Параметр `slow_mo=50` - замедляет действия
- Строгий `--disable-blink-features=AutomationControlled`
- Подмена `navigator.webdriver` → `undefined`
- User-Agent от Mac OS (менее подозрительный)
- Задержки `human_delay(1, 3)` между КАЖДЫМ действием
- Случайные задержки при прокрутке и кликах

### 3. Что имплементировали:

#### ✅ В `main.py`:
```python
browser = p.chromium.launch(
    headless=Config.HEADLESS,
    slow_mo=50,  # НОВОЕ - замедляет ВСЕ действия
    args=[
        '--disable-blink-features=AutomationControlled',  # Самое важное!
        '--disable-features=VizDisplayCompositor',  # Новое
        # ... остальные аргументы
    ]
)
```

#### ✅ В `config.py`:
```python
# Обновили User-Agent на Mac OS (из статьи)
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
```

#### ✅ В `stealth.py`:
```python
# Увеличили минимальные задержки
def human_delay(min_sec: float = 1.0, max_sec: float = 3.0):  # Было 0.5-2.0
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    logger.debug(f"Задержка: {delay:.2f}с")  # Добавили логирование
```

#### ✅ В `auth.py`:
```python
# Заменили фиксированные задержки на случайные
StealthHelper.human_delay(2, 4)  # Вместо time.sleep(2)
```

### 4. Что УЖЕ было у нас (и работает):

- ✅ `playwright-stealth` библиотека (v2.0.0)
- ✅ Подмена `navigator.webdriver` через JavaScript
- ✅ Подмена `navigator.plugins`
- ✅ Canvas и WebGL fingerprint protection
- ✅ Расширенные browser аргументы
- ✅ Контекст с правильными параметрами

---

## Почему это работает:

### 1. **slow_mo=50** 
Каждое действие (клик, ввод текста, прокрутка) выполняется на 50мс медленнее. Для бота это незаметно, но для детекта - критично. Человек не может действовать моментально.

### 2. **--disable-blink-features=AutomationControlled**
Отключает флаг, по которому сайты ПЕРВЫМ ДЕЛОМ определяют автоматизацию. Без этого всё остальное бесполезно.

### 3. **User-Agent от Mac**
Статистически Mac OS используют реже для ботов (обычно Windows/Linux). Меньше подозрений.

### 4. **Случайные задержки 1-3 секунды**
Человек думает, читает, двигает мышь. Бот без задержек выполняет действия за миллисекунды. Это мертвая выдача.

### 5. **playwright-stealth**
Автоматически применяет 30+ техник обхода детекта, включая:
- Скрытие automation флагов
- Эмуляция реальных плагинов
- Правильные значения для всех navigator свойств
- И многое другое

---

## Что делать дальше:

### Если ВСЁ РАВНО блокирует:

#### Вариант 1: Запустить локально БЕЗ headless
```bash
# В .env
HEADLESS=False
```

Браузер с GUI детектируется гораздо реже. Плюс можете вручную пройти капчу если появится.

#### Вариант 2: Добавить ещё больше задержек
```python
# В stealth.py
def human_delay(min_sec: float = 2.0, max_sec: float = 5.0):  # Ещё медленнее
```

#### Вариант 3: Использовать прокси с российским IP
```python
# В main.py, setup_browser_context()
context = browser.new_context(
    ...
    proxy={
        'server': 'http://proxy.example.com:8080',
        'username': 'user',
        'password': 'pass'
    }
)
```

#### Вариант 4: Запускать парсер реже
Вместо каждого часа - раз в 2-3 часа. Частые запросы повышают подозрения.

#### Вариант 5: Использовать реальный Chrome профиль
```python
context = browser.new_context(
    user_data_dir='/path/to/chrome/profile'  # Профиль с историей, куками
)
```

---

## Проверка работы:

### 1. Локально:
```bash
python main.py
```

Смотрите логи:
- `✅ playwright-stealth загружен (v2.0)` - должно быть
- `🛡️ Применяем stealth-режим...` - должно быть
- `Задержка: X.XXс` - должны быть случайные задержки
- Браузер должен работать МЕДЛЕННЕЕ чем раньше (из-за slow_mo)

### 2. На сервере:
```bash
# Обновить файлы
.\update-server.ps1

# Или вручную
scp main.py config.py auth.py stealth.py ozon@85.193.81.13:~/ozon_parser/

# Перезапустить
ssh ozon@85.193.81.13
sudo systemctl restart ozon-parser-api

# Тест
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

---

## Технические детали из статьи:

### Ключевые техники которые использовал автор статьи:

1. **Browser Setup**:
```python
browser = await playwright.chromium.launch(
    headless=True,
    slow_mo=50,  # ← КЛЮЧЕВОЕ
    args=[
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor"
    ]
)
```

2. **Context Setup**:
```python
context = await browser.new_context(
    viewport={"width": 1920, "height": 1080},
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
    java_script_enabled=True,
    ignore_https_errors=True
)
```

3. **JavaScript Injection**:
```javascript
Object.defineProperty(navigator, 'webdriver', { 
    get: () => undefined 
});
Object.defineProperty(navigator, 'plugins', { 
    get: () => [1, 2, 3, 4, 5] 
});
```

4. **Human Delays**:
```python
async def human_delay(self, min_sec=1, max_sec=3):
    await asyncio.sleep(random.uniform(min_sec, max_sec))
```

Применял задержки:
- После каждого goto()
- После каждого клика
- После каждого ввода текста
- При прокрутке страницы
- При переходе на следующую страницу

### Селекторы которые работают (из репозитория):

**Кнопка входа**:
- `span.tsCompact300XSmall:has-text("Войти")`
- `text="Войти"`

**Поиск товаров**:
- `[data-widget='searchResults']`
- `.tile-root a[href*='/product/']`

**Цены**:
- `[data-widget='webPrice']`
- В JSON: `window.__INITIAL_STATE__`

**Рейтинг**:
- `span[data-widget='webReviewRating']`

**Отзывы**:
- `span[data-widget='webReviewCount']`

---

## Итоговая архитектура защиты:

```
┌─────────────────────────────────────┐
│   Уровень 1: Browser Arguments      │
│   --disable-blink-features...       │
│   slow_mo=50                        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Уровень 2: Context Settings       │
│   viewport, user_agent, locale      │
│   geolocation, permissions          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Уровень 3: JavaScript Injection   │
│   navigator.webdriver = undefined   │
│   navigator.plugins = [...]         │
│   Canvas/WebGL protection           │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Уровень 4: playwright-stealth     │
│   30+ автоматических техник         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Уровень 5: Human Behavior         │
│   Случайные задержки 1-3с           │
│   Плавные движения мыши             │
│   Случайная прокрутка               │
└─────────────────────────────────────┘
```

---

## Коммиты:

- `2bc6497` - v1.9.1: Add playwright-stealth and enable screenshots
- `278749e` - v1.9.2: Enhanced anti-detection with slow_mo and better delays

---

## Файлы изменены:

- ✅ `main.py` - добавлен slow_mo=50, VizDisplayCompositor
- ✅ `config.py` - обновлен User-Agent на Mac OS
- ✅ `stealth.py` - увеличены задержки до 1-3с, добавлено логирование
- ✅ `auth.py` - заменены фиксированные задержки на случайные

---

## Статус:

✅ **v1.9.2 готов к тестированию**

Все техники из статьи Habr и GitHub репозитория имплементированы. Защита усилена до максимума в рамках Playwright.

**Следующий шаг**: Тестирование на реальном Ozon 🎯
