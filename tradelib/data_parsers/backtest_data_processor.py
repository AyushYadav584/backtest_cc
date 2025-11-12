'''
this module is responsible for processing backtest data
'''

from modules._logger import logger,get_exception_line_no
from tradelib.data_parsers._data_processor import DataProcessor
# from tradelib.data_parsers import DataAdpater

class BacktestDataProcessor(DataProcessor):

    def __init__(self, data_directory:str, file_type:str, config_file_name:str) -> None:
        super().__init__(data_directory=data_directory,file_type=file_type)
        self._config_file_name = config_file_name

    def load_target_column_list(self,str):
        pass

    def process(self):
        try:
            for file in self._file_list:
                df= self._data_adapter.process(file)

        except Exception as ex:
            print(f"exception within {__name__} at line:{get_exception_line_no()}")