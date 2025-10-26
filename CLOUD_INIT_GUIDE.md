# 🚀 Использование Cloud-init на Timeweb

Cloud-init автоматизирует первоначальную настройку сервера при его создании.

---

## 📋 Что делает наш Cloud-init скрипт?

✅ **Создаёт пользователя** `ozon` с sudo правами  
✅ **Устанавливает все пакеты** (Python, Playwright зависимости, Nginx)  
✅ **Настраивает firewall** (открывает порты 22, 80, 443, 8000)  
✅ **Устанавливает timezone** Europe/Moscow  
✅ **Создаёт swap** 2 ГБ (для стабильности)  
✅ **Создаёт директории** проекта  

**Экономия времени**: ~15-20 минут ручной настройки!

---

## 🎯 Какой файл использовать?

### Вариант 1: С SSH ключом (рекомендуется) ✅

**Файл**: `cloud-init-timeweb.yaml`

**Подготовка:**

1. **Сгенерируйте SSH ключ** на вашем компьютере:

```powershell
# В PowerShell
ssh-keygen -t ed25519 -C "gamerlab@mail.ru"

# Нажмите Enter 3 раза (сохранить в дефолтное место, без пароля)
```

2. **Скопируйте публичный ключ**:

```powershell
# Просмотр ключа
type $env:USERPROFILE\.ssh\id_ed25519.pub

# Вывод будет примерно таким:
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAbCdEfGhIjKlMnOpQrStUvWxYz your_email@example.com
```

3. **Откройте** `cloud-init-timeweb.yaml`

4. **Найдите строку**:
```yaml
ssh_authorized_keys:
  - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... your_email@example.com
```

5. **Замените** на ваш ключ (полностью, одной строкой)

6. **Скопируйте весь файл** и вставьте в поле Cloud-init на Timeweb

**Преимущества:**
- ✅ Безопасный вход без пароля
- ✅ Защита от брутфорса
- ✅ Можно отключить вход по паролю

---

### Вариант 2: Без SSH ключа (проще) ⚠️

**Файл**: `cloud-init-simple.yaml`

**Что делать:**

1. **Откройте** `cloud-init-simple.yaml`
2. **Скопируйте весь файл**
3. **Вставьте** в поле Cloud-init на Timeweb
4. Готово!

**После создания сервера:**
- Подключайтесь: `ssh ozon@YOUR_SERVER_IP`
- Пароль: `OzonParser2025!`
- **Сразу смените пароль**: `passwd`

**Недостатки:**
- ⚠️ Нужно помнить пароль
- ⚠️ Менее безопасно чем SSH ключ

---

## 📝 Как использовать Cloud-init на Timeweb

### Шаг 1: При создании сервера

1. Выберите **"Облачный сервер"**
2. Конфигурация: **2 CPU / 4 ГБ / 50 ГБ**
3. ОС: **Ubuntu 24.04**
4. IP: **Публичный**
5. **Раскройте секцию "Cloud-init"** ⬇️

### Шаг 2: Вставка скрипта

1. **Скопируйте содержимое** файла:
   - `cloud-init-timeweb.yaml` (с SSH ключом) - РЕКОМЕНДУЕТСЯ
   - `cloud-init-simple.yaml` (простой)

2. **Вставьте** в поле Cloud-init на Timeweb

3. **Нажмите "Создать сервер"**

### Шаг 3: Ожидание (5-10 минут)

Cloud-init выполняется автоматически при первом запуске:
- Создание сервера: 2-3 минуты
- Выполнение Cloud-init: 5-7 минут
- **Итого**: ~10 минут

Вы получите email с:
- ✅ IP адресом сервера
- ✅ Паролем root (но мы не используем root, у нас есть пользователь `ozon`)

### Шаг 4: Проверка

```powershell
# Подключение
ssh ozon@YOUR_SERVER_IP

# Если используете SSH ключ - вход без пароля ✅
# Если используете пароль - введите: OzonParser2025!

# Проверка, что всё установлено
which python3        # Должен быть: /usr/bin/python3
python3 --version    # Должно быть: Python 3.12.x
which git            # Должен быть: /usr/bin/git
date                 # Должно быть: Europe/Moscow timezone

# Проверка firewall
sudo ufw status      # Должно быть: Status: active

# Проверка директорий
ls -la ~/ozon_parser/
# Должны быть: logs/ screenshots/ browser_state/
```

---

## 🔄 Что делать после Cloud-init?

Cloud-init подготовил сервер, но **код ещё не установлен**!

### Следующие шаги:

1. **Скопируйте файлы проекта** на сервер:

```powershell
# На вашем Windows компьютере
cd "C:\Users\фф\Documents\Apps\Ozon_Parser"
scp -r * ozon@YOUR_SERVER_IP:~/ozon_parser/
```

2. **Подключитесь** к серверу:

```powershell
ssh ozon@YOUR_SERVER_IP
```

3. **Запустите установку**:

```bash
cd ~/ozon_parser
chmod +x *.sh
bash deploy.sh
```

4. **Настройте .env**:

```bash
nano ~/ozon_parser/.env
```

5. **Скопируйте google_credentials.json**:

```powershell
# На вашем компьютере
scp google_credentials.json ozon@YOUR_SERVER_IP:~/ozon_parser/
```

6. **Запустите сервисы**:

```bash
bash setup-systemd.sh
bash setup-cron.sh
```

7. **Готово!** 🎉

---

## 🐛 Troubleshooting

### Не могу подключиться по SSH

**Проблема**: `Connection refused` или `Permission denied`

**Решения:**

1. **Подождите 10 минут** - Cloud-init ещё выполняется
2. **Проверьте IP адрес** - правильный ли?
3. **Используйте root** (временно):
   ```bash
   ssh root@YOUR_SERVER_IP
   # Пароль из email
   
   # Проверьте логи Cloud-init:
   tail -100 /var/log/cloud-init-output.log
   ```

### SSH ключ не работает

**Проблема**: Всё равно просит пароль

**Решения:**

1. **Проверьте ключ вставлен правильно** в `cloud-init-timeweb.yaml`
2. **Используйте правильный ключ**:
   ```powershell
   ssh -i $env:USERPROFILE\.ssh\id_ed25519 ozon@YOUR_SERVER_IP
   ```
3. **Проверьте на сервере**:
   ```bash
   sudo cat /home/ozon/.ssh/authorized_keys
   # Должен быть ваш ключ
   ```

### Cloud-init завис

**Проблема**: Прошло > 15 минут, сервер не готов

**Решения:**

1. **Подключитесь через root**:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

2. **Проверьте статус**:
   ```bash
   cloud-init status
   # Должно быть: status: done
   ```

3. **Посмотрите логи**:
   ```bash
   cat /var/log/cloud-init-output.log
   # Ищите ERROR или FAILED
   ```

4. **Если ошибки** - можно выполнить команды вручную из `QUICKSTART_DEPLOY.md`

---

## 💡 Советы

### Можно ли не использовать Cloud-init?

**Да!** Просто:
1. Создайте сервер **без** Cloud-init
2. Подключитесь как root
3. Следуйте **всем шагам** из `QUICKSTART_DEPLOY.md` вручную

Это займёт на 15-20 минут дольше, но даст полный контроль.

### Безопасность

После настройки:

```bash
# 1. Отключите вход root по SSH
sudo nano /etc/ssh/sshd_config
# Найдите: PermitRootLogin yes
# Замените на: PermitRootLogin no
sudo systemctl restart sshd

# 2. Настройте fail2ban (защита от брутфорса)
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Backup конфигурации

Сохраните использованный `cloud-init-*.yaml` файл:
- При пересоздании сервера можете использовать тот же скрипт
- Или изменить под новые требования

---

## ✅ Итого

| Параметр | Значение |
|----------|----------|
| **Рекомендуемый файл** | `cloud-init-timeweb.yaml` (с SSH ключом) |
| **Альтернатива** | `cloud-init-simple.yaml` (с паролем) |
| **Время выполнения** | 5-10 минут |
| **Экономия времени** | 15-20 минут ручной настройки |
| **Что устанавливает** | Python, Playwright, Nginx, Firewall, Swap |
| **Что НЕ устанавливает** | Код проекта (нужно scp копировать) |

**После Cloud-init нужно**:
1. Скопировать файлы проекта (scp)
2. Запустить `deploy.sh`
3. Настроить `.env`
4. Запустить сервисы

---

**Используете Cloud-init? Смело вставляйте скрипт при создании сервера!** 🚀
