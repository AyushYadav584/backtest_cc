'''
this module is for processing theta data
'''

import os
from typing import Callable
import pandas as pd
import re
import json

from tradelib.data_parsers import DataAdpater
from modules._logger import logger, get_exception_line_no

def convert_to_primary_unit(input:int,conversion_factor:int):
    return input/conversion_factor

def convert_to_int(input):
    return int(input)

def convert_to_float(input):
    return float(input)

def strip_str_columns():
    pass

def change_datatype():
    pass

FIELDS_IN = ['DataType.MS_OF_DAY', 'DataType.BID_SIZE', 'DataType.BID_CONDITION',
       'DataType.BID', 'DataType.BID_EXCHANGE', 'DataType.ASK_SIZE',
       'DataType.ASK_CONDITION', 'DataType.ASK', 'DataType.ASK_EXCHANGE',
       'DataType.DATE', 'DataType.EXPIRY_DATE']

FIELDS_TO_CREATE = []
FIELDS_TO_DROP = ['UnixTimefrom 1-1-1980']
FIELDS_TO_TRANSFORM = [{convert_to_primary_unit:['DataType.MS_OF_DAY']},
                       {convert_to_float:['ExchToken']},
                       {convert_to_float:['BidPrice',
                                          'BidQty',
                                          'AskPrice',
                                          'AskQty',
                                          'TTq',
                                          'LTP',
                                          'TotalTradedPrice',
                                          'Strike']},
                        {}
                       ]
FIELDS_TO_MERGE = [{'data_time':['DataType.DATE','DataType.MS_OF_DAY']}]

FIELDS_OUT = []

preprocess_pipeline = []

from abc import ABC,abstractmethod
from collections.abc import Iterator, Iterable

class PreprocTask(ABC):
    def __init__(self, task_name:str) -> None:
        super().__init__()
        self._task_name = task_name

    @abstractmethod
    def execute(self):
        pass

class DropColumns(PreprocTask):
    def execute(self):

        return 


class PreprocTasks(Iterable):
    def __init__(self) -> None:
        super().__init__()


class PreprocTaskIterator(Iterator):
    def __init__(self, tasks) -> None:
        super().__init__()
        self._tasks = tasks
        self._index = 0

    def __next__(self):
        if self._index < len(self._tasks):
            value = self._tasks[self._index]
            self._index += 1
            return value
        else:
            raise StopIteration

class EISDataAdapter(DataAdpater):

    def __init__(self, file_loader: Callable[[str], pd.DataFrame]) -> None:
        super().__init__(file_loader)

    def process(self, file_path:str):

        try:
            df = self.load_file(file_path)

            # 
            for task in 
            return df

        except Exception as ex:
            logger.critical(f"error while processing file {file_path} at line:{get_exception_line_no()}. ErrorMessage:{ex}")
        return 