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

def convert_to_float(input):
    return float(input)


FIELDS_IN = ['DataType.MS_OF_DAY', 'DataType.BID_SIZE', 'DataType.BID_CONDITION',
       'DataType.BID', 'DataType.BID_EXCHANGE', 'DataType.ASK_SIZE',
       'DataType.ASK_CONDITION', 'DataType.ASK', 'DataType.ASK_EXCHANGE',
       'DataType.DATE', 'DataType.EXPIRY_DATE']

FIELDS_TO_CREATE = []
FIELDS_TO_DROP = ['DataType.BID_CONDITION',
                  'DataType.ASK_CONDITION',
                  'DataType.BID_EXCHANGE',
                  'DataType.ASK_EXCHANGE',
                  ]
FIELDS_TO_TRANSFORM = [{'DataType.MS_OF_DAY':convert_to_primary_unit}]
FIELDS_TO_MERGE = [{'data_time':['DataType.DATE','DataType.MS_OF_DAY']}]

FIELDS_OUT = []



class ThetaDataAdapter(DataAdpater):

    def __init__(self, file_loader: Callable[[str], pd.DataFrame]) -> None:
        super().__init__(file_loader)

    def process(self, file_path:str):

        try:
            df = self.load_file(file_path)
            file_name = os.path.basename(file_path)
            match = re.match(
                r"([A-Z]+)_([0-9]+(\.[0-9]+)?)_([A-Z]+)_([0-9]+).csv", file_name
            )
            if match:
                underlying, strike, _, expiry_type, date_str = match.groups()

                # Now you have the extracted components
                print(f"Underlying: {underlying}")
                print(f"Strike: {strike}")
                print(f"Expiry Type: {expiry_type}")
                print(f"Date: {date_str}")

            # Display columns and first five rows
            print("Columns:", df.columns)
            print("First five rows:")
            print(df.head())

            # TODO: need to add the field mapping (external-->internal)
            return df

        except Exception as ex:
            logger.critical(f"error while processing file {file_path} at line:{get_exception_line_no()}. ErrorMessage:{ex}")
        return 