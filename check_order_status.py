"""Проверка статусов в заказе"""
import json

with open('ozon_orders.json', encoding='utf-8') as f:
    data = json.load(f)

# Найти заказ 46206571-0591
orders = data['orders']
order = [o for o in orders if o['order_number'] == '46206571-0591'][0]

print(f"\n📦 Заказ: {order['order_number']}")
print(f"Всего товаров: {len(order['items'])}\n")

# Показать все товары с их статусами
print("Порядок в JSON:")
for idx, p in enumerate(order['items'], 1):
    name = p['name'][:40]
    status = p['status']
    mapped = p.get('mapped_name', 'НЕТ')
    quantity = p.get('quantity', 1)
    
    print(f"{idx:2}. status: {status:10} | qty: {quantity:2} | {name}")
