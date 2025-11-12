from tradelib_global_constants import start_date, end_date, data_dir, output_dir_folder
from tradelib_utils import get_expiry_from_pre_process
from tradelib_logger import logger, get_exception_line_no
from datetime import datetime
import os
import numpy as np
import pandas as pd
import glob
import shutil
import gc

# with open('/home/cloudcraftz/Desktop/leatest-backtest-multi/HFT-Options-EIS-Global/output_dir.txt', 'r') as file:
#     backtest_path = file.read()

backtest_path = os.path.join(output_dir_folder, "backtest/")
consolidated_store_path = os.path.join(output_dir_folder, "consolidated_store/")
os.makedirs(consolidated_store_path, exist_ok=True)

# def copy_csv_files(source_folder, destination_folder):
#     try:
#         if os.listdir(destination_folder) == 0:
#             for file_name in os.listdir(source_folder):
#                 # Check if the file is a CSV file
#                 if file_name.endswith('.csv'):
#                     # Construct full file paths
#                     source_file = os.path.join(source_folder, file_name)
#                     destination_file = os.path.join(destination_folder, file_name)
                    
#                     # Copy the CSV file to the destination folder
#                     shutil.copy(source_file, destination_file)
#         else:
#             pass
#     except Exception as e:
#         logger.critical('Error :: while copy the backtest file.')


def combine_backtest(expiry_list, startCash=0, startTime="092000", endTime="153000"):

    lastfile = np.array(glob.glob(pathname=backtest_path+"*.csv"))
    lastfile.sort(kind="stable")
    # print(lastfile)
    startDate = lastfile[0].split("/")[-1].split(".")[0]

    expiry_list = [d.strftime("%Y%m%d") for d in expiry_list]
    week_no = 0
    for files in lastfile:
        try:
            date = files.split("/")[-1].split(".")[0]
            
            if date >= startDate and date <= expiry_list[week_no]:
                newFile = files.split("/")[-1].split(".")[0]
                data = pd.read_csv(backtest_path+newFile+".csv")
                data['portfolio_value'] = data['portfolio_value'].apply(lambda x: x + startCash)
                data['portfolio_cash'] = data['portfolio_cash'].apply(lambda x: x + startCash)
                lastVal = data['portfolio_value'].iloc[-1]

                
                data.to_csv(path_or_buf=f"{consolidated_store_path}{newFile}.csv", index=False)
                del data
                gc.collect()

            else:
                startDate = date
                try:
                    startCash = lastVal
                except:
                    startCash = startCash
                    
                week_no += 1

                newFile = files.split("/")[-1].split(".")[0]
                data = pd.read_csv(backtest_path+newFile+".csv")
                data['portfolio_value'] = data['portfolio_value'].apply(lambda x: x + startCash)
                data['portfolio_cash'] = data['portfolio_cash'].apply(lambda x: x + startCash)
                lastVal = data['portfolio_value'].iloc[-1]

                data.to_csv(path_or_buf=f"{consolidated_store_path}{newFile}.csv", index=False)
                del data
                gc.collect()

        except Exception as e:
            # print(files.split("/")[-1].split(".")[0], "Problem is: ", e)
            print(f'{files.split("/")[-1].split(".")[0]} : exception within combine_backtest() at line {get_exception_line_no()}. {e}')

if __name__ == '__main__':
    print('running backtest combiner')
    # start = datetime.datetime.strptime(params['START_DATE_TIME'],params['DATE_TIME_FORMAT'])
    # end = datetime.datetime.strptime(params['END_DATE_TIME'],params['DATE_TIME_FORMAT'])
    start = start_date
    end = end_date

    expiry_list = get_expiry_from_pre_process(data_dir=data_dir)
    filtered_exp_list = [date for date in expiry_list if start_date <= date <= end_date]

    print(filtered_exp_list)

    combine_backtest(expiry_list=filtered_exp_list, startCash=0, 
                     startTime=start.strftime('%H%M%S'),endTime=end.strftime('%H%M%S'))
    
    print('backtest combiner finished')

    shutil.copy("tradelib/tradelib_global_constants.py", f"{output_dir_folder}/tradelib_global_constants.py")