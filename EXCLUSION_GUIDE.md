# Руководство по исключению заказов

## Описание

Система исключения заказов позволяет игнорировать нежелательные заказы при парсинге. Исключённые заказы сохраняются в `excluded_orders.json` и автоматически фильтруются при следующем запуске.

## Как это работает

### 1. Исключение заказа через Telegram

Во время интерактивного маппинга товаров в Telegram появляется возможность исключить весь заказ:

```
🔍 Товар НЕ НАЙДЕН в каталоге

📦 Товар из заказа:
• Название: Товар XYZ
• Цвет: Black
• Количество: 5
• Цена: 1000 ₽
• Заказ: 46206571-0593

💡 Варианты ответа:
1. Отправьте OK - использовать тип "расходники"
2. Отправьте Название | Тип - ввести вручную
3. Отправьте EXCLUDE - исключить весь заказ 46206571-0593

⏳ Ожидаю ваш ответ...
```

**Ответ**: `EXCLUDE`

**Результат**:
```
🚫 Заказ 46206571-0593 исключён!

Все товары из этого заказа будут пропущены.
```

### 2. Автоматическая фильтрация

При следующем запуске парсера:

1. **После парсинга заказов** (в `main.py`):
   ```
   📋 В списке исключённых: 3 заказов
   ⏭️ Пропущено исключённых заказов: 3
   • 46206571-0580
   • 46206571-0593
   • 46206571-0609
   ✅ Заказов для обработки: 9
   ```

2. **При маппинге товаров** (в `product_matcher.py`):
   - Все товары из исключённых заказов автоматически пропускаются
   - Не требуется повторного подтверждения

## Структура excluded_orders.json

```json
{
  "excluded_orders": [
    "46206571-0580",
    "46206571-0593",
    "46206571-0609"
  ],
  "last_updated": "2025-10-07 08:00:47",
  "description": "Список исключённых заказов (order_number), которые не будут парситься"
}
```

## Программное управление

### Использование ExcludedOrdersManager

```python
from excluded_manager import ExcludedOrdersManager

# Создание менеджера
manager = ExcludedOrdersManager()

# Добавить заказ в исключённые
manager.add_excluded("46206571-0593")

# Проверить, исключён ли заказ
if manager.is_excluded("46206571-0593"):
    print("Заказ исключён")

# Удалить заказ из исключённых
manager.remove_excluded("46206571-0593")

# Получить список всех исключённых
excluded_list = manager.get_excluded_list()
print(f"Исключено: {excluded_list}")

# Фильтрация списка заказов
valid_orders, excluded_orders = manager.filter_orders(all_orders_data)
print(f"Активных: {len(valid_orders)}, Исключённых: {len(excluded_orders)}")

# Очистить весь список
manager.clear_excluded()
```

## Тестирование

Запустите тестовый скрипт:

```bash
python test_exclude_orders.py
```

**Тесты проверяют**:
- ✅ Добавление заказов в excluded_orders.json
- ✅ Проверку наличия (is_excluded)
- ✅ Фильтрацию списка заказов (12 → 9 после исключения 3)
- ✅ Удаление из списка
- ✅ Интеграцию с product_matcher

## Примеры использования

### Сценарий 1: Исключить тестовый заказ

**Проблема**: При тестировании создан заказ с тестовыми товарами, который не нужен в реальных данных.

**Решение**:
1. При маппинге первого товара из этого заказа отправьте `EXCLUDE`
2. Все товары из заказа будут пропущены
3. При следующем парсинге заказ автоматически игнорируется

### Сценарий 2: Исключить отменённый заказ

**Проблема**: Заказ был отменён, но всё ещё отображается в истории Ozon.

**Решение**:
1. При маппинге отправьте `EXCLUDE`
2. Заказ больше не будет парситься

### Сценарий 3: Очистить старые исключения

**Проблема**: Накопилось много исключённых заказов за несколько месяцев.

**Решение**:
```python
from excluded_manager import ExcludedOrdersManager

manager = ExcludedOrdersManager()
print(f"Исключено: {manager.get_count()} заказов")

# Очистить все
manager.clear_excluded()
print("✅ Список очищен")
```

## Интеграция в рабочий процесс

### 1. Основной парсинг (main.py)

```python
# После парсинга всех заказов
from excluded_manager import ExcludedOrdersManager
excluded_manager = ExcludedOrdersManager()

# Фильтруем исключённые
valid_orders, excluded_orders = excluded_manager.filter_orders(all_orders_data)

if excluded_orders:
    logger.info(f"⏭️ Пропущено исключённых заказов: {len(excluded_orders)}")

# Продолжаем с valid_orders
all_orders_data = valid_orders
```

### 2. Маппинг товаров (product_matcher.py)

```python
# При вызове enrich_orders_with_mapping
all_orders_data = enrich_orders_with_mapping(
    all_orders_data,
    matcher,
    interactive=True,
    excluded_manager=excluded_manager  # Передаём менеджер
)
```

### 3. Интерактивное маппинг

```python
# При обработке каждого товара
mapped_name, mapped_type = match_product_interactive(
    item,
    matcher,
    auto_mode=False,
    order_number=first_order,           # Номер заказа
    excluded_manager=excluded_manager   # Менеджер исключений
)

# Если пользователь отправил EXCLUDE
if mapped_name is None and mapped_type is None:
    # Заказ исключён, пропускаем все его товары
    continue
```

## Советы и лучшие практики

1. **Регулярно проверяйте список**:
   ```python
   manager = ExcludedOrdersManager()
   print(f"Исключено заказов: {manager.get_count()}")
   for order_num in manager.get_excluded_list():
       print(f"  • {order_num}")
   ```

2. **Делайте бэкап перед очисткой**:
   ```bash
   cp excluded_orders.json excluded_orders_backup_$(date +%Y%m%d).json
   ```

3. **Используйте EXCLUDE осторожно**: Исключённый заказ пропускается полностью, включая все товары.

4. **Файл excluded_orders.json в .gitignore**: Это ваш личный список, он не коммитится в репозиторий.

## Часто задаваемые вопросы

### Q: Можно ли восстановить исключённый заказ?

**A**: Да, двумя способами:
1. Программно: `manager.remove_excluded("order_number")`
2. Вручную: Удалите order_number из `excluded_orders.json`

### Q: Что будет, если удалить excluded_orders.json?

**A**: Файл будет создан заново при следующем исключении. Все предыдущие исключения будут потеряны.

### Q: Можно ли исключить заказ после парсинга?

**A**: Да, вручную добавьте order_number в файл или используйте API:
```python
manager = ExcludedOrdersManager()
manager.add_excluded("46206571-0593")
```

### Q: Как узнать, сколько заказов исключено?

**A**: Запустите тестовый скрипт или используйте:
```python
manager = ExcludedOrdersManager()
print(f"Исключено: {manager.get_count()}")
```

## Техническая документация

### Класс ExcludedOrdersManager

**Файл**: `excluded_manager.py`

**Методы**:
- `add_excluded(order_number)` - Добавить заказ в исключённые
- `remove_excluded(order_number)` - Удалить заказ из исключённых
- `is_excluded(order_number)` - Проверить, исключён ли заказ
- `filter_orders(orders_data)` - Отфильтровать список заказов
- `get_excluded_list()` - Получить список всех исключённых
- `get_count()` - Получить количество исключённых
- `clear_excluded()` - Очистить весь список

**Хранение**: `excluded_orders.json` (JSON файл с массивом order_number)

**Автосохранение**: После каждой операции (add/remove/clear)

---

Версия: v1.7.0  
Дата: 2025-10-07
