import json

with open('ozon_orders.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

orders = data.get('orders', [])
order = [o for o in orders if o.get('order_number') == '46206571-0668'][0]

print(f'items_count (исходное количество): {order.get("items_count")}')
print(f'Всего записей в items сейчас: {len(order["items"])}')

# Считаем разбитые товары
split_items = [i for i in order['items'] if i.get('is_split')]
non_split_items = [i for i in order['items'] if not i.get('is_split')]

print(f'\nРазбитых записей (is_split=True): {len(split_items)}')
print(f'Неразбитых записей: {len(non_split_items)}')

if split_items:
    # Группируем по split_total
    split_groups = {}
    for item in split_items:
        total = item.get('split_total', 0)
        if total not in split_groups:
            split_groups[total] = 0
        split_groups[total] += 1
    
    print(f'\nГруппировка разбитых товаров:')
    for total, count in sorted(split_groups.items()):
        groups = count // total if total > 0 else 0
        print(f'  split_total={total}: {count} записей = {groups} групп(ы)')

# Вывод: Ожидается
original_count = order.get("items_count", 0)
if len(split_items) > 0:
    # Если все товары одинаковые и разбиты на 3
    first_split = split_items[0]
    split_total = first_split.get('split_total', 3)
    expected = original_count * split_total
    print(f'\n📊 Ожидалось: {original_count} товаров × {split_total} = {expected} записей')
    print(f'📊 Реально: {len(order["items"])} записей')
    print(f'📊 Разница: {len(order["items"]) - expected}')

