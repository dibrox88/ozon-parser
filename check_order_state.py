#!/usr/bin/env python3
"""Check current state of order in Google Sheets."""
import gspread
import re
from google.oauth2.service_account import Credentials
from config import Config

url = Config.GOOGLE_SHEETS_URL
match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
spreadsheet_id = match.group(1)

scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('google_credentials.json', scopes=scopes)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(spreadsheet_id)
worksheet = spreadsheet.get_worksheet_by_id(int(Config.GOOGLE_SHEETS_SYNC_GID))

all_data = worksheet.get_all_values()
order_data = []
for idx, row in enumerate(all_data, start=1):
    if len(row) > 1 and str(row[1]) == '46206571-0700':
        col_i = row[8].strip() if len(row) > 8 and row[8] else ''
        col_k = row[10].strip() if len(row) > 10 and row[10] else ''
        order_data.append({'row': idx, 'I': col_i, 'K': col_k})

print(f'=== Текущее состояние заказа 46206571-0700 ===')
print(f'Всего строк: {len(order_data)}')
print(f'Диапазон: {order_data[0]["row"]}-{order_data[-1]["row"]}')

with_article = [d for d in order_data if d['I']]
with_k_only = [d for d in order_data if not d['I'] and d['K']]
empty_ip = [d for d in order_data if not d['I'] and not d['K']]

print(f'\nС артикулом (I): {len(with_article)}')
for d in with_article:
    print(f"  {d['row']}: {d['I']}")

print(f'\nТолько K (без I): {len(with_k_only)}')
print(f'Пустые I и K: {len(empty_ip)}')

# Проверяем JSON
import json
data = json.load(open('ozon_orders.json'))
orders = data.get('orders', data) if isinstance(data, dict) else data
order = [o for o in orders if o.get('order_number') == '46206571-0700']
if order:
    items = order[0].get('items', [])
    total = sum(i.get('quantity', 1) for i in items)
    print(f'\n=== Данные из JSON ===')
    print(f'Позиций: {len(items)}, строк после парсинга: {total}')
    
    # Моделируем что получится после парсинга
    print(f'\n=== МОДЕЛИРОВАНИЕ РЕЗУЛЬТАТА ===')
    print(f'Было строк: {len(order_data)}')
    print(f'Будет строк: {total}')
    print(f'\nДанные I-P для переноса:')
    print(f'  - С артикулом: {len(with_article)} (все 24 перенесутся в первые 24 строки)')
    print(f'  - Только K: {len(with_k_only)} (из 26 перенесется {min(len(with_k_only), total - len(with_article))})')
    
    will_be_lost = len(with_article) + len(with_k_only) - total
    if will_be_lost > 0:
        print(f'\n⚠️ ПОТЕРЯЕТСЯ: {will_be_lost} записей с данными K (так как строк станет меньше)')
    else:
        print(f'\n✅ Все данные I-P будут сохранены')
