"""
Модуль для управления исключёнными заказами.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Set, Optional
from loguru import logger


class ExcludedOrdersManager:
    """Менеджер для работы со списком исключённых заказов."""
    
    EXCLUDED_FILE = "excluded_orders.json"
    
    def __init__(self, excluded_file: Optional[str] = None):
        """
        Инициализация.
        
        Args:
            excluded_file: Путь к файлу с исключёнными заказами
        """
        self.excluded_file = excluded_file or self.EXCLUDED_FILE
        self.excluded_orders: Set[str] = self._load_excluded()
    
    def _load_excluded(self) -> Set[str]:
        """Загрузить список исключённых заказов."""
        try:
            if Path(self.excluded_file).exists():
                with open(self.excluded_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    excluded = set(data.get('excluded_orders', []))
                    logger.info(f"📋 Загружено исключённых заказов: {len(excluded)}")
                    return excluded
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить исключённые заказы: {e}")
        
        return set()
    
    def _save_excluded(self) -> bool:
        """Сохранить список исключённых заказов."""
        try:
            data = {
                "excluded_orders": sorted(list(self.excluded_orders)),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "description": "Список исключённых заказов (order_number), которые не будут парситься"
            }
            
            with open(self.excluded_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Список исключённых заказов сохранён: {len(self.excluded_orders)} заказов")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения исключённых заказов: {e}")
            return False
    
    def add_excluded(self, order_number: str) -> bool:
        """
        Добавить заказ в список исключённых.
        
        Args:
            order_number: Номер заказа для исключения
            
        Returns:
            True если успешно добавлен
        """
        if order_number in self.excluded_orders:
            logger.warning(f"⚠️ Заказ {order_number} уже в списке исключённых")
            return False
        
        self.excluded_orders.add(order_number)
        logger.info(f"➕ Добавлен в исключённые: {order_number}")
        
        return self._save_excluded()
    
    def remove_excluded(self, order_number: str) -> bool:
        """
        Удалить заказ из списка исключённых.
        
        Args:
            order_number: Номер заказа для удаления
            
        Returns:
            True если успешно удалён
        """
        if order_number not in self.excluded_orders:
            logger.warning(f"⚠️ Заказ {order_number} не найден в списке исключённых")
            return False
        
        self.excluded_orders.remove(order_number)
        logger.info(f"➖ Удалён из исключённых: {order_number}")
        
        return self._save_excluded()
    
    def is_excluded(self, order_number: str) -> bool:
        """
        Проверить, исключён ли заказ.
        
        Args:
            order_number: Номер заказа
            
        Returns:
            True если заказ исключён
        """
        return order_number in self.excluded_orders
    
    def get_excluded_list(self) -> List[str]:
        """Получить список всех исключённых заказов."""
        return sorted(list(self.excluded_orders))
    
    def get_count(self) -> int:
        """Получить количество исключённых заказов."""
        return len(self.excluded_orders)
    
    def clear_excluded(self) -> bool:
        """
        Очистить весь список исключённых заказов.
        
        Returns:
            True если успешно очищен
        """
        if not self.excluded_orders:
            logger.info("ℹ️ Список исключённых заказов уже пуст")
            return True
        
        count = len(self.excluded_orders)
        self.excluded_orders.clear()
        logger.info(f"🗑️ Очищен список исключённых заказов: было {count} заказов")
        
        return self._save_excluded()
    
    def filter_orders(self, orders_data: list) -> tuple[list, list]:
        """
        Отфильтровать исключённые заказы из списка.
        
        Args:
            orders_data: Список всех заказов
            
        Returns:
            Кортеж (не_исключённые_заказы, исключённые_заказы)
        """
        valid_orders = []
        excluded_orders = []
        
        for order in orders_data:
            order_number = order.get('order_number', '')
            
            if self.is_excluded(order_number):
                excluded_orders.append(order)
                logger.debug(f"⏭️ Пропускаем исключённый заказ: {order_number}")
            else:
                valid_orders.append(order)
        
        if excluded_orders:
            logger.info(f"⏭️ Пропущено исключённых заказов: {len(excluded_orders)}")
        
        return valid_orders, excluded_orders
