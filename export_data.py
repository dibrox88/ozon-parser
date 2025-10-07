"""
Модуль для экспорта спарсенных данных в различные форматы.
"""

import json
from pathlib import Path
from datetime import datetime
from loguru import logger


class DataExporter:
    """Класс для экспорта данных заказов."""
    
    def __init__(self, output_dir: str = "."):
        """
        Инициализация экспортёра.
        
        Args:
            output_dir: Директория для сохранения файлов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_json(self, orders_data: list, filename: str | None = None) -> str:
        """
        Экспорт данных заказов в JSON файл.
        
        Args:
            orders_data: Список заказов с данными
            filename: Имя файла (если None, используется ozon_orders.json)
        
        Returns:
            Путь к сохранённому файлу
        """
        try:
            # Используем единый файл ozon_orders.json по умолчанию
            if filename is None:
                filename = "ozon_orders.json"
            
            # Полный путь к файлу
            filepath = self.output_dir / filename
            
            # Подготавливаем данные для экспорта
            export_data = {
                'export_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_orders': len(orders_data),
                'orders': orders_data
            }
            
            # Добавляем статистику
            total_items = sum(order.get('items_count', 0) for order in orders_data)
            total_amount = sum(order.get('total_amount', 0) for order in orders_data)
            
            export_data['statistics'] = {
                'total_items': total_items,
                'total_amount': total_amount,
                'total_positions': sum(len(order.get('items', [])) for order in orders_data)
            }
            
            # Сохраняем в JSON с красивым форматированием
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Данные экспортированы в JSON: {filepath}")
            logger.info(f"📊 Статистика: {len(orders_data)} заказов, {total_items} товаров, {total_amount:.2f} ₽")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при экспорте в JSON: {e}")
            raise
    
    def export_summary(self, orders_data: list) -> dict:
        """
        Создаёт сводку по заказам.
        
        Args:
            orders_data: Список заказов с данными
        
        Returns:
            Словарь со статистикой
        """
        if not orders_data:
            return {}
        
        # Группировка по статусам
        status_stats = {}
        for order in orders_data:
            for item in order.get('items', []):
                status = item.get('status', 'неизвестно')
                if status not in status_stats:
                    status_stats[status] = {
                        'count': 0,
                        'quantity': 0,
                        'total_amount': 0
                    }
                status_stats[status]['count'] += 1
                status_stats[status]['quantity'] += item.get('quantity', 0)
                status_stats[status]['total_amount'] += item.get('price', 0) * item.get('quantity', 0)
        
        # Общая статистика
        summary = {
            'total_orders': len(orders_data),
            'total_items': sum(order.get('items_count', 0) for order in orders_data),
            'total_positions': sum(len(order.get('items', [])) for order in orders_data),
            'total_amount': sum(order.get('total_amount', 0) for order in orders_data),
            'status_breakdown': status_stats,
            'date_range': {
                'from': min((order.get('date', '') for order in orders_data), default=''),
                'to': max((order.get('date', '') for order in orders_data), default='')
            }
        }
        
        return summary


def export_orders(orders_data: list, output_dir: str = ".") -> str:
    """
    Быстрая функция для экспорта заказов в JSON.
    
    Args:
        orders_data: Список заказов
        output_dir: Директория для сохранения
    
    Returns:
        Путь к сохранённому файлу
    """
    exporter = DataExporter(output_dir)
    return exporter.export_to_json(orders_data)


if __name__ == "__main__":
    # Пример использования
    test_data = [
        {
            'order_number': '12345-0001',
            'date': '01.10.2025',
            'total_amount': 1500.0,
            'items_count': 3,
            'items': [
                {'name': 'Товар 1', 'quantity': 2, 'price': 500.0, 'status': 'получен'},
                {'name': 'Товар 2', 'quantity': 1, 'price': 500.0, 'status': 'получен'}
            ]
        }
    ]
    
    exporter = DataExporter()
    filepath = exporter.export_to_json(test_data, 'test_orders.json')
    print(f"Файл сохранён: {filepath}")
    
    summary = exporter.export_summary(test_data)
    print(f"Статистика: {summary}")
