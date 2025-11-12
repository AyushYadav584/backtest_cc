'''
this module is the base class for all the data adapters
'''

from abc import ABC,abstractmethod
from typing import Callable
import os
import pandas as pd
import json


def csv_loader(file_path:str) -> pd.DataFrame:
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        raise Exception(f"non-existent file path: {file_path}")

def json_loader(file_path:str) -> pd.DataFrame:
    if os.path.exists(file_path):
        return pd.read_json(file_path)
    else:
        raise Exception(f"non-existent file path: {file_path}")

class DataAdpater(ABC):

    def __init__(self, file_loader:Callable[[str], pd.DataFrame]) -> None:
        super().__init__()
        self._file_loader = file_loader
        # self._field_map_file = field_map_file

    def load_file(self, file_name_with_path:str):
        return self._file_loader(file_name_with_path)

    # def read_field_map(self):

    #     pass

    @abstractmethod
    def process(self, file_name_with_path:str):
        pass