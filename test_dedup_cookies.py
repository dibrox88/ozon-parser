"""
Тест дедупликации cookies - проверяем логику без браузера
"""
import json
from collections import Counter

# Загружаем текущие cookies с дубликатами
with open('ozon_cookies.json', 'r', encoding='utf-8') as f:
    cookies = json.load(f)

print(f"📦 Исходно: {len(cookies)} cookies")

# Показываем дубликаты
names = [c['name'] for c in cookies]
duplicates = Counter(names)
dups = {k: v for k, v in duplicates.items() if v > 1}

if dups:
    print(f"❌ Дубликаты ЕСТЬ:")
    for name, count in dups.items():
        print(f"  - {name}: {count} раз(а)")

# Применяем логику дедупликации
unique_cookies = {}
for cookie in cookies:
    name = cookie.get('name', '')
    expires = cookie.get('expires', -1)
    
    if name in unique_cookies:
        existing_expires = unique_cookies[name].get('expires', -1)
        if expires > existing_expires:
            print(f"🔄 {name}: заменяем (expires {existing_expires} -> {expires})")
            unique_cookies[name] = cookie
    else:
        unique_cookies[name] = cookie

cookies_deduplicated = list(unique_cookies.values())

print(f"\n✅ После дедупликации: {len(cookies_deduplicated)} cookies")

# Проверяем дубликаты
names_after = [c['name'] for c in cookies_deduplicated]
duplicates_after = Counter(names_after)
dups_after = {k: v for k, v in duplicates_after.items() if v > 1}

if dups_after:
    print(f"❌ Дубликаты ВСЁ ЕЩЁ ЕСТЬ:")
    for name, count in dups_after.items():
        print(f"  - {name}: {count} раз(а)")
else:
    print("✅ Дубликатов больше НЕТ!")

print(f"\n📋 Список уникальных cookies ({len(set(names_after))}):")
for name in sorted(set(names_after)):
    print(f"  - {name}")
