# Настройка Google Sheets API

## Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Название проекта: `Ozon Parser` (или любое другое)

## Шаг 2: Включение API

1. В меню навигации выберите **APIs & Services** → **Library**
2. Найдите и включите следующие API:
   - **Google Sheets API**
   - **Google Drive API**

## Шаг 3: Создание Service Account

1. Перейдите в **APIs & Services** → **Credentials**
2. Нажмите **Create Credentials** → **Service Account**
3. Заполните форму:
   - **Service account name**: `ozon-parser-sheets`
   - **Service account ID**: автоматически заполнится
   - **Description**: `Service account for Ozon Parser to access Google Sheets`
4. Нажмите **Create and Continue**
5. Роль: **Editor** (или можно выбрать более ограниченную роль)
6. Нажмите **Done**

## Шаг 4: Создание ключа

1. На странице **Credentials** найдите созданный Service Account
2. Нажмите на него для редактирования
3. Перейдите на вкладку **Keys**
4. Нажмите **Add Key** → **Create new key**
5. Выберите формат **JSON**
6. Нажмите **Create**
7. Файл с ключом автоматически скачается

## Шаг 5: Установка ключа

1. Переименуйте скачанный файл в `google_credentials.json`
2. Поместите его в корневую директорию проекта `Ozon_Parser/`
3. Убедитесь, что файл находится в `.gitignore` (уже добавлен)

## Шаг 6: Настройка доступа к таблице

1. Откройте файл `google_credentials.json`
2. Найдите поле `"client_email"`, скопируйте email (вида `...@....iam.gserviceaccount.com`)
3. Откройте вашу Google Sheets таблицу
4. Нажмите **Share** (Поделиться)
5. Вставьте скопированный email
6. Дайте права **Viewer** (для чтения) или **Editor** (для записи)
7. Нажмите **Share**

## Шаг 7: Настройка .env

Добавьте в файл `.env`:

```bash
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit
GOOGLE_CREDENTIALS_FILE=google_credentials.json
```

Где:
- `GOOGLE_SHEETS_URL` - полный URL вашей таблицы
- `GOOGLE_CREDENTIALS_FILE` - путь к файлу с credentials (по умолчанию `google_credentials.json`)

## Структура таблицы

Парсер ожидает следующую структуру данных в таблице:

```
| Цена 1 | Название 1 | Тип 1 | Цена 2 | Название 2 | Тип 2 | ... |
|--------|------------|-------|--------|------------|-------|-----|
| 1000   | Товар A    | комп  | 2000   | Товар B    | расх  | ... |
| 1500   | Товар C    | комп  | 500    | Товар D    | расх  | ... |
```

**Каждые 3 столбца** содержат:
1. **Цена** - для справки
2. **Название** - используется для сопоставления
3. **Тип** - категория товара

Диапазон чтения: **A:AU** (можно настроить в коде)

## Проверка работы

Запустите тестовый скрипт:

```bash
python -c "from sheets_manager import SheetsManager; from config import Config; sm = SheetsManager(Config.GOOGLE_CREDENTIALS_FILE); print('✅ Подключение OK' if sm.connect() else '❌ Ошибка')"
```

## Устранение проблем

### Ошибка "Permission denied"
- Проверьте, что Service Account email добавлен в доступы к таблице
- Убедитесь, что API включены в Google Cloud Console

### Ошибка "File not found"
- Проверьте путь к `google_credentials.json`
- Убедитесь, что файл находится в корне проекта

### Ошибка "Invalid credentials"
- Пересоздайте ключ для Service Account
- Проверьте, что скачан файл в формате JSON

## Безопасность

⚠️ **ВАЖНО:**
- Никогда не коммитьте `google_credentials.json` в git
- Не публикуйте содержимое этого файла
- Регулярно проверяйте список Service Accounts и удаляйте неиспользуемые

## Дополнительные ресурсы

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [gspread Documentation](https://docs.gspread.org/)
- [Service Account Authentication](https://cloud.google.com/iam/docs/service-accounts)
