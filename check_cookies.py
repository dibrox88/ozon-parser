import json
from collections import Counter

with open('ozon_cookies.json', 'r', encoding='utf-8') as f:
    cookies = json.load(f)

print(f"Всего cookies: {len(cookies)}")

names = [c['name'] for c in cookies]
duplicates = Counter(names)
dups = {k: v for k, v in duplicates.items() if v > 1}

if dups:
    print(f"\n❌ Найдены дубликаты:")
    for name, count in dups.items():
        print(f"  - {name}: {count} раз(а)")
        # Показываем все экземпляры
        for i, c in enumerate(cookies):
            if c['name'] == name:
                print(f"    {i+1}. domain={c['domain']}, path={c['path']}, expires={c.get('expires', 'session')}")
else:
    print("\n✅ Дубликатов нет")

print(f"\n📋 Список уникальных cookies:")
unique_names = sorted(set(names))
for name in unique_names:
    print(f"  - {name}")
