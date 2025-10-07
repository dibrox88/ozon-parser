"""
Модуль для синхронизации заказов с Google Sheets.
MVP версия: базовая запись новых заказов.
"""

import gspread
from google.oauth2.service_account import Credentials
from loguru import logger
from typing import List, Dict, Optional
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
    
    def __init__(self, credentials_file: str):
        """
        Инициализация синхронизатора.
        
        Args:
            credentials_file: Путь к JSON файлу с credentials от Google
        """
        self.credentials_file = credentials_file
        self.client: Optional[gspread.Client] = None
        self.spreadsheet = None
        self.worksheet = None
        
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
            
            # Фильтруем пустые и заголовки
            existing_orders = [
                order_num for order_num in column_b 
                if order_num and order_num not in ['order_number', 'Номер заказа', '']
            ]
            
            logger.info(f"📋 Найдено существующих заказов в таблице: {len(existing_orders)}")
            return existing_orders
            
        except Exception as e:
            logger.error(f"❌ Ошибка чтения существующих заказов: {e}")
            return []
    
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
                    ""                                         # I: пустой (резерв)
                ]
                rows.append(row)
        
        logger.debug(f"Подготовлено {len(rows)} строк для заказа {order_number}")
        return rows
    
    def sync_orders(self, orders_data: List[Dict]) -> bool:
        """
        Синхронизировать заказы с Google Sheets (MVP версия).
        
        Args:
            orders_data: Список заказов из ozon_orders.json
            
        Returns:
            True если успешно
        """
        try:
            logger.info("🔄 Начинаем синхронизацию заказов с Google Sheets...")
            sync_send_message("🔄 <b>Синхронизация с Google Sheets...</b>")
            
            # Получаем существующие заказы
            existing_orders = self.get_existing_orders()
            
            # Фильтруем новые заказы
            new_orders = [
                order for order in orders_data['orders']
                if order.get('order_number') not in existing_orders
            ]
            
            if not new_orders:
                logger.info("✅ Нет новых заказов для добавления")
                sync_send_message("✅ Нет новых заказов для добавления")
                return True
            
            logger.info(f"📦 Найдено новых заказов: {len(new_orders)}")
            sync_send_message(f"📦 <b>Новых заказов:</b> {len(new_orders)}")
            
            # Подготавливаем все строки
            all_rows = []
            for order in new_orders:
                rows = self.prepare_rows_from_order(order)
                all_rows.extend(rows)
            
            logger.info(f"📝 Всего строк для добавления: {len(all_rows)}")
            
            # Находим последнюю непустую строку в столбце A
            column_a = self.worksheet.col_values(1)
            last_row = len([cell for cell in column_a if cell.strip()]) + 1
            
            logger.info(f"📍 Начало записи с строки: {last_row}")
            
            # Записываем данные
            if all_rows:
                start_cell = f"A{last_row}"
                self.worksheet.update(start_cell, all_rows, value_input_option='USER_ENTERED')
                
                logger.info(f"✅ Записано {len(all_rows)} строк в таблицу")
                sync_send_message(f"✅ <b>Записано строк:</b> {len(all_rows)}\n<b>Новых заказов:</b> {len(new_orders)}")
            
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
