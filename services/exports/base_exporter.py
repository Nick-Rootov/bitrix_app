from abc import ABC, abstractmethod


class BaseExporter(ABC):
    @abstractmethod
    def export(self, data: list[dict[str, str]], file_path: str) -> str: #Экспортирует данные в файл и возвращает путь к файлу
        pass