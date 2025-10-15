"""
Модуль для управления связками товаров (bundles).
Позволяет разбивать комплектные товары на отдельные комплектующие.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger


class BundleManager:
    """Менеджер для управления связками товаров."""
    
    def __init__(self, bundles_file: str = "product_bundles.json"):
        """
        Инициализация менеджера.
        
        Args:
            bundles_file: Путь к файлу со связками
        """
        self.bundles_file = bundles_file
        self.bundles: Dict[str, Any] = self._load_bundles()
    
    def _load_bundles(self) -> Dict[str, Any]:
        """
        Загрузить связки из файла.
        
        Returns:
            Словарь со связками
        """
        if not os.path.exists(self.bundles_file):
            logger.info(f"📦 Файл {self.bundles_file} не найден, создаём новый")
            return {"bundles": {}}
        
        try:
            with open(self.bundles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"📦 Загружено связок: {len(data.get('bundles', {}))}")
                return data
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {self.bundles_file}: {e}")
            return {"bundles": {}}
    
    def _save_bundles(self) -> bool:
        """
        Сохранить связки в файл.
        
        Returns:
            True если успешно
        """
        try:
            with open(self.bundles_file, 'w', encoding='utf-8') as f:
                json.dump(self.bundles, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Связки сохранены в {self.bundles_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения {self.bundles_file}: {e}")
            return False
    
    def has_bundle(self, product_name: str) -> bool:
        """
        Проверить, существует ли связка для товара.
        
        Args:
            product_name: Название товара
            
        Returns:
            True если связка существует
        """
        return product_name in self.bundles.get("bundles", {})
    
    def get_bundle(self, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Получить связку для товара.
        
        Args:
            product_name: Название товара
            
        Returns:
            Словарь со связкой или None
        """
        bundle = self.bundles.get("bundles", {}).get(product_name)
        if bundle:
            # Обновляем last_used
            bundle["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_bundles()
            logger.info(f"📦 Найдена связка для '{product_name[:50]}...'")
        return bundle
    
    def create_bundle(
        self, 
        product_name: str, 
        components: List[Dict[str, Any]], 
        total_price: float
    ) -> bool:
        """
        Создать новую связку.
        
        Args:
            product_name: Название исходного товара
            components: Список компонентов
            total_price: Общая цена товара
            
        Returns:
            True если успешно
        """
        # Проверяем сумму
        components_total = sum(c.get("price", 0) for c in components)
        if abs(components_total - total_price) > 0.01:  # Допустимая погрешность
            logger.error(f"❌ Сумма компонентов ({components_total}) != общая цена ({total_price})")
            return False
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        bundle = {
            "original_name": product_name,
            "components": components,
            "total_price": total_price,
            "components_count": len(components),
            "created_at": now,
            "last_used": now
        }
        
        if "bundles" not in self.bundles:
            self.bundles["bundles"] = {}
        
        self.bundles["bundles"][product_name] = bundle
        
        if self._save_bundles():
            logger.info(f"✅ Создана связка для '{product_name[:50]}...' ({len(components)} компонентов)")
            return True
        
        return False
    
    def delete_bundle(self, product_name: str) -> bool:
        """
        Удалить связку.
        
        Args:
            product_name: Название товара
            
        Returns:
            True если успешно
        """
        if product_name in self.bundles.get("bundles", {}):
            del self.bundles["bundles"][product_name]
            self._save_bundles()
            logger.info(f"🗑️ Удалена связка для '{product_name[:50]}...'")
            return True
        
        logger.warning(f"⚠️ Связка для '{product_name[:50]}...' не найдена")
        return False
    
    def get_all_bundles(self) -> Dict[str, Any]:
        """
        Получить все связки.
        
        Returns:
            Словарь всех связок
        """
        return self.bundles.get("bundles", {})
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику по связкам.
        
        Returns:
            Словарь со статистикой
        """
        bundles = self.bundles.get("bundles", {})
        total_components = sum(
            bundle.get("components_count", 0) 
            for bundle in bundles.values()
        )
        
        return {
            "total_bundles": len(bundles),
            "total_components": total_components,
            "avg_components": total_components / len(bundles) if bundles else 0
        }


def create_bundle_item(
    original_item: Dict[str, Any],
    components: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Создать item с меткой bundle на основе оригинального item.
    
    Args:
        original_item: Оригинальный item из заказа
        components: Список компонентов связки
        
    Returns:
        Item с добавленными полями bundle
    """
    bundle_item = original_item.copy()
    bundle_item["is_bundle"] = True
    bundle_item["bundle_key"] = original_item["name"]
    bundle_item["components"] = components
    
    # Добавляем статус в каждый компонент
    for component in bundle_item["components"]:
        if "status" not in component:
            component["status"] = original_item.get("status", "")
    
    logger.debug(f"📦 Создан bundle item: {len(components)} компонентов")
    return bundle_item
