from datetime import datetime,timedelta
import pandas as pd
import os
from modules.global_variables import params
from modules._utils import get_expiry_list_from_date_range,preprocess_eis_data
from modules._logger import logger, get_exception_line_no
import gc



def get_combined_parquet_files(underlying:str ,start_date_time:datetime, end_date_time:datetime,expiry_type:str,DATA_DIRECTORY:str)-> None:
    ''' 
    This function will create the combined parquet files between the given dates seperated by the expirires.
    start_date_time : datetime, end_date_time: datetime, expiry_type:str - (nearest_monthly/nearest_weekly)
    underlying : str - name of underlying, DATA_DIRECTORY : str - path to the datastore
    '''
    try:
        # Creating the Parquet Datastore
        os.makedirs(os.path.join(DATA_DIRECTORY,'parquet_datasets'), exist_ok=True)
        # Getting the expiry list based on the start_date, end_date and the expiry type
        exp_dates = get_expiry_list_from_date_range(start_date=start_date_time,end_date=end_date_time,expiry_type=expiry_type)
        # logger.info(f'Expiry list created : {exp_dates}')
        # Setting the first_trading_day as start_datetime for iterating 
        first_trading_day = start_date_time
        # Counter is used to track the expiry from the expiry list
        counter = 0
        # Iterating over the batch of expiry windows
        while first_trading_day <= end_date_time : 
            # print(f'{first_trading_day} : {exp_dates[counter]}' )
            # Creating the master dataframe
            master_df_list = []
            # master_df = pd.DataFrame()
            current_date = first_trading_day
            # Iterating over each day to load the file and append it to the master dataframe
            while current_date.date() <= exp_dates[counter].date():
                try:
                    # loading the data
                    df = pd.read_csv(os.path.join(DATA_DIRECTORY, f'{underlying}_{current_date.strftime("%Y%m%d")}_Intraday.csv'))
                    # Concating the day's data to the master dataframe
                    master_df_list.append(df)

                    # Increamenting the current_date by 1 days
                    current_date += timedelta(days=1)
                    del df
                    gc.collect()
                    
                except Exception as e:
                    logger.critical(f'Error : {e} at {current_date}; at line no. {get_exception_line_no()} : File not loaded / error in concat.')
                    # Increamenting the current_date by 1 days
                    current_date += timedelta(days=1)

            master_df = pd.concat(master_df_list, ignore_index=True)
            del master_df_list
            gc.collect()

            logger.info(f'Preprocessing the combined data')
            # preprocessing the eis_data
            master_df = preprocess_eis_data(master_df)
            try: 
                # filtering the data on the expiry date
                master_df = master_df[master_df['ExpiryDate'] == f'{str(exp_dates[counter].date())}']
                logger.info(f'Filtering data on expiry date : {str(exp_dates[counter].date())}')

                # Saving the file to Parquet_datasets
                logger.info(f'Saving master_df to data dir : {os.path.join(DATA_DIRECTORY,f"parquet_datasets")}')
                master_df.to_parquet(os.path.join(DATA_DIRECTORY,f'parquet_datasets',f'{underlying}_{first_trading_day.date()}_{exp_dates[counter].date()}.parquet'),engine='pyarrow',compression=None)

                print(f"Successfully saved :: {underlying}_{first_trading_day.date()}_{exp_dates[counter].date()}.parquet")
                # Increamenting to next trading expiry starting day
            except:
                logger.error(f'data not found in parquet generator')

            first_trading_day = exp_dates[counter]+timedelta(days=1)
            counter+=1

            del master_df
            gc.collect()

    except Exception as e:
        logger.critical(f'Error : {e} in get_combined_parquet_files at line : {get_exception_line_no()}')
    

if __name__ == '__main__':
    
    start_date_time = datetime.strptime(params['START_DATE_TIME'][:10],'%Y-%m-%d')
    end_date_time = datetime.strptime(params['END_DATE_TIME'][:10],'%Y-%m-%d')
    # start_date = start_date_time.date()
    # end_date = end_date_time.date()

    get_combined_parquet_files(underlying = params['UNDERLYING'] ,start_date_time=start_date_time, end_date_time=end_date_time,expiry_type=params["EXPIRY_TYPE"],DATA_DIRECTORY=params['DATA_DIRECTORY'])