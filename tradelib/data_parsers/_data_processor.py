'''
this is the base class for processing files from different sources
'''

from abc import ABC,abstractmethod
import os

from tradelib.data_parsers._data_adapter import DataAdpater


class DataProcessor(ABC):

    def __init__(self, data_directory:str, file_type:str) -> None:
        super().__init__()
        self._data_dir = data_directory
        self._file_type = file_type
        
        if os.path.exists(self._data_dir):
            self._file_list = [os.path.join(self._data_dir,file) for file in os.listdir(self._data_dir) if file.endswith(file_type)]
            if len(self._file_list) == 0:
                raise Exception(f"no {file_type} files found in directory {data_directory}")
        else:
            raise Exception(f"non-existent data directory {self._data_dir}")
 

    # @abstractmethod
    # def _load_data(self, data_directory)

    def set_adapter(self,data_adapter:DataAdpater):
        self._data_adapter = data_adapter

    @abstractmethod
    def process(self):
        pass

