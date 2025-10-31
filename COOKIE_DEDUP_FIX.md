# 🍪 Проблема дубликатов cookies - РЕШЕНО

## ❓ Вопрос:
У нас 14-16 cookies в файле, не должны ли сохраняться только последние?

## ✅ Решение:

### Проблема:
Playwright при экспорте cookies возвращает **все версии** каждой cookie для разных:
- Доменов (`.ozon.ru` vs `.ozone.ru`)
- Путей (`/` vs `/my/orders`)
- Контекстов (с `partitionKey` и без)

Например, `abt_data` была **дважды**:
1. `.ozone.ru` - expires 1793483890
2. `.ozon.ru` - expires 1793483930 (свежее)

### Исправление:

В `export_cookies.py` добавлена **дедупликация**:
```python
# Удаляем дубликаты - оставляем самую свежую версию
unique_cookies = {}
for cookie in cookies:
    name = cookie.get('name', '')
    expires = cookie.get('expires', -1)
    
    if name in unique_cookies:
        existing_expires = unique_cookies[name].get('expires', -1)
        # Оставляем ту, что истекает позже (более свежая)
        if expires > existing_expires:
            unique_cookies[name] = cookie
    else:
        unique_cookies[name] = cookie

cookies = list(unique_cookies.values())
```

### Результат:

**До:** 14 cookies (с дубликатом `abt_data`)
**После:** 13 cookies (уникальные, самые свежие)

✅ При следующем экспорте cookies будет сохраняться только последняя версия каждой.

## 🔧 Проверка:

```bash
# Проверить дубликаты в текущих cookies
python check_cookies.py

# Тест логики дедупликации
python test_dedup_cookies.py
```

## 📝 Следующий раз:

При обновлении cookies через `python export_cookies.py`:
- Будет показано: "📦 Получено X cookies из браузера"
- Будет показано: "✅ Уникальных cookies: Y"
- Если X ≠ Y, значит были дубликаты и они удалены

Это **нормально** и **правильно** - так должно быть!
