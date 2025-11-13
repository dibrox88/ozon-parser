import requests
import time

BOT_TOKEN = '5394562199:AAFfYLaFmjtbblNrriyranFcqGOHz0PBYXo'
CHAT_ID = '368338076'
BASE_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

def send_message(text):
    response = requests.post(f'{BASE_URL}/sendMessage', json={'chat_id': CHAT_ID, 'text': text})
    return response.json()

# Отправляем команду /parse_range
print('Sending /parse_range...')
result = send_message('/parse_range')
print(f'Result: {result.get("ok", False)}')

# Ждём ответа бота
time.sleep(3)

# Отправляем первый номер заказа (последний)
print('\nSending 46206571-0710...')
result = send_message('46206571-0710')
print(f'Result: {result.get("ok", False)}')

# Ждём ответа бота
time.sleep(3)

# Отправляем количество заказов
print('\nSending 3...')
result = send_message('3')
print(f'Result: {result.get("ok", False)}')

print('\n✅ Done! Check Telegram and parser logs.')
print('To view logs: ssh ozon@85.193.81.13 "tail -f /home/ozon/ozon_parser/logs/telegram_bot.log"')
