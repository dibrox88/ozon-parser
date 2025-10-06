""""""

Модуль для работы с Google Sheets.Модуль для работы с Google Sheets.

Загружает товары из таблицы и предоставляет их для сопоставления.Загружает товары из таблицы и предоставляет их для сопоставления.

""""""



import gspreadimport gspread

from google.oauth2.service_account import Credentialsfrom google.oauth2.service_account import Credentials

from loguru import loggerfrom loguru import logger

from typing import List, Dict, Tuple, Optionalfrom typing import List, Dict, Tuple, Optional

import reimport re





class SheetsManager:class SheetsManager:

    """Менеджер для работы с Google Sheets."""    """Менеджер для работы с Google Sheets."""

        

    SCOPES = [    SCOPES = [

        'https://www.googleapis.com/auth/spreadsheets.readonly',        'https://www.googleapis.com/auth/spreadsheets.readonly',

        'https://www.googleapis.com/auth/drive.readonly'        'https://www.googleapis.com/auth/drive.readonly'

    ]    ]

        

    def __init__(self, credentials_file: str):    def __init__(self, credentials_file: str):

        """        """

        Инициализация менеджера.        Инициализация менеджера.

                

        Args:        Args:

            credentials_file: Путь к JSON файлу с credentials от Google            credentials_file: Путь к JSON файлу с credentials от Google

        """        """

        self.credentials_file = credentials_file        self.credentials_file = credentials_file

        self.client = None        self.client = None

        self.products_cache = []        self.products_cache = []

                

    def connect(self) -> bool:    def connect(self) -> bool:

        """        """

        Подключение к Google Sheets API.        Подключение к Google Sheets API.

                

        Returns:        Returns:

            True если подключение успешно            True если подключение успешно

        """        """

        try:        try:

            logger.info("Подключение к Google Sheets API...")            logger.info("Подключение к Google Sheets API...")

            creds = Credentials.from_service_account_file(            creds = Credentials.from_service_account_file(

                self.credentials_file,                self.credentials_file,

                scopes=self.SCOPES                scopes=self.SCOPES

            )            )

            self.client = gspread.authorize(creds)            self.client = gspread.authorize(creds)

            logger.info("✅ Успешно подключились к Google Sheets API")            logger.info("✅ Успешно подключились к Google Sheets API")

            return True            return True

        except Exception as e:        except Exception as e:

            logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")            logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")

            return False            return False

        

    def load_products_from_sheet(    def load_products_from_sheet(

        self,         self, 

        spreadsheet_url: str,        spreadsheet_url: str,

        sheet_name: Optional[str] = None,        sheet_name: Optional[str] = None,

        columns_range: str = "A:AU"        columns_range: str = "A:AU"

    ) -> List[Dict[str, str]]:    ) -> List[Dict[str, str]]:

        """        """

        Загрузка товаров из Google Sheets.        Загрузка товаров из Google Sheets.

                

        Структура: каждые 3 столбца содержат [цена, наименование, тип]        Структура: каждые 3 столбца содержат [цена, наименование, тип]

                

        Args:        Args:

            spreadsheet_url: URL таблицы (может содержать gid для выбора листа)            spreadsheet_url: URL таблицы

            sheet_name: Название листа (если None, используется gid из URL или первый лист)            sheet_name: Название листа (если None, берётся первый)

            columns_range: Диапазон столбцов для чтения            columns_range: Диапазон столбцов для чтения

                        

        Returns:        Returns:

            Список уникальных товаров [{name, type}, ...]            Список уникальных товаров [{name, type}, ...]

        """        """

        try:        try:

            logger.info(f"Загрузка товаров из таблицы: {spreadsheet_url}")            logger.info(f"Загрузка товаров из таблицы: {spreadsheet_url}")

                        # Открываем таблицу

            # Открываем таблицу            spreadsheet = self.client.open_by_url(spreadsheet_url)

            spreadsheet = self.client.open_by_url(spreadsheet_url)            # Выбираем лист

                        worksheet = None

            # Выбираем лист            if sheet_name:

            worksheet = None                worksheet = spreadsheet.worksheet(sheet_name)

            if sheet_name:            else:

                # Явно указано имя листа                gid_match = re.search(r'[?&]gid=(\d+)', spreadsheet_url)

                worksheet = spreadsheet.worksheet(sheet_name)                gid = gid_match.group(1) if gid_match else None

                logger.info(f"📄 Открыт лист по имени: {worksheet.title} (id={worksheet.id})")                if gid:

            else:                    for ws in spreadsheet.worksheets():

                # Пытаемся получить gid из URL                        if str(ws.id) == str(gid):

                gid_match = re.search(r'[?&]gid=(\d+)', spreadsheet_url)                            worksheet = ws

                gid = gid_match.group(1) if gid_match else None                            break

                                if worksheet is None:

                if gid:                    worksheet = spreadsheet.get_worksheet(0)

                    logger.info(f"🔍 Ищем лист с gid={gid}")            logger.info(f"📄 Открыт лист: {worksheet.title} (id={worksheet.id})")

                    # Найти лист с нужным gid            

                    for ws in spreadsheet.worksheets():            # Получаем все данные из диапазона

                        if str(ws.id) == str(gid):            all_values = worksheet.get(columns_range)

                            worksheet = ws            

                            logger.info(f"✅ Найден лист с gid={gid}: {ws.title}")            if not all_values:

                            break                logger.warning("⚠️ Таблица пустая")

                                    try:

                    if worksheet is None:                    logger.info(f"Загрузка товаров из таблицы: {spreadsheet_url}")

                        logger.warning(f"⚠️ Лист с gid={gid} не найден, используем первый лист")                    # Открываем таблицу

                                    spreadsheet = self.client.open_by_url(spreadsheet_url)

                # Если не нашли по gid или gid не указан, берём первый лист                    worksheet = None

                if worksheet is None:                    if sheet_name:

                    worksheet = spreadsheet.get_worksheet(0)                        worksheet = spreadsheet.worksheet(sheet_name)

                    logger.info(f"📄 Открыт первый лист: {worksheet.title} (id={worksheet.id})")                    else:

                                    gid_match = re.search(r'[?&]gid=(\d+)', spreadsheet_url)

            # Получаем все данные из диапазона                        gid = gid_match.group(1) if gid_match else None

            all_values = worksheet.get(columns_range)                        if gid:

                                        for ws in spreadsheet.worksheets():

            if not all_values:                                if str(ws.id) == str(gid):

                logger.warning("⚠️ Таблица пустая")                                    worksheet = ws

                return []                                    break

                                    if worksheet is None:

            # Парсим данные: каждые 3 столбца = [цена, наименование, тип]                            worksheet = spreadsheet.get_worksheet(0)

            products = []                    logger.info(f"📄 Открыт лист: {worksheet.title} (id={worksheet.id})")

            unique_products = set()  # Для отслеживания уникальных (name, type)                        continue

                                

            # Проходим по каждой строке                    # Создаём уникальный ключ

            for row_idx, row in enumerate(all_values, start=1):                    unique_key = (name.lower(), product_type.lower())

                # Обрабатываем каждую тройку столбцов                    

                for col_idx in range(0, len(row), 3):                    if unique_key not in unique_products:

                    if col_idx + 2 >= len(row):                        unique_products.add(unique_key)

                        break  # Недостаточно столбцов для полной тройки                        products.append({

                                                'name': name,

                    price = row[col_idx].strip() if col_idx < len(row) else ""                            'type': product_type,

                    name = row[col_idx + 1].strip() if col_idx + 1 < len(row) else ""                            'price': price  # Для справки

                    product_type = row[col_idx + 2].strip() if col_idx + 2 < len(row) else ""                        })

                                            logger.debug(f"Добавлен товар: {name} ({product_type})")

                    # Пропускаем пустые или заголовочные строки            

                    if not name or name.lower() in ['наименование', 'название', 'товар']:            logger.info(f"✅ Загружено уникальных товаров: {len(products)}")

                        continue            self.products_cache = products

                                return products

                    # Пропускаем если тип пустой            

                    if not product_type or product_type.lower() in ['тип', 'категория']:        except Exception as e:

                        continue            logger.error(f"❌ Ошибка загрузки данных из Google Sheets: {e}")

                                return []

                    # Создаём уникальный ключ    

                    unique_key = (name.lower(), product_type.lower())    def get_products(self) -> List[Dict[str, str]]:

                            """Получить кешированный список товаров."""

                    if unique_key not in unique_products:        return self.products_cache

                        unique_products.add(unique_key)    

                        products.append({    def find_similar_product(self, search_name: str) -> List[Dict[str, str]]:

                            'name': name,        """

                            'type': product_type,        Найти похожие товары по названию.

                            'price': price  # Для справки        

                        })        Args:

                        logger.debug(f"Добавлен товар: {name} ({product_type})")            search_name: Название товара для поиска

                        

            logger.info(f"✅ Загружено уникальных товаров: {len(products)}")        Returns:

            self.products_cache = products            Список похожих товаров

            return products        """

                    if not self.products_cache:

        except Exception as e:            return []

            logger.error(f"❌ Ошибка загрузки данных из Google Sheets: {e}")        

            return []        search_lower = search_name.lower()

            similar = []

    def get_products(self) -> List[Dict[str, str]]:        

        """Получить кешированный список товаров."""        for product in self.products_cache:

        return self.products_cache            product_name_lower = product['name'].lower()

                

    def find_similar_product(self, search_name: str) -> List[Dict[str, str]]:            # Точное совпадение

        """            if product_name_lower == search_lower:

        Найти похожие товары по названию.                similar.insert(0, {**product, 'match_score': 100})

                        continue

        Args:            

            search_name: Название товара для поиска            # Содержит полное название

                        if search_lower in product_name_lower or product_name_lower in search_lower:

        Returns:                similar.append({**product, 'match_score': 80})

            Список похожих товаров с оценкой совпадения                continue

        """            

        if not self.products_cache:            # Проверка по ключевым словам

            return []            search_words = set(re.findall(r'\w+', search_lower))

                    product_words = set(re.findall(r'\w+', product_name_lower))

        search_lower = search_name.lower()            

        similar = []            if search_words and product_words:

                        common_words = search_words & product_words

        for product in self.products_cache:                if common_words:

            product_name_lower = product['name'].lower()                    score = int((len(common_words) / max(len(search_words), len(product_words))) * 70)

                                if score >= 30:  # Минимальный порог похожести

            # Точное совпадение            worksheet = None

            if product_name_lower == search_lower:            if sheet_name:

                similar.insert(0, {**product, 'match_score': 100})                worksheet = spreadsheet.worksheet(sheet_name)

                continue            else:

                            # Попробуем получить gid из URL

            # Содержит полное название                import re

            if search_lower in product_name_lower or product_name_lower in search_lower:                gid_match = re.search(r'[?&]gid=(\d+)', spreadsheet_url)

                similar.append({**product, 'match_score': 80})                gid = gid_match.group(1) if gid_match else None

                continue                if gid:

                                # Найти лист с нужным gid

            # Проверка по ключевым словам                    for ws in spreadsheet.worksheets():

            search_words = set(re.findall(r'\w+', search_lower))                        if str(ws.id) == str(gid):

            product_words = set(re.findall(r'\w+', product_name_lower))                            worksheet = ws

                                        break

            if search_words and product_words:                if worksheet is None:

                common_words = search_words & product_words                    worksheet = spreadsheet.get_worksheet(0)

                if common_words:        

                    score = int((len(common_words) / max(len(search_words), len(product_words))) * 70)        return similar[:5]  # Топ-5 похожих

                    if score >= 30:  # Минимальный порог похожести
                        similar.append({**product, 'match_score': score})
        
        # Сортируем по score
        similar.sort(key=lambda x: x['match_score'], reverse=True)
        
        return similar[:5]  # Топ-5 похожих
