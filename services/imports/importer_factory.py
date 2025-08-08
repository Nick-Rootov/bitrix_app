from .csv_importer import CSVImporter
from .xlsx_importer import XLSXImporter


class ImporterFactory:  # Фабрика для создания экземпляров импортеров.
    @staticmethod
    def get_importer(file_extension: str):

        print('file',file_extension)
        importers = {
            'csv': CSVImporter,
            'xlsx': XLSXImporter
        }

        extension = file_extension.lower().lstrip('.')
        importer_class = importers.get(extension)

        if not importer_class:
            supported = ", ".join(importers.keys())
            raise ValueError(
                f"Неподдерживаемый формат импорта: '{extension}'. "
                f"Доступные форматы: {supported}"
            )

        return importer_class()