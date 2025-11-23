from bs4 import BeautifulSoup

with open('wb.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

# Найдем родителя с датой и пройдемся вверх
date_elem = soup.find('span', string=lambda t: t and 'ноября' in t)
if date_elem:
    print('Найден элемент с датой, идем вверх по дереву:\n')
    
    current = date_elem
    level = 0
    while current and level < 10:
        print(f'Уровень {level}: {current.name}, классы: {current.get("class")}')
        if current.name in ['li', 'div', 'article'] and current.get('class'):
            print(f'  -> Возможная карточка товара!')
            # Ищем название и цену
            print(f'  Содержимое (первые 800 символов):')
            print(f'  {str(current)[:800]}...\n')
        current = current.parent
        level += 1

print('\n' + '='*80)
print('Поиск всех карточек товаров...\n')

# Попробуем найти все li с определенным классом  
all_li = soup.find_all('li')
print(f'Всего <li>: {len(all_li)}')

# Найдем li которые содержат дату
date_li = [li for li in all_li if li.find('span', string=lambda t: t and 'ноября' in t)]
print(f'<li> с датами: {len(date_li)}')

if date_li:
    first = date_li[0]
    print(f'\nПервый <li> с датой:')
    print(f'Классы: {first.get("class")}')
    print(f'Содержимое:\n{str(first)[:1500]}...')
