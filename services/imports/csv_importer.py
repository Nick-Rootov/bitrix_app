import csv
from typing import List, Dict
from .base_importer import BaseImporter


class CSVImporter(BaseImporter):
    # Реализация импорта данных из CSV файла
    def import_data(self, file_path: str) -> List[Dict]:

        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                data = [row for row in reader]

                if not data:
                    raise ValueError("CSV файл не содержит данных")

                result = []

                # Получаем заголовки из первого элемента (удаляем \ufeff если есть)
                headers = data[0].keys()
                header_str = next(iter(headers)).lstrip('\ufeff')  # Получаем строку заголовков

                # Разделяем заголовки
                fieldnames = [field.strip() for field in header_str.split(';')]

                for item in data:
                    # Получаем строку значений (берем первое значение из словаря)
                    values_str = next(iter(item.values()))
                    values = [v.strip() for v in values_str.split(';')]

                    # Создаем словарь для текущей записи
                    record = {}
                    for field, value in zip(fieldnames, values):
                        record[field] = value

                    result.append(record)

                return result

        except csv.Error as e:
            raise IOError(f"Ошибка чтения CSV файла: {str(e)}")