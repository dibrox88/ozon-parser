"""Проверка порядка строк в Google Sheets"""
import gspread
from google.oauth2.service_account import Credentials
from config import Config

# Подключение
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(Config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Открыть таблицу (без gid)
spreadsheet = client.open_by_url(Config.GOOGLE_SHEETS_URL)

# Открыть нужный лист
worksheet = spreadsheet.get_worksheet_by_id(1946316259)

# Прочитать последние 40 строк (где записаны тестовые данные)
start_row = 13804
end_row = 13841

values = worksheet.get(f'A{start_row}:I{end_row}')

print(f"\n📊 Строки {start_row}-{end_row} в Google Sheets:")
print(f"Всего строк: {len(values)}\n")

# Показать только заказ 46206571-0591
print("🔍 Заказ 46206571-0591:")
for idx, row in enumerate(values, start_row):
    if len(row) > 1 and row[1] == '46206571-0591':  # B: order_number
        status = row[3] if len(row) > 3 else ''
        mapped = row[6] if len(row) > 6 else ''
        mapped_short = mapped[:30] if mapped else ''
        print(f"  Строка {idx}: status={status:10} | {mapped_short}")
