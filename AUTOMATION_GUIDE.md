# Автоматизация и управление парсером через Telegram

## 🤖 Telegram бот для управления парсером

Теперь вы можете управлять парсером прямо из Telegram!

### Доступные команды:

- `/start` - Приветствие и список команд
- `/help` - Подробная справка
- `/status` - Статус парсера (работает/готов, время последнего запуска)
- `/parse` - **Запустить парсинг вручную**

### Установка бота:

1. **На сервере выполните:**
   ```bash
   cd ~/ozon_parser
   chmod +x setup-telegram-bot.sh
   ./setup-telegram-bot.sh
   ```

2. **Бот установится как systemd сервис и запустится автоматически**

3. **Управление ботом:**
   ```bash
   # Статус
   sudo systemctl status ozon-bot
   
   # Перезапуск
   sudo systemctl restart ozon-bot
   
   # Остановка
   sudo systemctl stop ozon-bot
   
   # Логи
   tail -f ~/ozon_parser/logs/telegram_bot.log
   ```

4. **Проверка работы:**
   - Откройте Telegram
   - Найдите вашего бота
   - Отправьте `/start`
   - Используйте `/parse` для запуска парсинга!

---

## ⏰ Автоматический запуск по расписанию

Парсер запускается автоматически каждые 15 минут с 9:00 до 21:00 (МСК).

### Установка cron:

1. **На сервере выполните:**
   ```bash
   cd ~/ozon_parser
   chmod +x setup-cron-auto.sh
   ./setup-cron-auto.sh
   ```

2. **Проверка установки:**
   ```bash
   # Показать cron задачи
   crontab -l
   
   # Должна быть строка:
   # */15 9-21 * * * /home/ozon/ozon_parser/run_parser.sh
   ```

3. **Просмотр логов автозапуска:**
   ```bash
   tail -f ~/ozon_parser/logs/cron.log
   ```

### Расписание:

- **Время работы:** 9:00 - 21:00 МСК
- **Интервал:** Каждые 15 минут
- **Запусков в день:** ~48 раз
- **Логи:** `~/ozon_parser/logs/cron.log`

### Изменение расписания:

Отредактируйте cron:
```bash
crontab -e
```

Примеры:
```bash
# Каждые 30 минут (9:00-21:00)
*/30 9-21 * * * /home/ozon/ozon_parser/run_parser.sh

# Каждый час (9:00-21:00)
0 9-21 * * * /home/ozon/ozon_parser/run_parser.sh

# Каждые 10 минут (круглосуточно)
*/10 * * * * /home/ozon/ozon_parser/run_parser.sh
```

---

## 🍪 Уведомления об устаревших cookies

Теперь при обнаружении блокировки из-за устаревших cookies вы получите подробное уведомление в Telegram:

```
🍪 COOKIES УСТАРЕЛИ!

❌ Ozon блокирует доступ с текущими cookies.

📝 Действия:
1. Запустите на локальной машине:
   python export_cookies.py

2. Скопируйте cookies на сервер:
   scp ozon_cookies.json ozon@SERVER:~/ozon_parser/

⏰ Cookies нужно обновлять каждые 3-7 дней.
```

---

## 📊 Мониторинг работы

### 1. Логи парсера
```bash
# Основные логи
tail -f ~/ozon_parser/logs/ozon_parser_*.log

# Логи автозапуска
tail -f ~/ozon_parser/logs/cron.log

# Логи Telegram бота
tail -f ~/ozon_parser/logs/telegram_bot.log
```

### 2. Статус через Telegram
Отправьте боту `/status` для получения:
- Статус парсера (работает/готов)
- Время последнего запуска
- Сколько времени прошло

### 3. Проверка cron
```bash
# Список задач
crontab -l

# Последние запуски (из логов)
grep "Запуск парсера" ~/ozon_parser/logs/cron.log | tail -20
```

---

## 🔧 Устранение неполадок

### Бот не отвечает:
```bash
# Проверить статус
sudo systemctl status ozon-bot

# Посмотреть ошибки
tail -50 ~/ozon_parser/logs/telegram_bot_error.log

# Перезапустить
sudo systemctl restart ozon-bot
```

### Cron не запускается:
```bash
# Проверить права
chmod +x ~/ozon_parser/run_parser.sh

# Проверить логи
tail -50 ~/ozon_parser/logs/cron.log

# Проверить cron
crontab -l
```

### Парсер не запускается через бота:
```bash
# Проверить, что бот работает в правильной директории
ps aux | grep telegram_bot

# Проверить права на main.py
ls -la ~/ozon_parser/main.py

# Попробовать запустить вручную
cd ~/ozon_parser
source venv/bin/activate
python main.py
```

---

## ✅ Быстрый старт (все команды):

```bash
# На сервере
cd ~/ozon_parser

# 1. Установить Telegram бота
chmod +x setup-telegram-bot.sh
./setup-telegram-bot.sh

# 2. Настроить автозапуск
chmod +x setup-cron-auto.sh
./setup-cron-auto.sh

# 3. Проверить работу
sudo systemctl status ozon-bot
crontab -l

# 4. В Telegram отправьте /start боту
```

---

## 📝 Обновление cookies (каждые 3-7 дней)

**На локальной машине:**
```powershell
# 1. Экспорт cookies
python export_cookies.py

# 2. Копирование на сервер
scp ozon_cookies.json ozon@85.193.81.13:~/ozon_parser/
```

**Или через Telegram:**
- Бот автоматически уведомит об устаревших cookies
- Следуйте инструкциям из уведомления

---

## 🎯 Итого

✅ **Telegram бот** - запуск парсинга командой `/parse`
✅ **Автозапуск** - каждые 15 минут (9:00-21:00)
✅ **Уведомления** - об устаревших cookies
✅ **Мониторинг** - статус через `/status`
✅ **Логи** - полное логирование всех процессов

Парсер теперь полностью автоматизирован! 🚀
