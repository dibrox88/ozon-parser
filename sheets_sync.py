"""
Модуль для синхронизации заказов с Google Sheets.
MVP версия: базовая запись новых заказов.
"""

import gspread
from google.oauth2.service_account import Credentials
from loguru import logger
from typing import List, Dict, Optional, Any, cast
from config import Config
from notifier import sync_send_message


class SheetsSynchronizer:
    """Класс для синхронизации заказов с Google Sheets."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Маппинг статусов для столбца D
    STATUS_MAPPING = {
        'получен': 'TRUE',      # Галочка
        'забрать': 'FALSE',     # Нет галочки (явно FALSE)
        'в пути': 'в пути',     # Текст
        'отменен': 'отменен'    # Текст
    }
    
    # Приоритет статусов для сортировки (используем маппированные значения)
    STATUS_PRIORITY = {
        'TRUE': 1,      # получен → TRUE
        'FALSE': 2,     # забрать → FALSE
        'в пути': 3,
        'отменен': 4
    }
    
    def __init__(self, credentials_file: str):
        """
        Инициализация синхронизатора.
        
        Args:
            credentials_file: Путь к JSON файлу с credentials от Google
        """
        self.credentials_file = credentials_file
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self.worksheet: Optional[gspread.Worksheet] = None
        
    def connect(self) -> bool:
        """Подключение к Google Sheets API с правами записи."""
        try:
            logger.info("🔄 Подключение к Google Sheets (запись)...")
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(creds)
            logger.info("✅ Подключение успешно (режим записи)")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            return False
    
    def open_sync_worksheet(self, spreadsheet_url: str, gid: str) -> bool:
        """
        Открыть лист для синхронизации по GID.
        
        Args:
            spreadsheet_url: URL таблицы
            gid: ID листа
            
        Returns:
            True если успешно
        """
        try:
            if self.client is None:
                raise RuntimeError("Клиент не инициализирован. Вызовите connect() сначала.")
            
            # Открываем таблицу
            self.spreadsheet = self.client.open_by_url(spreadsheet_url)
            
            # Ищем лист по GID
            for ws in self.spreadsheet.worksheets():
                if str(ws.id) == str(gid):
                    self.worksheet = ws
                    logger.info(f"📄 Открыт лист: {ws.title} (gid={gid})")
                    return True
            
            logger.error(f"❌ Лист с gid={gid} не найден")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка открытия листа: {e}")
            return False
    
    def ensure_buffer_rows(self, last_used_row: int, buffer_size: int = 1000) -> None:
        """
        Убедиться, что после последней использованной строки есть буфер пустых строк.
        
        Args:
            last_used_row: Номер последней использованной строки
            buffer_size: Размер буфера пустых строк (по умолчанию 1000)
        """
        try:
            if self.worksheet is None:
                return
            
            current_rows = self.worksheet.row_count
            required_rows = last_used_row + buffer_size
            
            if current_rows < required_rows:
                rows_to_add = required_rows - current_rows
                self.worksheet.add_rows(rows_to_add)
                logger.info(f"➕ Добавлено {rows_to_add} пустых строк (всего: {current_rows + rows_to_add}, буфер: {buffer_size})")
            else:
                logger.debug(f"✓ Буфер пустых строк достаточен ({current_rows - last_used_row} строк после данных)")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось добавить пустые строки: {e}")
    
    def get_existing_orders(self) -> List[str]:
        """
        Получить список существующих order_number из столбца B.
        
        Returns:
            Список номеров заказов
        """
        try:
            if self.worksheet is None:
                return []
            
            # Читаем столбец B (order_number)
            column_b = self.worksheet.col_values(2)  # 2 = столбец B
            
            # Фильтруем пустые и заголовки, приводим к строкам
            existing_orders: List[str] = [
                str(order_num) for order_num in column_b 
                if order_num and str(order_num) not in ['order_number', 'Номер заказа', '']
            ]
            
            logger.info(f"📋 Найдено существующих заказов в таблице: {len(existing_orders)}")
            return existing_orders
            
        except Exception as e:
            logger.error(f"❌ Ошибка чтения существующих заказов: {e}")
            return []
    
    def get_order_data(self, order_number: str) -> Dict[str, Any]:
        """
        Получить полные данные существующего заказа из Google Sheets.
        
        Args:
            order_number: Номер заказа
            
        Returns:
            Словарь с данными заказа: {
                'order_number': str,
                'rows': List[Dict],  # Список строк с данными
                'start_row': int,    # Номер первой строки в таблице
                'end_row': int       # Номер последней строки
            }
        """
        try:
            if self.worksheet is None:
                return {}
            
            # Читаем все данные (столбцы A-I)
            all_data = self.worksheet.get_all_values()
            
            order_rows = []
            start_row = None
            end_row = None
            
            for idx, row in enumerate(all_data, start=1):
                # Пропускаем пустые строки
                if len(row) < 2:
                    continue
                
                # Проверяем столбец B (order_number)
                if len(row) > 1 and str(row[1]) == str(order_number):
                    if start_row is None:
                        start_row = idx
                    
                    end_row = idx
                    
                    # Сохраняем данные строки
                    order_rows.append({
                        'row_number': idx,
                        'date': row[0] if len(row) > 0 else '',
                        'order_number': row[1] if len(row) > 1 else '',
                        'source': row[2] if len(row) > 2 else '',
                        'status': row[3] if len(row) > 3 else '',
                        'formula': row[4] if len(row) > 4 else '',
                        'price': row[5] if len(row) > 5 else '',
                        'mapped_name': row[6] if len(row) > 6 else '',
                        'mapped_type': row[7] if len(row) > 7 else '',
                        'reserved': row[8] if len(row) > 8 else ''
                    })
            
            if not order_rows:
                logger.debug(f"Заказ {order_number} не найден в таблице")
                return {}
            
            logger.debug(f"Найден заказ {order_number}: {len(order_rows)} строк (строки {start_row}-{end_row})")
            
            return {
                'order_number': order_number,
                'rows': order_rows,
                'start_row': start_row,
                'end_row': end_row,
                'total_rows': len(order_rows)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка чтения данных заказа {order_number}: {e}")
            return {}
    
    def compare_orders(self, json_order: Dict, sheets_order: Dict) -> Dict[str, Any]:
        """
        Сравнить данные заказа из JSON с данными из Google Sheets.
        
        Args:
            json_order: Данные заказа из JSON
            sheets_order: Данные заказа из Sheets (результат get_order_data)
            
        Returns:
            Словарь с результатами сравнения: {
                'has_changes': bool,
                'changes': List[str],  # Список описаний изменений
                'details': Dict  # Детальная информация об изменениях
            }
        """
        try:
            changes = []
            details = {}
            
            # Группируем строки из Sheets по mapped_name и status
            sheets_items = {}
            for row in sheets_order.get('rows', []):
                key = f"{row['mapped_name']}|{row['status']}"
                if key not in sheets_items:
                    sheets_items[key] = 0
                sheets_items[key] += 1  # Считаем количество строк (= quantity)
            
            # Группируем товары из JSON
            json_items = {}
            for item in json_order.get('items', []):
                mapped_name = item.get('mapped_name', item.get('name', ''))
                status = self.STATUS_MAPPING.get(item.get('status', ''), item.get('status', ''))
                quantity = item.get('quantity', 1)
                
                key = f"{mapped_name}|{status}"
                json_items[key] = {
                    'quantity': quantity,
                    'price': item.get('price', 0),
                    'mapped_name': mapped_name,
                    'status': status
                }
            
            # Сравниваем
            all_keys = set(sheets_items.keys()) | set(json_items.keys())
            
            for key in all_keys:
                sheets_qty = sheets_items.get(key, 0)
                json_item = json_items.get(key)
                json_qty = json_item['quantity'] if json_item else 0
                
                if sheets_qty != json_qty:
                    name, status = key.split('|', 1)
                    
                    if sheets_qty == 0:
                        # Новый товар
                        changes.append(f"➕ Добавлен: {name} ({status}) x{json_qty}")
                        details.setdefault('added', []).append({
                            'mapped_name': name,
                            'status': status,
                            'quantity': json_qty,
                            'price': json_item['price'] if json_item else 0
                        })
                    elif json_qty == 0:
                        # Удалённый товар
                        changes.append(f"➖ Удалён: {name} ({status}) x{sheets_qty}")
                        details.setdefault('removed', []).append({
                            'mapped_name': name,
                            'status': status,
                            'quantity': sheets_qty
                        })
                    else:
                        # Изменено количество
                        changes.append(f"🔄 Изменено: {name} ({status}) {sheets_qty} → {json_qty}")
                        details.setdefault('modified', []).append({
                            'mapped_name': name,
                            'status': status,
                            'old_quantity': sheets_qty,
                            'new_quantity': json_qty,
                            'price': json_item['price'] if json_item else 0
                        })
            
            has_changes = len(changes) > 0
            
            if has_changes:
                logger.info(f"🔍 Найдены изменения в заказе {json_order.get('order_number')}: {len(changes)} изменений")
            
            return {
                'has_changes': has_changes,
                'changes': changes,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка сравнения заказов: {e}")
            return {
                'has_changes': False,
                'changes': [],
                'details': {}
            }
    
    def update_order(self, order: Dict, sheets_data: Dict) -> bool:
        """
        Обновить существующий заказ в Google Sheets.
        Удаляет старые строки и вставляет новые на их место.
        
        Args:
            order: Данные заказа из JSON
            sheets_data: Данные заказа из Sheets (результат get_order_data)
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            if not sheets_data or self.worksheet is None:
                return False
            
            order_number = order.get('order_number', '')
            start_row = sheets_data.get('start_row')
            old_row_count = sheets_data.get('total_rows', 0)
            
            if start_row is None:
                logger.error(f"❌ Не указана начальная строка для заказа {order_number}")
                return False
            
            logger.info(f"🔄 Обновление заказа {order_number} (строки {start_row}-{start_row + old_row_count - 1})")
            
            # Подготавливаем новые данные
            new_rows = self.prepare_rows_from_order(order)
            new_rows = self.group_and_sort_rows(new_rows)
            new_rows = self.add_sum_formulas(new_rows, start_row)
            new_row_count = len(new_rows)
            
            logger.info(f"   Старых строк: {old_row_count}, новых строк: {new_row_count}")
            
            # Если количество строк изменилось
            if new_row_count > old_row_count:
                # Нужно добавить строки
                rows_to_add = new_row_count - old_row_count
                logger.info(f"   ➕ Добавление {rows_to_add} строк")
                for _ in range(rows_to_add):
                    self.worksheet.insert_row([], index=start_row)
                
            elif new_row_count < old_row_count:
                # Нужно удалить строки
                rows_to_delete = old_row_count - new_row_count
                logger.info(f"   ➖ Удаление {rows_to_delete} строк")
                # Удаляем с конца диапазона
                delete_start = start_row + new_row_count
                for _ in range(rows_to_delete):
                    self.worksheet.delete_rows(delete_start)
            
            # Записываем новые данные
            start_cell = f"A{start_row}"
            self.worksheet.update(range_name=start_cell, values=new_rows, value_input_option='USER_ENTERED')  # type: ignore[arg-type]
            logger.info(f"   ✅ Записано {new_row_count} строк")
            
            # Применяем границы
            self.add_group_borders(start_row, new_row_count, new_rows)
            
            logger.info(f"✅ Заказ {order_number} успешно обновлён")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления заказа: {e}")
            return False
    
    def sync_split_items_status(self, order: Dict) -> None:
        """
        Синхронизировать статусы для разбитых товаров.
        Если товар разбит на несколько единиц (is_split=True), 
        все единицы должны иметь одинаковый статус.
        
        Args:
            order: Данные заказа из JSON
        """
        try:
            if not order.get('items'):
                return
            
            order_number = order.get('order_number', '')
            
            # Группируем разбитые товары по (name, order_number, split_total)
            split_groups = {}
            
            for item in order['items']:
                if not item.get('is_split'):
                    continue
                
                name = item.get('mapped_name', item.get('name', ''))
                split_total = item.get('split_total', 0)
                status = item.get('status', '')
                
                # Ключ группы: имя товара + номер заказа + общее количество единиц
                group_key = f"{name}|{order_number}|{split_total}"
                
                if group_key not in split_groups:
                    split_groups[group_key] = {
                        'name': name,
                        'split_total': split_total,
                        'statuses': [],
                        'items': []
                    }
                
                split_groups[group_key]['statuses'].append(status)
                split_groups[group_key]['items'].append(item)
            
            # Проверяем каждую группу на несоответствие статусов
            for group_key, group_data in split_groups.items():
                statuses = group_data['statuses']
                
                # Если все статусы одинаковые - ничего не делаем
                if len(set(statuses)) == 1:
                    continue
                
                # Если статусы различаются - выбираем приоритетный
                # Приоритет: получен > в пункте выдачи > отменён > забрать
                priority_status = self._get_priority_status(statuses)
                
                logger.warning(
                    f"⚠️ Разбитый товар '{group_data['name']}' имеет разные статусы: {set(statuses)}"
                )
                logger.info(f"🔄 Синхронизация статуса на: '{priority_status}'")
                
                # Обновляем статусы всех единиц в группе
                for item in group_data['items']:
                    item['status'] = priority_status
                
                sync_send_message(
                    f"🔄 <b>Синхронизация статусов</b>\n"
                    f"Товар: {group_data['name']}\n"
                    f"Единиц: {group_data['split_total']}\n"
                    f"Новый статус: {priority_status}"
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации статусов разбитых товаров: {e}")
    
    def _get_priority_status(self, statuses: List[str]) -> str:
        """
        Выбрать приоритетный статус из списка.
        
        Args:
            statuses: Список статусов
            
        Returns:
            Приоритетный статус
        """
        # Приоритеты статусов (чем меньше число, тем выше приоритет)
        status_priority = {
            'получен': 1,
            'в пункте выдачи': 2,
            'отменён': 3,
            'забрать': 4
        }
        
        # Сортируем статусы по приоритету
        sorted_statuses = sorted(
            statuses,
            key=lambda s: status_priority.get(s, 999)
        )
        
        return sorted_statuses[0] if sorted_statuses else statuses[0]
    
    def prepare_rows_from_order(self, order: Dict) -> List[List]:
        """
        Подготовить строки для записи из одного заказа.
        Развернуть quantity в отдельные строки.
        
        Args:
            order: Словарь с данными заказа
            
        Returns:
            Список строк для записи
        """
        rows = []
        order_number = order.get('order_number', '')
        date = order.get('date', '')
        
        for item in order.get('items', []):
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)
            status = item.get('status', '')
            mapped_name = item.get('mapped_name', item.get('name', ''))
            mapped_type = item.get('mapped_type', '')
            
            # Проверяем, является ли товар разбитым на единицы
            is_split = item.get('is_split', False)
            split_index = item.get('split_index', '')
            split_total = item.get('split_total', '')
            
            # Создаём quantity дубликатов строк
            for _ in range(quantity):
                row = [
                    date,                                      # A: дата
                    order_number,                              # B: order_number
                    "Озон",                                    # C: всегда "Озон"
                    self.STATUS_MAPPING.get(status, status),  # D: status
                    "",                                        # E: формула (добавим позже)
                    price,                                     # F: price
                    mapped_name,                               # G: mapped_name
                    mapped_type,                               # H: mapped_type
                    "",                                        # I: пустой (резерв)
                    str(is_split) if is_split else "",        # J: is_split
                    str(split_index) if split_index else "",  # K: split_index
                    str(split_total) if split_total else ""   # L: split_total
                ]
                rows.append(row)
        
        logger.debug(f"Подготовлено {len(rows)} строк для заказа {order_number}")
        return rows
    
    def group_and_sort_rows(self, all_rows: List[List]) -> List[List]:
        """
        Группировать и сортировать строки: order_number → mapped_name → status.
        
        Args:
            all_rows: Список всех строк для записи
            
        Returns:
            Отсортированный список строк
        """
        if not all_rows:
            return all_rows
        
        # Сортируем: сначала по order_number (col B), потом по mapped_name (col G), потом по status (col D)
        def sort_key(row):
            order_number = row[1] if len(row) > 1 else ''  # B: order_number
            mapped_name = row[6] if len(row) > 6 else ''   # G: mapped_name
            status = row[3] if len(row) > 3 else ''        # D: status
            
            # Получаем приоритет статуса
            status_priority = self.STATUS_PRIORITY.get(status, 999)
            
            return (order_number, mapped_name.lower(), status_priority)
        
        sorted_rows = sorted(all_rows, key=sort_key)
        logger.info(f"🔄 Строки отсортированы по order_number → mapped_name → status")
        
        return sorted_rows
    
    def add_sum_formulas(self, sorted_rows: List[List], start_row: int) -> List[List]:
        """
        Добавить формулы SUM в столбец E для каждой группы заказа.
        
        Args:
            sorted_rows: Отсортированные строки
            start_row: Номер строки начала записи
            
        Returns:
            Строки с добавленными формулами
        """
        if not sorted_rows:
            return sorted_rows
        
        # Группируем по order_number (колонка B, индекс 1)
        current_order = None
        group_start_idx = 0
        
        for idx, row in enumerate(sorted_rows):
            order_num = row[1] if len(row) > 1 else ''  # B: order_number
            
            # Если начинается новая группа заказа
            if order_num != current_order:
                # Добавляем формулу для предыдущей группы
                if current_order is not None and group_start_idx < idx:
                    formula_row = start_row + group_start_idx
                    end_formula_row = start_row + idx - 1
                    formula = f"=SUM(F{formula_row}:F{end_formula_row})"
                    sorted_rows[group_start_idx][4] = formula  # E: формула
                
                # Начинаем новую группу
                current_order = order_num
                group_start_idx = idx
        
        # Добавляем формулу для последней группы
        if current_order is not None and group_start_idx < len(sorted_rows):
            formula_row = start_row + group_start_idx
            end_formula_row = start_row + len(sorted_rows) - 1
            formula = f"=SUM(F{formula_row}:F{end_formula_row})"
            sorted_rows[group_start_idx][4] = formula  # E: формула
        
        logger.info(f"➕ Добавлены формулы SUM для групп заказов")
        
        return sorted_rows
    
    def add_group_borders(self, start_row: int, num_rows: int, sorted_rows: List[List]) -> None:
        """
        Добавить границы:
        1. Верхняя граница 1px для первой строки каждого заказа (A-I)
        2. Нижняя граница 2px между группами товаров (G-I)
        
        Args:
            start_row: Номер строки начала данных
            num_rows: Количество строк
            sorted_rows: Отсортированные строки для определения границ
        """
        try:
            if self.worksheet is None or not sorted_rows:
                return
            
            requests = []
            
            # СНАЧАЛА очищаем все границы в диапазоне вставленных строк
            # Это предотвращает копирование форматирования при вставке
            clear_borders_request = {
                "updateBorders": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "startRowIndex": start_row - 1,  # -1 для 0-индексации
                        "endRowIndex": start_row + num_rows - 1,
                        "startColumnIndex": 0,  # A
                        "endColumnIndex": 9     # I (не включительно)
                    },
                    "top": {"style": "NONE"},
                    "bottom": {"style": "NONE"},
                    "left": {"style": "NONE"},
                    "right": {"style": "NONE"}
                }
            }
            requests.append(clear_borders_request)
            logger.info(f"🧹 Очищены границы в диапазоне строк {start_row}-{start_row + num_rows - 1}")
            
            # 1. Находим границы заказов (для верхней линии 1px)
            order_borders = []
            current_order = None
            
            for idx, row in enumerate(sorted_rows):
                order_num = row[1] if len(row) > 1 else ''  # B: order_number
                
                # Если начинается новый заказ
                if order_num != current_order:
                    order_borders.append(start_row + idx)
                    current_order = order_num
            
            # Добавляем верхние границы для заказов (A-I, 1px)
            for border_row in order_borders:
                request = {
                    "updateBorders": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "startRowIndex": border_row - 1,  # -1 для 0-индексации
                            "endRowIndex": border_row,
                            "startColumnIndex": 0,  # A
                            "endColumnIndex": 9     # I (не включительно)
                        },
                        "top": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0}
                        }
                    }
                }
                requests.append(request)
            
            logger.info(f"� Добавлены верхние границы для {len(order_borders)} заказов")
            
            # 2. Находим границы групп товаров по mapped_name (для нижней линии 2px)
            group_borders = []
            current_name = None
            current_order = None
            
            for idx, row in enumerate(sorted_rows):
                order_num = row[1] if len(row) > 1 else ''  # B: order_number
                mapped_name = row[6] if len(row) > 6 else ''  # G: mapped_name
                
                # Если начинается новая группа товаров (но не новый заказ)
                if mapped_name != current_name and current_name is not None and order_num == current_order:
                    # Граница после предыдущей группы
                    group_borders.append(start_row + idx - 1)
                
                current_name = mapped_name
                current_order = order_num
            
            # Добавляем нижние границы между группами товаров (G-I, 2px)
            for border_row in group_borders:
                request = {
                    "updateBorders": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "startRowIndex": border_row - 1,  # -1 для 0-индексации
                            "endRowIndex": border_row,
                            "startColumnIndex": 6,  # G
                            "endColumnIndex": 9      # I (не включительно)
                        },
                        "bottom": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0}
                        }
                    }
                }
                requests.append(request)
            
            logger.info(f"🔲 Добавлены нижние границы между {len(group_borders)} группами товаров")
            
            # Отправляем batch запрос
            if requests and self.spreadsheet:
                self.spreadsheet.batch_update({"requests": requests})
                logger.info(f"✅ Применены границы: {len(order_borders)} заказов + {len(group_borders)} групп товаров")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось добавить границы: {e}")
            # Не критично, продолжаем работу
    
    def sync_orders(self, orders_data: Dict[str, Any]) -> bool:
        """
        Синхронизировать заказы с Google Sheets (MVP версия).
        
        Args:
            orders_data: Словарь с данными заказов из ozon_orders.json
            
        Returns:
            True если успешно
        """
        try:
            logger.info("🔄 Начинаем синхронизацию заказов с Google Sheets...")
            sync_send_message("🔄 <b>Синхронизация с Google Sheets...</b>")
            
            # Получаем существующие заказы
            existing_orders = self.get_existing_orders()
            
            # Проверяем существующие заказы на изменения
            orders_list = orders_data.get('orders', [])
            updated_orders = []
            
            for order in orders_list:
                order_number = order.get('order_number')
                
                # Синхронизируем статусы разбитых товаров ПЕРЕД обновлением
                self.sync_split_items_status(order)
                
                # Если заказ существует - проверяем на изменения
                if order_number in existing_orders:
                    logger.info(f"🔍 Проверка заказа {order_number} на изменения...")
                    
                    # Получаем данные из Sheets
                    sheets_data = self.get_order_data(order_number)
                    
                    if sheets_data:
                        # Сравниваем
                        comparison = self.compare_orders(order, sheets_data)
                        
                        if comparison['has_changes']:
                            logger.warning(f"⚠️ Обнаружены изменения в заказе {order_number}")
                            
                            # Формируем сообщение для Telegram
                            changes_text = "\n".join([f"  • {change}" for change in comparison['changes'][:5]])
                            if len(comparison['changes']) > 5:
                                changes_text += f"\n  • ... ещё {len(comparison['changes']) - 5} изменений"
                            
                            sync_send_message(
                                f"⚠️ <b>Изменения в заказе {order_number}:</b>\n{changes_text}\n\n"
                                f"🔄 Обновляем данные..."
                            )
                            
                            # Обновляем заказ
                            if self.update_order(order, sheets_data):
                                updated_orders.append(order_number)
                                sync_send_message(f"✅ Заказ {order_number} обновлён")
                            else:
                                sync_send_message(f"❌ Не удалось обновить заказ {order_number}")
            
            if updated_orders:
                logger.info(f"🔄 Обновлено заказов: {len(updated_orders)}")
            
            # Фильтруем новые заказы
            new_orders = [
                order for order in orders_list
                if order.get('order_number') not in existing_orders
            ]
            
            # Если нет ни обновлений, ни новых заказов
            if not new_orders and not updated_orders:
                logger.info("✅ Нет изменений для синхронизации")
                sync_send_message("✅ Нет изменений для синхронизации")
                return True
            
            # Если есть новые заказы - добавляем их
            if new_orders:
                logger.info(f"📦 Найдено новых заказов: {len(new_orders)}")
                sync_send_message(f"📦 <b>Новых заказов:</b> {len(new_orders)}")
                
                # Подготавливаем все строки
                all_rows = []
                for order in new_orders:
                    rows = self.prepare_rows_from_order(order)
                    all_rows.extend(rows)
                
                logger.info(f"📝 Всего строк для добавления: {len(all_rows)}")
                
                # Проверяем, что worksheet не None
                if self.worksheet is None:
                    raise RuntimeError("Worksheet не инициализирован")
                
                # Находим последнюю непустую строку в столбце A
                column_a = self.worksheet.col_values(1)
                last_row = len([cell for cell in column_a if isinstance(cell, str) and cell.strip()]) + 1
                
                logger.info(f"📍 Начало записи с строки: {last_row}")
                
                # Группируем и сортируем строки
                all_rows = self.group_and_sort_rows(all_rows)
                
                # Добавляем формулы SUM
                all_rows = self.add_sum_formulas(all_rows, last_row)
                
                # Записываем данные
                if all_rows:
                    start_cell = f"A{last_row}"
                    # type: ignore для gspread API
                    self.worksheet.update(range_name=start_cell, values=all_rows, value_input_option='USER_ENTERED')  # type: ignore[arg-type]
                    
                    logger.info(f"✅ Записано {len(all_rows)} строк в таблицу")
                    
                    # Добавляем границы между группами
                    self.add_group_borders(last_row, len(all_rows), all_rows)
                    
                    # Убеждаемся, что есть буфер пустых строк после данных
                    last_used_row = last_row + len(all_rows) - 1
                    self.ensure_buffer_rows(last_used_row, buffer_size=1000)
                    
                    # Формируем итоговое сообщение
                    summary_parts = []
                    if updated_orders:
                        summary_parts.append(f"🔄 <b>Обновлено:</b> {len(updated_orders)}")
                    summary_parts.append(f"➕ <b>Добавлено:</b> {len(new_orders)}")
                    summary_parts.append(f"📝 <b>Записано строк:</b> {len(all_rows)}")
                    
                    sync_send_message("✅ " + "\n".join(summary_parts))
            elif updated_orders:
                # Были только обновления, без добавления новых
                sync_send_message(f"✅ <b>Обновлено заказов:</b> {len(updated_orders)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации: {e}")
            sync_send_message(f"❌ Ошибка синхронизации: {e}")
            return False


def sync_to_sheets(orders_json_path: str = "ozon_orders.json") -> bool:
    """
    Главная функция для синхронизации заказов с Google Sheets.
    
    Args:
        orders_json_path: Путь к JSON файлу с заказами
        
    Returns:
        True если успешно
    """
    try:
        import json
        
        # Загружаем данные из JSON
        with open(orders_json_path, 'r', encoding='utf-8') as f:
            orders_data = json.load(f)
        
        logger.info(f"📂 Загружен JSON: {orders_json_path}")
        logger.info(f"📊 Всего заказов: {orders_data.get('total_orders', 0)}")
        
        # Создаём синхронизатор
        sync = SheetsSynchronizer(Config.GOOGLE_CREDENTIALS_FILE)
        
        # Подключаемся
        if not sync.connect():
            return False
        
        # Открываем лист для синхронизации
        if not sync.open_sync_worksheet(Config.GOOGLE_SHEETS_URL, Config.GOOGLE_SHEETS_SYNC_GID):
            return False
        
        # Синхронизируем
        return sync.sync_orders(orders_data)
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации: {e}")
        return False
