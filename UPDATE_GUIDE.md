# 🔄 Обновление кода на сервере

После внесения изменений в локальные файлы, вам нужно обновить код на сервере.

## Способ 1: Автоматический скрипт (рекомендуется)

### Windows (PowerShell):
```powershell
.\update-server.ps1
```

### Linux/Mac:
```bash
chmod +x update-server.sh
bash update-server.sh
```

Скрипт:
- ✅ Показывает список файлов для обновления
- ✅ Запрашивает подтверждение
- ✅ Копирует только изменённые Python файлы
- ✅ Автоматически перезапускает API сервер
- ✅ Показывает результат и команды для проверки

---

## Способ 2: Ручное копирование конкретного файла

Если изменили только один файл:

### Windows (PowerShell):
```powershell
scp notifier.py ozon@85.193.81.13:~/ozon_parser/
```

### Linux/Mac:
```bash
scp notifier.py ozon@85.193.81.13:~/ozon_parser/
```

---

## Способ 3: Git (для продвинутых)

### На локальной машине:
```bash
git add .
git commit -m "Описание изменений"
git push origin main
```

### На сервере:
```bash
ssh ozon@85.193.81.13
cd ~/ozon_parser
git pull origin main
sudo systemctl restart ozon-parser-api
```

---

## После обновления

### 1. Проверьте что файл обновился:
```bash
ssh ozon@85.193.81.13
cd ~/ozon_parser
ls -lh notifier.py  # Проверить дату изменения
```

### 2. Перезапустите API сервер (если запущен):
```bash
sudo systemctl restart ozon-parser-api
sudo systemctl status ozon-parser-api
```

### 3. Тестовый запуск:
```bash
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

---

## Какие файлы обычно обновляются:

**Основная логика:**
- `main.py` - главный скрипт
- `parser.py` - парсинг заказов
- `auth.py` - авторизация

**Интеграции:**
- `notifier.py` - Telegram уведомления
- `sheets_manager.py` - работа с Google Sheets
- `sheets_sync.py` - синхронизация данных

**Обработка данных:**
- `product_matcher.py` - сопоставление товаров
- `bundle_manager.py` - работа с наборами
- `excluded_manager.py` - исключения

**API:**
- `api_server.py` - FastAPI сервер
- `config.py` - конфигурация

---

## Быстрое обновление только изменённых файлов

### Windows:
```powershell
# Обновить notifier.py (включить скриншоты)
scp notifier.py ozon@85.193.81.13:~/ozon_parser/

# Перезапустить сервисы
ssh ozon@85.193.81.13 "sudo systemctl restart ozon-parser-api"
```

### Linux/Mac:
```bash
# Обновить notifier.py
scp notifier.py ozon@85.193.81.13:~/ozon_parser/

# Перезапустить сервисы
ssh ozon@85.193.81.13 "sudo systemctl restart ozon-parser-api"
```

---

## Проверка логов после обновления

```bash
# Подключиться к серверу
ssh ozon@85.193.81.13

# Посмотреть логи парсера
tail -f ~/ozon_parser/logs/parser_*.log

# Посмотреть логи API сервера
tail -f ~/ozon_parser/logs/api_server*.log

# Посмотреть логи cron
tail -f ~/ozon_parser/logs/cron_*.log

# Посмотреть системные логи
sudo journalctl -u ozon-parser-api -f
```

---

## Откат изменений (если что-то пошло не так)

### Скопировать старую версию с локальной машины:
```bash
# Найти резервную копию
git checkout HEAD~1 notifier.py
scp notifier.py ozon@85.193.81.13:~/ozon_parser/
git checkout main  # Вернуться обратно
```

### Или восстановить из Git на сервере:
```bash
ssh ozon@85.193.81.13
cd ~/ozon_parser
git checkout notifier.py  # Отменить изменения
```

---

## Советы

1. **Всегда тестируйте локально** перед обновлением на сервере
2. **Делайте commit в Git** перед обновлением (для отката)
3. **Обновляйте по одному файлу**, если не уверены
4. **Проверяйте логи** после обновления
5. **Держите резервные копии** важных конфигурационных файлов (.env, google_credentials.json)

---

## Автоматическое обновление через Git (настройка)

### На сервере создайте скрипт:
```bash
cat > ~/ozon_parser/git-update.sh << 'EOF'
#!/bin/bash
cd ~/ozon_parser
git pull origin main
sudo systemctl restart ozon-parser-api
echo "✅ Обновление завершено: $(date)"
EOF

chmod +x ~/ozon_parser/git-update.sh
```

### Теперь обновление в одну команду:
```bash
ssh ozon@85.193.81.13 "~/ozon_parser/git-update.sh"
```
