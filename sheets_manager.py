"""
Модуль для работы с Google Sheets.
Загружает товары из таблицы и предоставляет их для сопоставления.
"""

import gspread
from google.oauth2.service_account import Credentials
from loguru import logger
from typing import List, Dict, Optional
import re


class SheetsManager:
    """Менеджер для работы с Google Sheets."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    def __init__(self, credentials_file: str):
        """
        Инициализация менеджера.
        
        Args:
            credentials_file: Путь к JSON файлу с credentials от Google
        """
        self.credentials_file = credentials_file
        self.client: Optional[gspread.Client] = None
        self.products_cache: List[Dict[str, str]] = []
        
    def connect(self) -> bool:
        """
        Подключение к Google Sheets API.
        
        Returns:
            True если подключение успешно
        """
        try:
            logger.info("Подключение к Google Sheets API...")
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(creds)
            logger.info("✅ Успешно подключились к Google Sheets API")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")
            return False
    
    def load_products_from_sheet(
        self, 
        spreadsheet_url: str,
        sheet_name: str = "Настройки",
        columns_range: str = "A:AU"
    ) -> List[Dict[str, str]]:
        """
        Загрузка товаров из Google Sheets.
        
        Структура: каждые 4 столбца содержат [цена, наименование, тип, номер заказа]
        
        Args:
            spreadsheet_url: URL таблицы
            sheet_name: Название листа (по умолчанию "Настройки")
            columns_range: Диапазон столбцов для чтения
            
        Returns:
            Список уникальных товаров [{name, type, price}, ...]
        """
        try:
            logger.info(f"Загрузка товаров из таблицы: {spreadsheet_url}")
            
            # Проверяем, что клиент инициализирован
            if self.client is None:
                raise RuntimeError("Google Sheets client не инициализирован. Вызовите connect() сначала.")
            
            # Открываем таблицу
            spreadsheet = self.client.open_by_url(spreadsheet_url)
            
            # Открываем лист "Настройки"
            worksheet = spreadsheet.worksheet(sheet_name)
            logger.info(f"📄 Открыт лист: {worksheet.title}")
            
            # Получаем все данные из диапазона
            all_values = worksheet.get(columns_range)
            
            if not all_values:
                logger.warning("⚠️ Таблица пустая")
                return []
            
            # Парсим данные: каждые 4 столбца = [цена, наименование, тип, номер заказа]
            products = []
            unique_products = set()  # Для отслеживания уникальных (name, type)
            
            # Проходим по каждой строке
            for row_idx, row in enumerate(all_values, start=1):
                # Обрабатываем каждую четвёрку столбцов
                for col_idx in range(0, len(row), 4):
                    if col_idx + 2 >= len(row):
                        break  # Недостаточно столбцов для полной четвёрки (минимум нужны price, name, type)
                    
                    price = row[col_idx].strip() if col_idx < len(row) else ""
                    name = row[col_idx + 1].strip() if col_idx + 1 < len(row) else ""
                    product_type = row[col_idx + 2].strip() if col_idx + 2 < len(row) else ""
                    # Четвёртый столбец (номер заказа) игнорируем
                    # order_number = row[col_idx + 3].strip() if col_idx + 3 < len(row) else ""
                    
                    # Пропускаем пустые или заголовочные строки
                    if not name or name.lower() in ['наименование', 'название', 'товар']:
                        continue
                    
                    # Пропускаем если тип пустой
                    if not product_type or product_type.lower() in ['тип', 'категория']:
                        continue
                    
                    # Создаём уникальный ключ
                    unique_key = (name.lower(), product_type.lower())
                    
                    if unique_key not in unique_products:
                        unique_products.add(unique_key)
                        products.append({
                            'name': name,
                            'type': product_type,
                            'price': price  # Для справки
                        })
                        logger.debug(f"Добавлен товар: {name} ({product_type})")
            
            logger.info(f"✅ Загружено уникальных товаров: {len(products)}")
            self.products_cache = products
            return products
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки данных из Google Sheets: {e}")
            return []
    
    def get_products(self) -> List[Dict[str, str]]:
        """Получить кешированный список товаров."""
        return self.products_cache
    
    def find_similar_product(self, search_name: str) -> List[Dict[str, str]]:
        """
        Найти похожие товары по названию.
        
        Args:
            search_name: Название товара для поиска
            
        Returns:
            Список похожих товаров
        """
        if not self.products_cache:
            return []
        
        search_lower = search_name.lower()
        similar = []
        
        for product in self.products_cache:
            product_name_lower = product['name'].lower()
            
            # Точное совпадение
            if product_name_lower == search_lower:
                similar.insert(0, {**product, 'match_score': 100})
                continue
            
            # Содержит полное название
            if search_lower in product_name_lower or product_name_lower in search_lower:
                similar.append({**product, 'match_score': 80})
                continue
            
            # Проверка по ключевым словам
            search_words = set(re.findall(r'\w+', search_lower))
            product_words = set(re.findall(r'\w+', product_name_lower))
            
            if search_words and product_words:
                common_words = search_words & product_words
                if common_words:
                    score = int((len(common_words) / max(len(search_words), len(product_words))) * 70)
                    if score >= 30:  # Минимальный порог похожести
                        similar.append({**product, 'match_score': score})
        
        # Сортируем по score
        similar.sort(key=lambda x: x['match_score'], reverse=True)
        
        return similar[:5]  # Топ-5 похожих