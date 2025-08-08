from .csv_exporter import CSVExporter
from .xlsx_exporter import XLSXExporter


class ExporterFactory:
    @staticmethod
    def get_exporter(format_type: str):
        exporters = {
            'csv': CSVExporter,
            'xlsx': XLSXExporter
        }

        exporter_class = exporters.get(format_type.lower())
        if not exporter_class:
            raise ValueError(f"Unsupported export format: {format_type}")

        return exporter_class()