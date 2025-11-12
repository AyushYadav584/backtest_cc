'''
this module is responsible for start processing the backtest data
'''

from tradelib.data_parsers import BacktestDataProcessor
from tradelib.data_parsers import ThetaDataAdapter
from tradelib.data_parsers import json_loader,csv_loader
DATA_SOURCE = "THETA" # could be "CBOE", "REFINITIVE" etc
DATA_FILE_TYPE = "csv"
DATA_DIR = "datasets/theta/"


def get_file_type_loader(file_type:str):
    if file_type == 'csv':
        return csv_loader
    elif file_type == 'json':
        return json_loader
    else:
        print(f"file type {file_type} not supported yet")
        return None


if __name__ == "__main__":
    data_processor = BacktestDataProcessor(data_directory=DATA_DIR, file_type=DATA_FILE_TYPE)
    if DATA_SOURCE == "THETA":
        print(f"initiating Theta Data processor")
        data_processor.set_adapter(ThetaDataAdapter(file_loader=get_file_type_loader(DATA_FILE_TYPE)))
        data_processor.process()
    elif DATA_SOURCE == "EIS":
        print(f"initiating Theta Data processor")
        # data_processor.set_adapter(EisDataAdapter(file_loader=get_file_type_loader(DATA_FILE_TYPE)))
        # data_processor.process()
        pass
    else:
        print(f"data source {DATA_SOURCE} is not supported yet.")

