import csv
from .base_exporter import BaseExporter


class CSVExporter(BaseExporter):
    def export(self, data: list[dict[str, str]], file_path: str) -> str:
        if not data:
            raise ValueError("No data to export")

        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(data)

        return file_path