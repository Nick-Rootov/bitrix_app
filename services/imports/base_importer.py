from abc import ABC, abstractmethod
from typing import List, Dict


class BaseImporter(ABC): #    Абстрактный базовый класс для всех импортеров. Определяет общий интерфейс для всех реализаций импорта

    @abstractmethod
    def import_data(self, file_path: str) -> List[Dict]:

        pass