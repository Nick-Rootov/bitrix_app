from openpyxl import Workbook
from .base_exporter import BaseExporter



class XLSXExporter(BaseExporter):
    def export(self, data: list[dict[str, str]], file_path: str) -> str:
        if not data:
            raise ValueError("No data to export")

        wb = Workbook()
        ws = wb.active

        # Заголовки
        headers = list(data[0].keys())
        ws.append(headers)

        # Данные
        for row in data:
            ws.append(list(row.values()))

        wb.save(file_path)
        return file_path