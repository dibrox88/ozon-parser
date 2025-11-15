#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тест парсинга цен с запятыми и точками."""

test_cases = [
    '1 443,97 ₽',    # Европейский формат с запятой
    '25740 ₽',       # Целое число
    '534.50 ₽',      # Точка как разделитель
    '1234,56 ₽',     # Запятая
    '1 234,56 ₽',    # Пробелы + запятая
    '12 345 ₽',      # Только пробелы
]

print("Тестирование парсинга цен:")
print("-" * 50)

for case in test_cases:
    price_str = case.replace('₽', '').replace(' ', '').replace('\xa0', '').replace('\u202f', '').replace(',', '.').strip()
    try:
        price = float(price_str)
        print(f"✅ '{case:20}' -> {price}")
    except ValueError as e:
        print(f"❌ '{case:20}' -> ERROR: {e}")
