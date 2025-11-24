"""
Скрипт для парсинга товаров из файла wb.html.
"""

from bs4 import BeautifulSoup
import re
import csv


def parse_price(price_text: str) -> str:
    """
    Парсит цену, убирает пробелы и знак ₽.
    Если нет цифр - возвращает исходный текст.
    """
    if not price_text:
        return ""
    
    # Ищем цифры в тексте
    digits = re.findall(r'\d+', price_text)
    if digits:
        # Убираем пробелы и знак ₽
        return ''.join(digits)
    
    return price_text.strip()


def parse_date(date_text: str) -> str:
    """
    Трансформирует дату из формата "Получен 22 ноября" в "22.11.2025".
    Если нет цифр - возвращает исходный текст.
    """
    if not date_text:
        return ""
    
    # Словарь месяцев
    months = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
    }
    
    # Ищем день и месяц
    match = re.search(r'(\d+)\s+([а-яё]+)', date_text.lower())
    if match:
        day = match.group(1).zfill(2)  # Добавляем ведущий ноль если нужно
        month_name = match.group(2)
        
        if month_name in months:
            month = months[month_name]
            
            # Ищем год (2024 или 2025)
            year_match = re.search(r'(202[4-5])', date_text)
            if year_match:
                year = year_match.group(1)
            else:
                from datetime import datetime
                year = str(datetime.now().year)  # Текущий год
                
            return f"{day}.{month}.{year}"
    
    # Если не удалось распарсить - возвращаем исходный текст
    return date_text.strip()


def parse_product_name(name_elem):
    """
    Извлечь название товара из элемента <p class="archive-item__brand">.
    Убирает бренд в <span> и оставляет только название после "/".
    """
    if not name_elem:
        return ''
    
    # Текст внутри p: <span>Brand</span> / Product Name
    # Используем separator=' ', чтобы гарантировать пробелы
    full_text = name_elem.get_text(separator=' ', strip=True)
    
    # Если есть разделитель " / ", берем правую часть
    if '/' in full_text:
        parts = full_text.split('/', 1)
        if len(parts) > 1:
            return parts[1].strip()
            
    # Fallback: если нет слэша, но есть span, убираем его текст
    span = name_elem.find('span')
    if span:
        span_text = span.get_text(strip=True)
        return full_text.replace(span_text, '').strip()
    
    return full_text


import json
import os

def load_mappings(file_path: str = 'product_mappings.json') -> dict:
    """
    Загружает маппинг товаров из JSON файла.
    """
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке маппинга: {e}")
        return {}


def get_standardized_name(name: str, mappings: dict) -> str:
    """
    Возвращает стандартизированное наименование товара на основе маппинга.
    Если совпадение не найдено, возвращает исходное название.
    """
    if not name or not mappings:
        return name
        
    # Нормализуем имя для поиска (как в ProductMatcher)
    normalized_name = " ".join(name.lower().split())
    
    # Пробуем найти с разными вариантами цвета (так как в HTML цвета может не быть)
    # Приоритет: Black -> White -> 0 -> без цвета
    variants = ['black', 'white', '0', '']
    
    for color in variants:
        if color:
            key = f"{normalized_name}|{color}"
        else:
            key = normalized_name
            
        if key in mappings:
            return mappings[key].get('mapped_name', name)
            
    return name


def parse_wb_html(file_path: str) -> list:
    """
    Парсит файл wb.html и извлекает товары.
    
    Returns:
        Список словарей с данными товаров (name, price, date)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    
    # Ищем все товары - они находятся в <li> с классом archive-item
    # Можно искать просто li, но лучше уточнить класс если он есть
    all_li = soup.find_all('li', class_='archive-item')
    
    # Если не нашли по классу, ищем все li (fallback)
    if not all_li:
        all_li = soup.find_all('li')
    
    print(f"Найдено элементов списка: {len(all_li)}")
    
    for li in all_li:
        # 1. Определяем статус заказа
        status = "Получен"
        status_elem = li.find('p', class_='archive-item__status')
        if status_elem:
            status = status_elem.get_text(strip=True)

        # 2. Определяем дату
        date_text = ""
        date_elem = li.find('p', class_='archive-item__receive-date')
        if date_elem:
            # Извлекаем текст из span'ов. Обычно "Получен" "17 января"
            # Используем separator=' ', чтобы получить "Получен 17 января"
            date_text = date_elem.get_text(separator=' ', strip=True)
        
        # Если статус "Отмена...", даты может и не быть в receive-date
        # Но мы не парсим btn-wrap по требованию
        
        # Проверяем, есть ли дата или статус (чтобы отсеять мусор)
        if not date_elem and not status_elem:
             # Попробуем найти по тексту "Получен", если класс не сработал
            if not li.find(string=lambda t: t and ('Получен' in t)):
                continue
        
        # --- Извлекаем название ---
        # <p class="archive-item__brand"><span>Brand</span> / Name</p>
        name_elem = li.find('p', class_='archive-item__brand')
        name = parse_product_name(name_elem)
        
        # --- Извлекаем цену ---
        # <div class="archive-item__price">219 ₽</div>
        price_elem = li.find('div', class_='archive-item__price')
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        price = parse_price(price_text)
        
        # --- Парсим дату ---
        date = parse_date(date_text)
        
        # Добавляем только если есть название
        if name:
            products.append({
                'name': name,
                'price': price,
                'date': date,
                'status': status
            })
    
    return products


def export_to_csv(products: list, output_file: str = 'wb_products.csv'):
    """
    Экспортирует товары в CSV для вставки в Google Sheets.
    """
    try:
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            
            # Заголовки
            writer.writerow(['Наименование', 'Цена', 'Дата', 'Статус'])
            
            # Данные
            for product in products:
                writer.writerow([
                    product.get('name', ''),
                    product.get('price', ''),
                    product.get('date', ''),
                    product.get('status', '')
                ])
        
        print(f"✓ Экспортировано {len(products)} товаров в {output_file}")
        
    except PermissionError:
        print(f"\n❌ Ошибка: Не удалось записать файл '{output_file}'.")
        print("Вероятно, он открыт в Excel или другой программе.")
        
        # Пробуем сохранить с новым именем
        new_file = output_file.replace('.csv', '_new.csv')
        print(f"Попытка сохранить в '{new_file}'...")
        
        try:
            with open(new_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['Наименование', 'Цена', 'Дата', 'Статус'])
                for product in products:
                    writer.writerow([
                        product.get('name', ''),
                        product.get('price', ''),
                        product.get('date', ''),
                        product.get('status', '')
                    ])
            print(f"✓ Экспортировано {len(products)} товаров в {new_file}")
        except Exception as e:
            print(f"❌ Не удалось сохранить файл: {e}")


def main():
    file_path = 'wb.html'
    
    print(f"Парсинг файла: {file_path}")
    products = parse_wb_html(file_path)
    
    print(f"\nНайдено товаров: {len(products)}")
    
    if products:
        # Показываем данные в виде таблицы
        print("\n" + "="*120)
        print(f"{'Наименование':<50} {'Цена':<10} {'Дата':<15} {'Статус':<20}")
        print("="*120)
        
        for product in products[:10]:  # Показываем первые 10
            print(f"{product['name']:<50} {product['price']:<10} {product['date']:<15} {product['status']:<20}")
        
        if len(products) > 10:
            print(f"... и еще {len(products) - 10} товаров")
        
        print("="*120)
        
        # Экспортируем в CSV
        export_to_csv(products)
        
        print("Файл wb_products.csv готов для импорта в Google Sheets")
    else:
        print("\nТовары не найдены. Проверьте структуру HTML.")


if __name__ == '__main__':
    main()
