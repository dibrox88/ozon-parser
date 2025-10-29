# 🚀 Обновление v1.9.1 - Антидетект + Скриншоты

## Что изменилось:

### 1. ✅ Включена отправка скриншотов
- Восстановлена функция `sync_send_photo()` в `notifier.py`
- Теперь скриншоты будут отправляться в Telegram на каждом этапе

### 2. 🛡️ Установлен playwright-stealth
- Добавлена библиотека `playwright-stealth==2.0.0`
- Автоматическое применение stealth-техник к каждой странице
- Скрывает признаки автоматизации от антибот-систем Ozon

### 3. 🔧 Усилена защита от детекта
- Улучшены browser аргументы в `main.py`
- Расширенный JavaScript для подмены navigator свойств
- Canvas и WebGL fingerprint protection
- Более реалистичные плагины браузера

---

## Обновление на сервере:

### Вариант 1: Автоматический скрипт (Windows)
```powershell
.\update-server.ps1
```

### Вариант 2: Вручную
```powershell
# Копируем обновленные файлы
scp main.py notifier.py requirements-production.txt ozon@85.193.81.13:~/ozon_parser/

# Подключаемся к серверу
ssh ozon@85.193.81.13

# Устанавливаем новые зависимости
cd ~/ozon_parser
source venv/bin/activate
pip install playwright-stealth==2.0.0

# Перезапускаем сервисы
sudo systemctl restart ozon-parser-api

# Тестовый запуск
python main.py
```

---

## Проверка работы:

### 1. Локально (уже работает):
- [x] playwright-stealth установлен
- [x] Stealth-режим применяется
- [x] Главная страница Ozon открывается
- [ ] Ожидаем завершения авторизации

### 2. После обновления на сервере:
```bash
# Проверить что stealth загрузился
grep "playwright-stealth загружен" ~/ozon_parser/logs/ozon_parser_*.log

# Проверить что нет блокировок
tail -100 ~/ozon_parser/logs/ozon_parser_*.log | grep -i "блок\|block\|captcha"

# Проверить что скриншоты отправляются
ls -lh ~/ozon_parser/screenshots/ | tail -10
```

---

## Изменённые файлы:

- `main.py` - добавлен импорт и применение playwright-stealth
- `notifier.py` - включена отправка скриншотов
- `requirements-production.txt` - добавлен playwright-stealth==2.0.0
- `stealth.py` - новый модуль с хелперами (опциональный)
- `ANTIDETECT_GUIDE.md` - полная документация по антидетекту

---

## Если всё равно блокирует:

### План Б:
1. Попробовать Firefox вместо Chromium
2. Добавить прокси с российским IP
3. Увеличить задержки между действиями
4. Запускать в неголовном режиме (HEADLESS=False) локально

Детали в `ANTIDETECT_GUIDE.md` 📚

---

**Статус**: ✅ Локально работает, готово к обновлению на сервере
