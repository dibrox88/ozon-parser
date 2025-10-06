# Быстрый старт с сопоставлением товаров

## 📦 Установка зависимостей

```bash
pip install -r requirements.txt
```

Новые библиотеки в v1.4.0:
- `gspread==6.0.0` - работа с Google Sheets
- `google-auth==2.27.0` - авторизация в Google API

## 🔧 Настройка Google Sheets

### 1. Быстрая настройка (5 минут)

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте проект "Ozon Parser"
3. Включите API:
   - Google Sheets API
   - Google Drive API
4. Создайте Service Account:
   - **Credentials** → **Create Credentials** → **Service Account**
   - Роль: **Editor**
5. Создайте JSON ключ:
   - **Keys** → **Add Key** → **Create new key** → **JSON**
6. Сохраните файл как `google_credentials.json` в корне проекта

### 2. Дайте доступ к таблице

1. Откройте `google_credentials.json`
2. Скопируйте значение поля `"client_email"`
3. Откройте вашу Google Sheets таблицу
4. **Share** → вставьте email → дайте права **Viewer**

### 3. Настройте .env

```bash
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/1JsvsWxlDZN4zV-BwFDTIOpZSElLKdh_mkTqP_fpPUhk/edit?gid=1473954199
GOOGLE_CREDENTIALS_FILE=google_credentials.json
```

📖 Подробная инструкция: [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md)

## 📊 Структура таблицы

Ваша Google Sheets таблица должна иметь структуру:

```
| Цена | Название      | Тип    | Цена | Название      | Тип    | ... |
|------|---------------|--------|------|---------------|--------|-----|
| 1000 | Корпус Q11    | комп   | 2000 | Адаптер Wi-Fi | расх   | ... |
| 1500 | Кулер CPU     | комп   | 500  | Термопаста    | расх   | ... |
```

**Каждые 3 столбца**: Цена (справка) | Название | Тип

**Диапазон чтения**: A:AU (столбцы от A до AU)

## 🚀 Запуск

```bash
python main.py
```

Система автоматически:
1. ✅ Парсит заказы с Ozon
2. ✅ Подключается к Google Sheets
3. ✅ Загружает каталог товаров
4. ✅ Сопоставляет товары из заказов с каталогом
5. ✅ Сохраняет результат в JSON с полями `mapped_name` и `mapped_type`

## 📁 Результат

### JSON с сопоставлениями

Файл: `ozon_orders_2025-XX-XX_XX-XX-XX.json`

```json
{
  "orders": [
    {
      "order_number": "46206571-0580",
      "items": [
        {
          "name": "Корпус Invader Q11 кубик + 3 ARGB вентилятора...",
          "color": "White",
          "quantity": 5,
          "price": 4098.0,
          "status": "забрать",
          "mapped_name": "Корпус компьютерный Q11",
          "mapped_type": "комплектующие"
        }
      ]
    }
  ]
}
```

### Кеш сопоставлений

Файл: `product_mappings.json`

Сохраняет все подтверждённые связки для быстрого повторного использования.

## 🎯 Как работает сопоставление

### 1. Проверка кеша
```
Товар уже сопоставлялся? → Используем сохранённое значение
```

### 2. Автоматический поиск
```
Ищем похожие товары в каталоге:
- Точное совпадение (100%)
- Частичное совпадение (80%)
- По ключевым словам (30-70%)
```

### 3. Интерактивное подтверждение (опционально)
```
Telegram уведомление:
🔍 Найдено совпадение
Товар: Корпус Invader Q11...
→ Корпус компьютерный Q11 (комплектующие) [85%]

Отправьте OK для подтверждения
```

### 4. Сохранение
```
Связка сохраняется в product_mappings.json
При следующем запуске используется автоматически
```

## 🔍 Тип по умолчанию

Если товар не найден в каталоге, используется тип: **"расходники"**

Можно изменить в `product_matcher.py`:

```python
class ProductMatcher:
    DEFAULT_TYPE = "расходники"  # Измените на нужный
```

## 📋 Проверка работы

### Тест подключения к Google Sheets

```bash
python -c "from sheets_manager import SheetsManager; from config import Config; sm = SheetsManager(Config.GOOGLE_CREDENTIALS_FILE); print('✅ OK' if sm.connect() else '❌ Ошибка')"
```

### Просмотр загруженных товаров

```bash
python -c "
from sheets_manager import SheetsManager
from config import Config

sm = SheetsManager(Config.GOOGLE_CREDENTIALS_FILE)
if sm.connect():
    products = sm.load_products_from_sheet(Config.GOOGLE_SHEETS_URL)
    print(f'Загружено: {len(products)} товаров')
    for p in products[:5]:
        print(f'  • {p[\"name\"]} - {p[\"type\"]}')
"
```

### Просмотр сопоставлений

```bash
python -c "
import json
from pathlib import Path

if Path('product_mappings.json').exists():
    with open('product_mappings.json') as f:
        mappings = json.load(f)
    print(f'Сохранено сопоставлений: {len(mappings)}')
    for key, val in list(mappings.items())[:3]:
        print(f'  • {val[\"original_name\"]} → {val[\"mapped_name\"]}')
else:
    print('Сопоставлений пока нет')
"
```

## 🛠️ Управление кешем

### Очистить все сопоставления

```bash
# Windows PowerShell
Remove-Item product_mappings.json

# Linux/Mac
rm product_mappings.json
```

### Редактировать конкретное сопоставление

Откройте `product_mappings.json` и измените нужное значение:

```json
{
  "корпус warrior z5|black": {
    "mapped_name": "Корпус компьютерный Warrior",
    "mapped_type": "комплектующие"
  }
}
```

## 📚 Дополнительная документация

- [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) - Подробная настройка Google Sheets API
- [PRODUCT_MATCHING.md](PRODUCT_MATCHING.md) - Полное руководство по сопоставлению
- [CHANGELOG.md](CHANGELOG.md) - История версий

## ❓ Устранение проблем

### Google Sheets не подключается

1. Проверьте, что файл `google_credentials.json` существует
2. Убедитесь, что Service Account email добавлен в доступы к таблице
3. Проверьте, что API включены в Google Cloud Console

### Товары не сопоставляются

1. Проверьте структуру таблицы (каждые 3 столбца)
2. Убедитесь, что названия и типы заполнены
3. Проверьте диапазон чтения (A:AU)

### Неправильные сопоставления

1. Удалите `product_mappings.json`
2. Запустите парсер заново
3. Или отредактируйте файл вручную

## 🎉 Готово!

Теперь ваш парсер автоматически:
- ✅ Парсит заказы с Ozon
- ✅ Сопоставляет товары с вашим каталогом
- ✅ Сохраняет обогащённые данные в JSON
- ✅ Кеширует сопоставления для быстрой работы

Следующий запуск будет ещё быстрее благодаря кешу! 🚀
