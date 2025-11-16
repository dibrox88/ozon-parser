"""
Модуль для синхронизации заказов с Google Sheets.
MVP версия: базовая запись новых заказов.
"""

import gspread
import json
from google.oauth2.service_account import Credentials
from loguru import logger
from typing import List, Dict, Optional, Any, cast
from config import Config
from notifier import sync_send_message, sync_wait_for_input
import time


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
        self._lost_i_values: List[Dict[str, str]] = []  # Список потерянных значений колонки I
        self.product_mappings: Dict[str, Any] = {}  # Загруженные маппинги товаров
        self._load_product_mappings()
    
    def _load_product_mappings(self) -> None:
        """Загрузить product_mappings.json для получения split_units."""
        try:
            with open('product_mappings.json', 'r', encoding='utf-8') as f:
                self.product_mappings = json.load(f)
            logger.debug(f"Загружено {len(self.product_mappings)} товаров из product_mappings.json")
        except Exception as e:
            logger.warning(f"Не удалось загрузить product_mappings.json: {e}")
            self.product_mappings = {}
    
    def _get_split_units(self, mapped_name: str, color: str = '') -> int:
        """
        Получить split_units для товара.
        
        Args:
            mapped_name: Название товара (mapped_name)
            color: Цвет товара
            
        Returns:
            Количество единиц в упаковке (по умолчанию 1)
            Например, если split_units=3 и quantity=30, то будет 90 строк (30*3)
        """
        # Формируем ключ как в product_matcher
        key = f"{mapped_name.lower()}|{color.lower()}" if color else mapped_name.lower()
        
        # Ищем товар в маппингах
        product_info = self.product_mappings.get(key, {})
        return product_info.get('split_units', 1)
        
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
                color = item.get('color', '')
                
                # Получаем split_units для этого товара
                split_units = self._get_split_units(mapped_name, color)
                
                # Рассчитываем ожидаемое количество строк
                expected_rows = quantity * split_units
                
                key = f"{mapped_name}|{status}"
                json_items[key] = {
                    'quantity': expected_rows,  # Количество строк, а не упаковок!
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
        КРИТИЧНО: Сохраняет данные в колонке I при обновлении.
        
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
            new_row_count = len(new_rows)
            
            logger.info(f"   Старых строк: {old_row_count}, новых строк: {new_row_count}")
            
            # КРИТИЧНО: Сохраняем данные из колонки I ПЕРЕД любыми изменениями
            # Сохраняем по ключу (mapped_name, status) для точного сопоставления
            column_i_mapping = {}
            if old_row_count > 0:
                try:
                    # Читаем все данные старого диапазона (A-I)
                    old_range = f"A{start_row}:I{start_row + old_row_count - 1}"
                    old_data = self.worksheet.get(old_range)
                    
                    for row in old_data:
                        if len(row) > 8 and row[8]:  # Если есть значение в колонке I
                            mapped_name = row[6] if len(row) > 6 else ''  # G: mapped_name
                            status = row[3] if len(row) > 3 else ''       # D: status
                            key = f"{mapped_name}|{status}"
                            
                            # Сохраняем значение I для каждого уникального товара
                            if key not in column_i_mapping:
                                column_i_mapping[key] = []
                            column_i_mapping[key].append(row[8])
                    
                    logger.info(f"   💾 Сохранено {len(column_i_mapping)} уникальных значений из колонки I")
                except Exception as e:
                    logger.warning(f"   ⚠️ Не удалось прочитать колонку I: {e}")
            
            # Корректируем количество строк
            if new_row_count > old_row_count:
                # Нужно добавить строки В КОНЕЦ диапазона
                rows_to_add = new_row_count - old_row_count
                logger.info(f"   ➕ Добавление {rows_to_add} строк в конец диапазона")
                insert_position = start_row + old_row_count
                for _ in range(rows_to_add):
                    self.worksheet.insert_row([], index=insert_position)
                
            elif new_row_count < old_row_count:
                # Нужно удалить строки с конца
                rows_to_delete = old_row_count - new_row_count
                logger.info(f"   ➖ Удаление {rows_to_delete} строк с конца")
                delete_start = start_row + new_row_count
                for _ in range(rows_to_delete):
                    self.worksheet.delete_rows(delete_start)
            
            # Добавляем формулы SUM с учетом финального количества строк
            new_rows = self.add_sum_formulas(new_rows, start_row)
            
            # Восстанавливаем данные из колонки I в новые строки
            # ПОРЯДОК: Сначала D="TRUE", потом D="FALSE" и остальные
            # Сопоставление ТОЛЬКО по G (mapped_name), НЕ по статусу
            
            # Группируем старые значения I ТОЛЬКО по G (mapped_name)
            i_values_by_name = {}
            for key, values in column_i_mapping.items():
                mapped_name = key.split('|')[0]  # Берем только название, без статуса
                if mapped_name not in i_values_by_name:
                    i_values_by_name[mapped_name] = []
                i_values_by_name[mapped_name].extend(values)
            
            # Счетчик для каждого названия товара
            name_counters = {}

            # Интерактивное сопоставление для новых названий, которых нет в старых данных
            existing_names = list(i_values_by_name.keys())

            # Функция для попытки интерактивного сопоставления через бота
            def try_interactive_mapping(target_name: str) -> bool:
                """Попытаться сопоставить target_name с существующими именами через Telegram.
                Возвращает True, если сопоставление выполнено, False в противном случае.
                """
                if not existing_names:
                    return False

                # Показываем ВСЕ доступные варианты (без автоматического фильтра)
                candidates = [name for name in existing_names if i_values_by_name.get(name)]
                if not candidates:
                    return False

                # Формируем сообщение с вариантами
                msg = f"🔄 <b>Сопоставление колонки I</b>\n\n"
                msg += f"📦 Новое название: <code>{target_name}</code>\n\n"
                msg += f"Доступные старые названия (со значениями I):\n"
                
                # Показываем первые 15 вариантов
                display_count = min(15, len(candidates))
                for i in range(display_count):
                    c = candidates[i]
                    count = len(i_values_by_name.get(c, []))
                    msg += f"{i+1}. <code>{c}</code> ({count} знач.)\n"
                
                if len(candidates) > display_count:
                    msg += f"... ещё {len(candidates) - display_count} вариантов\n"
                
                msg += f"\n0. Пропустить (оставить I пустым)\n\n"
                msg += f"💬 Выберите номер (0-{len(candidates)}):" 

                # Отправляем промпт и ждём ответа
                try:
                    response = sync_wait_for_input(msg, timeout=300)
                except Exception as e:
                    logger.warning(f"Не удалось запросить сопоставление для '{target_name}': {e}")
                    return False

                if not response:
                    logger.info(f"Сопоставление для '{target_name}' не выполнено (нет ответа)")
                    return False

                # Разбираем ответ
                try:
                    choice = int(response.strip())
                except ValueError:
                    logger.info(f"Неверный ответ при сопоставлении '{target_name}': {response}")
                    sync_send_message(f"❌ Ожидается число от 0 до {len(candidates)}")
                    return False

                if choice == 0:
                    # Собираем потерянные значения для этого названия
                    lost_values = i_values_by_name.get(target_name, [])
                    if not lost_values:
                        # Ищем значения среди старых названий
                        for old_name, values in i_values_by_name.items():
                            if values:  # Есть непустые значения
                                lost_values = values
                                break
                    
                    logger.info(f"Пользователь пропустил сопоставление для '{target_name}'")
                    
                    msg = f"⏭️ Пропущено: <code>{target_name}</code>"
                    if lost_values:
                        msg += f"\n\n❗ <b>Потеряно значений:</b> {len(lost_values)}"
                        for val in lost_values[:5]:
                            if val:
                                msg += f"\n  • {val}"
                        if len(lost_values) > 5:
                            msg += f"\n  • ... ещё {len(lost_values) - 5}"
                    
                    sync_send_message(msg)
                    return False

                if 1 <= choice <= len(candidates):
                    chosen = candidates[choice - 1]
                    # Переносим старые I значения под новое имя
                    i_values_by_name[target_name] = list(i_values_by_name.get(chosen, []))
                    logger.info(f"Сопоставлено '{target_name}' -> '{chosen}' и восстановлены {len(i_values_by_name[target_name])} значений I")
                    sync_send_message(f"✅ Сопоставлено: <code>{target_name}</code> → <code>{chosen}</code> ({len(i_values_by_name[target_name])} знач.)")
                    return True
                
                # Неверный номер
                sync_send_message(f"❌ Неверный номер: {choice}")
                return False

            # ЭТАП 1: Заполняем строки где D="TRUE" (получен)
            for row in new_rows:
                mapped_name = row[6] if len(row) > 6 else ''  # G: mapped_name
                status = row[3] if len(row) > 3 else ''       # D: status

                if status == "TRUE":
                    # Инициализируем счетчик для этого товара
                    if mapped_name not in name_counters:
                        name_counters[mapped_name] = 0

                    # Если нет известных значений для этого названия,
                    # попробуем интерактивно сопоставить их с существующими
                    if mapped_name and mapped_name not in i_values_by_name:
                        mapped = try_interactive_mapping(mapped_name)
                        if not mapped:
                            logger.warning(f"⚠️ Не найдено соответствий для '{mapped_name}' (D=TRUE), оставляем I пустым")

                    # Восстанавливаем значение I по названию товара (G)
                    i_value = ""
                    if mapped_name in i_values_by_name and name_counters[mapped_name] < len(i_values_by_name[mapped_name]):
                        i_value = i_values_by_name[mapped_name][name_counters[mapped_name]]
                        name_counters[mapped_name] += 1

                    # Добавляем значение I в строку
                    if len(row) > 8:
                        row[8] = i_value
                    else:
                        while len(row) < 8:
                            row.append("")
                        row.append(i_value)

            # ЭТАП 2: Заполняем строки где D!="TRUE" (FALSE, в пути, отменен и т.д.)
            for row in new_rows:
                mapped_name = row[6] if len(row) > 6 else ''  # G: mapped_name
                status = row[3] if len(row) > 3 else ''       # D: status

                if status != "TRUE":
                    # Инициализируем счетчик для этого товара
                    if mapped_name not in name_counters:
                        name_counters[mapped_name] = 0

                    # Если нет известных значений для этого названия,
                    # попробуем интерактивно сопоставить их с существующими
                    if mapped_name and mapped_name not in i_values_by_name:
                        mapped = try_interactive_mapping(mapped_name)
                        if not mapped:
                            logger.warning(f"⚠️ Не найдено соответствий для '{mapped_name}' (D!=TRUE), оставляем I пустым")

                    # Восстанавливаем значение I по названию товара (G)
                    i_value = ""
                    if mapped_name in i_values_by_name and name_counters[mapped_name] < len(i_values_by_name[mapped_name]):
                        i_value = i_values_by_name[mapped_name][name_counters[mapped_name]]
                        name_counters[mapped_name] += 1

                    # Добавляем значение I в строку
                    if len(row) > 8:
                        row[8] = i_value
                    else:
                        while len(row) < 8:
                            row.append("")
                        row.append(i_value)
            
            # Записываем новые данные (только A-H, НЕ трогаем I)
            # Разбиваем данные: отдельно A-H и отдельно I
            rows_without_i = [row[:8] for row in new_rows]  # Только A-H
            
            # Обновляем A-H
            range_a_h = f"A{start_row}:H{start_row + new_row_count - 1}"
            self.worksheet.update(range_name=range_a_h, values=rows_without_i, value_input_option='USER_ENTERED')  # type: ignore[arg-type]
            logger.info(f"   ✅ Записано {new_row_count} строк (A-H)")
            
            # Восстанавливаем колонку I
            i_values = [[row[8] if len(row) > 8 else ""] for row in new_rows]
            i_range = f"I{start_row}:I{start_row + new_row_count - 1}"
            self.worksheet.update(range_name=i_range, values=i_values, value_input_option='USER_ENTERED')  # type: ignore[arg-type]
            logger.info(f"   ✅ Восстановлена колонка I (сопоставлено по названию товара)")
            
            # Собираем потерянные значения колонки I (которые не были восстановлены)
            lost_i_values = []
            for old_name, values in i_values_by_name.items():
                used_count = name_counters.get(old_name, 0)
                if used_count < len(values):
                    # Есть неиспользованные значения
                    unused = values[used_count:]
                    for val in unused:
                        if val:  # Только непустые
                            lost_i_values.append({
                                'old_name': old_name,
                                'value': val
                            })
                            logger.warning(f"❗ Потеряно значение I: {old_name} = {val}")
            
            # Сохраняем информацию о потерянных значениях для отчета
            if lost_i_values:
                if not hasattr(self, '_lost_i_values'):
                    self._lost_i_values = []
                self._lost_i_values.extend(lost_i_values)
            
            # КРИТИЧНО: Очищаем границы ПОСЛЕ записи данных, но ПЕРЕД добавлением новых границ
            # Иначе новые вставленные строки будут иметь старые границы
            self._clear_borders_for_range(start_row, new_row_count)
            
            # Применяем границы ПОСЛЕ всех манипуляций со строками
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
            color = item.get('color', '')
            
            # Получаем split_units для этого товара
            split_units = self._get_split_units(mapped_name, color)
            
            # Рассчитываем реальное количество строк
            actual_rows = quantity * split_units
            
            # Проверяем, является ли товар разбитым на единицы
            is_split = item.get('is_split', False)
            split_index = item.get('split_index', '')
            split_total = item.get('split_total', '')
            
            # Формируем JSON для столбца Q с информацией о разбивке
            split_info = ""
            if is_split and split_index and split_total:
                split_data = {
                    'is_split': True,
                    'split_index': split_index,
                    'split_total': split_total
                }
                split_info = json.dumps(split_data, ensure_ascii=False)
            
            # Создаём actual_rows дубликатов строк (учитываем split_units)
            for _ in range(actual_rows):
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
                    "", "", "", "", "",                        # J-N: пустые столбцы
                    "",                                        # O: пустой
                    "",                                        # P: пустой
                    split_info                                 # Q: split info (JSON)
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
    
    def _clear_borders_for_range(self, start_row: int, num_rows: int) -> None:
        """
        Очистить ВСЕ границы (внешние + внутренние) для указанного диапазона строк по ВСЕМ столбцам.
        
        Args:
            start_row: Номер строки начала диапазона
            num_rows: Количество строк в диапазоне
        """
        try:
            if self.worksheet is None or num_rows == 0:
                return
            
            clear_borders_request = {
                "updateBorders": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "startRowIndex": start_row - 1,  # -1 для 0-индексации
                        "endRowIndex": start_row + num_rows - 1
                        # НЕ указываем startColumnIndex и endColumnIndex = очистка по ВСЕМ столбцам
                    },
                    # Очистка ВСЕХ границ: внешних и внутренних
                    "top": {"style": "NONE"},
                    "bottom": {"style": "NONE"},
                    "left": {"style": "NONE"},
                    "right": {"style": "NONE"},
                    "innerHorizontal": {"style": "NONE"},  # Горизонтальные границы между строками
                    "innerVertical": {"style": "NONE"}      # Вертикальные границы между столбцами
                }
            }
            
            # Отправляем очистку ОТДЕЛЬНЫМ запросом
            if self.spreadsheet:
                self.spreadsheet.batch_update({"requests": [clear_borders_request]})
                logger.info(f"🧹 Очищены границы (ВСЕ столбцы) для диапазона: строки {start_row}-{start_row + num_rows - 1}")
        
        except Exception as e:
            logger.warning(f"⚠️ Не удалось очистить границы: {e}")
    
    def add_group_borders(self, start_row: int, num_rows: int, sorted_rows: List[List]) -> None:
        """
        Добавить границы:
        1. Верхняя граница 1px для первой строки каждого заказа (A-I, вся строка)
        2. Нижняя граница 1px на последнюю строку каждого заказа (A-I, вся строка)
        3. Нижняя граница 1px между группами товаров внутри заказа (G-I)
        
        ВАЖНО: Границы должны быть очищены ДО вызова этого метода через _clear_borders_for_range()
        
        Args:
            start_row: Номер строки начала данных
            num_rows: Количество строк (ВЕСЬ заказ после вставки/удаления)
            sorted_rows: Отсортированные строки для определения границ
        """
        try:
            if self.worksheet is None or not sorted_rows:
                return
            
            # Создаем запросы для добавления границ
            requests = []
            
            # 1. Находим границы заказов (для верхней линии 1px)
            order_borders = []
            current_order = None
            
            for idx, row in enumerate(sorted_rows):
                order_num = row[1] if len(row) > 1 else ''  # B: order_number
                
                # Если начинается новый заказ
                if order_num != current_order:
                    order_borders.append(start_row + idx)
                    current_order = order_num
            
            # Добавляем верхние границы для заказов (ВСЯ СТРОКА, 1px)
            for border_row in order_borders:
                request = {
                    "updateBorders": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "startRowIndex": border_row - 1,  # -1 для 0-индексации
                            "endRowIndex": border_row
                            # НЕ указываем startColumnIndex и endColumnIndex = граница на ВСЮ строку
                        },
                        "top": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0}
                        }
                    }
                }
                requests.append(request)
            
            logger.info(f"📐 Добавлены верхние границы для {len(order_borders)} заказов")
            
            # 1б. Находим последние строки каждого заказа (для нижней линии 1px на всю строку)
            order_last_rows = []
            current_order = None
            last_row_idx = None
            
            for idx, row in enumerate(sorted_rows):
                order_num = row[1] if len(row) > 1 else ''  # B: order_number
                
                if order_num != current_order:
                    # Если был предыдущий заказ, сохраняем его последнюю строку
                    if current_order is not None and last_row_idx is not None:
                        order_last_rows.append(last_row_idx)
                    current_order = order_num
                
                last_row_idx = start_row + idx
            
            # Добавляем последнюю строку самого последнего заказа
            if last_row_idx is not None:
                order_last_rows.append(last_row_idx)
            
            # Добавляем нижние границы для последних строк заказов (ВСЯ СТРОКА, 1px)
            for border_row in order_last_rows:
                request = {
                    "updateBorders": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "startRowIndex": border_row - 1,  # -1 для 0-индексации
                            "endRowIndex": border_row
                            # НЕ указываем startColumnIndex и endColumnIndex = граница на ВСЮ строку
                        },
                        "bottom": {
                            "style": "SOLID",
                            "width": 1,
                            "color": {"red": 0, "green": 0, "blue": 0}
                        }
                    }
                }
                requests.append(request)
            
            logger.info(f"📐 Добавлены нижние границы для {len(order_last_rows)} заказов (последние строки)")
            
            # 2. Находим границы групп товаров по mapped_name (для нижней линии 1px)
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
            
            # Добавляем нижние границы между группами товаров (G-I, 1px)
            for border_row in group_borders:
                request = {
                    "updateBorders": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "startRowIndex": border_row - 1,  # -1 для 0-индексации
                            "endRowIndex": border_row,
                            "startColumnIndex": 6,  # G
                            "endColumnIndex": 9      # I (не включительно = до конца столбца I)
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
                logger.info(f"✅ Применены границы: {len(order_borders)} заказов (верх) + {len(order_last_rows)} заказов (низ) + {len(group_borders)} групп товаров")
            
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
                            
                            # Создаем ссылку на заказ
                            order_link = f"https://www.ozon.ru/my/orderdetails?orderId={order_number}"
                            
                            sync_send_message(
                                f"⚠️ <b>Изменения в заказе <a href='{order_link}'>{order_number}</a>:</b>\n{changes_text}\n\n"
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
                    
                    # Добавляем отчет о потерянных значениях колонки I
                    if hasattr(self, '_lost_i_values') and self._lost_i_values:
                        summary_parts.append(f"\n❗ <b>Потеряно значений колонки I:</b> {len(self._lost_i_values)}")
                        for item in self._lost_i_values[:5]:  # Первые 5
                            summary_parts.append(f"  • <code>{item['old_name']}</code>: {item['value']}")
                        if len(self._lost_i_values) > 5:
                            summary_parts.append(f"  • ... ещё {len(self._lost_i_values) - 5}")
                    
                    sync_send_message("✅ " + "\n".join(summary_parts))
            elif updated_orders:
                # Были только обновления, без добавления новых
                summary_msg = f"✅ <b>Обновлено заказов:</b> {len(updated_orders)}"
                
                # Добавляем отчет о потерянных значениях колонки I
                if hasattr(self, '_lost_i_values') and self._lost_i_values:
                    summary_msg += f"\n\n❗ <b>Потеряно значений колонки I:</b> {len(self._lost_i_values)}"
                    for item in self._lost_i_values[:5]:  # Первые 5
                        summary_msg += f"\n  • <code>{item['old_name']}</code>: {item['value']}"
                    if len(self._lost_i_values) > 5:
                        summary_msg += f"\n  • ... ещё {len(self._lost_i_values) - 5}"
                
                sync_send_message(summary_msg)
            
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
