import csv
import json
import datetime
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from sheets_sync import SheetsSynchronizer
from config import Config
from notifier import sync_send_message

class WBSheetsSynchronizer(SheetsSynchronizer):
    """
    Синхронизатор для Wildberries.
    Переопределяет логику подготовки строк.
    """
    def prepare_rows_from_order(self, order: Dict) -> List[List]:
        rows = []
        month_year = order.get('order_number', '')
        
        for item in order.get('items', []):
            date = item.get('date', '')
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)
            status = item.get('status', 'Получен')
            mapped_name = item.get('mapped_name', '')
            mapped_type = item.get('mapped_type', '')
            split_units = item.get('split_units', 1)
            
            actual_rows = quantity * split_units
            unit_price = round(price / split_units, 2) if split_units > 1 else price
            
            for _ in range(actual_rows):
                row = [
                    date,           # A: Date
                    month_year,     # B: MonthYear
                    "WB",           # C: Source
                    status,         # D: Status
                    "",             # E: Formula
                    unit_price,     # F: Price
                    mapped_name,    # G: Mapped Name
                    mapped_type,    # H: Mapped Type
                    "",             # I: Reserved
                    "", "", "", "", "", # J-N
                    "",             # O
                    ""              # P
                ]
                rows.append(row)
        
        return rows

def get_mapping_info(original_name: str, mappings: Dict) -> Dict:
    """Find mapping info for original name."""
    normalized_name = " ".join(original_name.lower().split())
    variants = ['black', 'white', '0', '']
    
    for color in variants:
        if color:
            key = f"{normalized_name}|{color}"
        else:
            key = normalized_name
            
        if key in mappings:
            return mappings[key]
            
    return {}

def sync_wb_to_sheets(csv_path: str = 'wb_products.csv', mappings_path: str = 'product_mappings.json') -> bool:
    """
    Main function to sync WB CSV to Sheets.
    """
    try:
        logger.info("🚀 Запуск синхронизации WB...")
        sync_send_message("🚀 <b>Запуск синхронизации WB...</b>")

        # Load mappings
        try:
            with open(mappings_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load mappings: {e}")
            mappings = {}

        # Load CSV
        products = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    products.append(row)
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            sync_send_message(f"❌ Ошибка чтения CSV: {e}")
            return False

        if not products:
            logger.warning("No products in CSV")
            sync_send_message("⚠️ CSV файл пуст")
            return True

        # Group by MonthYear
        orders_map = {}
        months_ru = {
            1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель', 5: 'май', 6: 'июнь',
            7: 'июль', 8: 'август', 9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'
        }

        for row in products:
            date_str = row.get('Дата', '')
            price_str = row.get('Цена', '0')
            original_name = row.get('Наименование', '')
            std_name = row.get('Стандартизированное наименование', '')
            
            # Parse price
            try:
                # Remove spaces and currency symbol, replace comma with dot
                clean_price = re.sub(r'[^\d.,]', '', price_str)
                clean_price = clean_price.replace(',', '.')
                price = float(clean_price) if clean_price else 0.0
            except:
                price = 0.0
            
            # Parse date
            try:
                day, month, year = map(int, date_str.split('.'))
                month_name = months_ru.get(month, 'январь')
                year_short = str(year)[2:]
                month_year = f"{month_name}{year_short}"
            except:
                month_year = "unknown"
            
            # Get mapping info
            mapping_info = get_mapping_info(original_name, mappings)
            mapped_type = mapping_info.get('mapped_type', '')
            split_units = mapping_info.get('split_units', 1)
            
            # If std_name is empty in CSV, try to get from mapping
            if not std_name:
                std_name = mapping_info.get('mapped_name', original_name)

            item = {
                'name': original_name,
                'mapped_name': std_name,
                'mapped_type': mapped_type,
                'price': price,
                'quantity': 1,
                'status': 'Получен',
                'date': date_str,
                'split_units': split_units
            }
            
            if month_year not in orders_map:
                orders_map[month_year] = {
                    'order_number': month_year,
                    'date': date_str, 
                    'items': []
                }
            
            orders_map[month_year]['items'].append(item)

        # Convert to list
        orders_list = list(orders_map.values())
        orders_data = {'orders': orders_list, 'total_orders': len(orders_list)}
        
        logger.info(f"📊 Сформировано {len(orders_list)} групп заказов (по месяцам)")
        
        # Sync
        sync = WBSheetsSynchronizer(Config.GOOGLE_CREDENTIALS_FILE)
        if not sync.connect():
            sync_send_message("❌ Ошибка подключения к Google Sheets")
            return False
            
        if not sync.open_sync_worksheet(Config.GOOGLE_SHEETS_URL, Config.GOOGLE_SHEETS_SYNC_GID):
            sync_send_message("❌ Ошибка открытия таблицы")
            return False
            
        return sync.sync_orders(orders_data)

    except Exception as e:
        logger.error(f"WB Sync Error: {e}")
        sync_send_message(f"❌ Критическая ошибка WB Sync: {e}")
        return False

if __name__ == "__main__":
    sync_wb_to_sheets()
