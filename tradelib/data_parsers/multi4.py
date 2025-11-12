import multiprocessing
import os
import pandas as pd
from modules import HistoricalData
import numpy as np
import py_vollib_vectorized as pv
from datetime import datetime, timedelta

from modules.global_variables import params
from modules._utils import get_expiry_list_from_date_range, get_no_holidays_in_between
from modules._logger import logger, get_exception_line_no
from modules._black_scholes import implied_volatility_options
import gc


def calculate_time_to_expiry(expiry:datetime, at_time_t:datetime, total_trading_holidays:int=16) -> float:
    """
    Calculate the time left to the given expiry date and time in minutes.

    Args:
        expiry (datetime): The expiry date and time.
        at_time_t (datetime): The current time.
        total_trading_holidays (int, optional): Total trading holidays in a year. Defaults to 16.

    Returns:
        float: The annualized time left in minutes.
    """
    # calculates the time difference between expiry and present time
    # send in minutes
    total_trading_days_in_year = 252
    number_of_trading_mins_day = (6.25 * 60)

    logger.debug("within calculate_time_to_expiry()")
    try:
        # Convert np.datetime64 to datetime if needed
        if isinstance(expiry, np.datetime64):
            expiry = datetime.utcfromtimestamp(expiry.astype('O')/1e9)

        # Calculate time left and days left until expiry
        time_left, days_left = (expiry - at_time_t), (expiry - at_time_t).days

        # Calculate the minutes left in the current day
        minutes_left = (time_left - timedelta(days=days_left)).seconds // 60

        # Calculate total time left in minutes
        time_left_in_mins = (days_left * number_of_trading_mins_day) + minutes_left

        # Subtract holidays from the time left
        holidays_till_expiry = get_no_holidays_in_between(from_date=at_time_t, to_date=expiry)
        time_left_in_mins = time_left_in_mins - (holidays_till_expiry * 375)

        # Calculate annualized time left
        annualised_time_left = time_left_in_mins / ((total_trading_days_in_year - total_trading_holidays) * number_of_trading_mins_day)

        return annualised_time_left
    except Exception as ex:
        logger.critical(f'error while calculating time to expiry at line={get_exception_line_no()}. # {ex}')


def get_premium(mk_data:pd.DataFrame, q_type:str):
    """
    Get the premium price from market data based on the specified quote type.

    Args:
        mk_data (pd.DataFrame): Market data containing BidPrice and AskPrice.
        q_type (str): Quote type ("bid", "ask", or "mid").

    Returns:
        float: The premium price.
    """
    try:
        # Check the quote type and calculate premium accordingly
        if q_type.lower() == "bid":
            premium = mk_data['BidPrice']
        elif q_type.lower() == "ask":
            premium = mk_data['AskPrice']
        elif q_type.lower() == "mid":
            premium = (mk_data['BidPrice'] + mk_data['AskPrice']) / 2

        return premium
    except Exception as e:
        logger.critical(f'Error : {e} in get_premium at line no. : {get_exception_line_no()}')


def calculate_greeks(row:pd.Series, rf:float=params["RISK_FREE_RATE"]) -> list:
    """
    Calculate option Greeks (Delta, Theta, Gamma, Vega, Sigma) for a given option data row.

    Args:
        row (pd.Series): A row of option data containing necessary information.
        rf (float): Risk-free rate.

    Returns:
        list: A list containing Delta, Theta, Gamma, Vega, Sigma, and ExchToken.
    """
    try:
        # Extract relevant data from the option data row
        time_to_expire = row['Time_to_expire']
        option_type = row['Type']
        spot = row["Spot"]
        strike = row['Strike']

        # Handle the case where time_to_expire is 0
        if time_to_expire == 0.0:
            time_to_expire = 0.00001

        # Determine the option type flag ('p' for PE, 'c' for CE)
        if option_type == "PE":
            flag = 'p'
        else:
            flag = 'c'

        # Calculate implied volatility (Sigma)
        sigma = implied_volatility_options(price=row["Premium"], S=spot, K=strike, t=time_to_expire, r=rf, q=params['DIVIDEND'], option_type=option_type)[0]
        # print(sigma)

        # Calculates the delta for a options
        delta = pv.greeks.delta(flag=flag,S=spot,K=strike,t=time_to_expire,r=rf,sigma=sigma,q=params['DIVIDEND'],model='black_scholes',return_as='numpy')
        
        # Calculates the gamma for a options
        gamma = pv.greeks.gamma(flag=flag,S=spot,K=strike,t=time_to_expire,r=rf,sigma=sigma,q=params['DIVIDEND'],model='black_scholes',return_as='numpy')
        
        # Calculates the theta for a options
        theta = pv.greeks.theta(flag=flag,S=spot,K=strike,t=time_to_expire,r=rf,sigma=sigma,q=params['DIVIDEND'],model='black_scholes',return_as='numpy')
        
        # Calculates the theta for a options
        vega = pv.greeks.vega(flag=flag,S=spot,K=strike,t=time_to_expire,r=rf,sigma=sigma,q=params['DIVIDEND'],model='black_scholes',return_as='numpy')

        return [delta[0], theta[0], gamma[0], vega[0], sigma, row['ExchToken']]
    except Exception as e:
        logger.critical(f'Error : {e} in calculate_greeks at line no. : {get_exception_line_no()}')
        return [np.nan, np.nan, np.nan, np.nan, sigma, row['ExchToken']]


def new_preprocessing(mk_data_object: HistoricalData, dates:list, path: str):
    """
    Perform preprocessing on market data for a list of dates and save the results to CSV files.

    Args:
        mk_data_object (HistoricalData): Market data object.
        dates (list): List of dates to process.
        path (str): Path to save the processed data.
    """
    try:
        print("Preprocessing Date List: ", dates)
        logger.info(f'Entering the for loop for iterating over the dates {dates}')
        
        for date_ in dates:
            print(f'Processing : {date_}')
            
            start_time = datetime.strptime(date_+" "+params['START_TIME'], params['DATE_TIME_FORMAT'])
            end_time =  datetime.strptime(date_+" "+params['END_TIME'], params['DATE_TIME_FORMAT'])

            # final_df = pd.DataFrame()
            final_df_list = []
            
            logger.info('Entering while loop for minuite wise')
            while start_time <= end_time:
                try:
                    # Get a slice of market data for the current time
                    slice_data_obj = mk_data_object.getSlice(start_time)
                    slice_data = slice_data_obj.getData()
                    slice_data.reset_index(inplace = True)
                    
                    # Get spot, time to expiry and premium
                    spot = slice_data_obj.get_spot_v2(start_time)
                    time_to_expire = calculate_time_to_expiry(expiry=slice_data['ExpiryDateTime'][0], at_time_t=start_time)
                    premium = get_premium(slice_data, q_type=params['MARKET_SIDE'])

                    # Add calculated values to the slice_data DataFrame
                    slice_data['Spot'] = spot
                    slice_data['Time_to_expire'] = time_to_expire
                    slice_data['Premium'] = premium

                    # Filter out the data based of ITM % and OTM %
                    # if params['EXPIRY_TYPE'] == "nearest_monthly":
                    #     call_df = slice_data[(slice_data['Type']=="CE") & (slice_data['Spot']*(1+params['OTM_PCT'])>=slice_data['Strike']) & (slice_data['Spot']*(1-params['ITM_PCT'])<=slice_data['Strike'])]

                    #     put_df = slice_data[(slice_data['Type']=="PE") & (slice_data['Spot']*(1-params['OTM_PCT'])<=slice_data['Strike']) & (slice_data['Spot']*(1+params['ITM_PCT'])>=slice_data['Strike'])]

                    #     slice_data = pd.concat([call_df, put_df])

                    #     del call_df, put_df
                    #     gc.collect()
                
                    logger.info(f'Calculation the option greeks')
                    # Calculate option Greeks for each row in the slice_data DataFrame
                    greeks_list = slice_data.apply(lambda row: calculate_greeks(row), axis=1).to_list()
                    greeks_df = pd.DataFrame(greeks_list, columns=["Delta", "Theta", "Gamma", "Vega", "Sigma", "ExchToken"])

                    # Drop unnecessary columns from slice_data
                    slice_data.drop(columns=['Time_to_expire', 'Premium'],inplace=True)

                    # Merge greeks_df with slice_data based on 'ExchToken'
                    logger.info(f'Merging greeks df with slice df')
                    slice_data = pd.merge(slice_data, greeks_df, on='ExchToken')

                    # Store the slice data into a list
                    final_df_list.append(slice_data)

                    del slice_data_obj, slice_data
                except Exception as e:
                    logger.critical(f'Error while at ={start_time} at line={get_exception_line_no()}.# {e}')

                finally:
                    # Increase the start time by 1 minute
                    start_time = start_time + timedelta(minutes=1)

            # Concatenate every minute's slice data into a single dataframe
            final_df = pd.concat(final_df_list, ignore_index=True)

            # Generate a file name based on date and underlying
            file_name = params['UNDERLYING'] +'_'+start_time.date().strftime('%Y%m%d')+'_Intraday_Preprocessed.csv'

            # Save the final DataFrame to a CSV file
            final_df.to_csv(os.path.join(path, file_name), index=False)

            print(f'Successfully saved :: {file_name}')

            del final_df_list, final_df
            gc.collect()

    except Exception as e:
        logger.critical(f'Error : {e} ; in new_preprocessing at line={get_exception_line_no()}')


def get_date_ranges(start_date_time : datetime, end_date_time : datetime, expiry_type : str):
    """
    Generate a list of start and end dates for a given date range and expiry type.

    Args:
        start_date_time (datetime): The start date and time.
        end_date_time (datetime): The end date and time.
        expiry_type (str): The type of expiry.

    Returns:
        list: A list of start and end date pairs.
    """
    try:
        # Get a list of expiry dates within the specified date range
        exp_dates = get_expiry_list_from_date_range(start_date=start_date_time,end_date=end_date_time,expiry_type=expiry_type)

        # Initialize the first trading day as the start date for iteration
        first_trading_day = start_date_time
        end_date_time = exp_dates[-1]
        
        # Counter is used to track the expiry from the expiry list
        counter = 0
        start_end_date = []
        
        # Iterating over the batch of expiry windows
        while first_trading_day < end_date_time:
            # Create a pair of start and end dates as strings
            a = np.array([f'{eval(str(first_trading_day.date()).replace("-",""))}', f'{eval(str(exp_dates[counter].date()).replace("-",""))}'])
            start_end_date.append(a)

            # Increamenting to next trading expiry starting day
            first_trading_day = exp_dates[counter]+timedelta(days=1)
            counter+=1

        return start_end_date
        
    except Exception as e:
        logger.critical(f'Error : {e} in get_date_ranges at_line : {get_exception_line_no()}')


def multi_process(date: list):
    """
    Perform multi-process data preprocessing for a specific date range.

    Args:
        date (list): A list containing the start and end dates.

    Notes:
        This function loads historical data for the specified date range and performs data preprocessing.
    """
    try:
        start_date= date[0]
        end_date=date[1]

        logger.info(f'Start and End date : {start_date} : {end_date}')
        print(f'Start and End date : {start_date} : {end_date}')

        # Create an instance of HistoricalData
        eis_data = HistoricalData(source='eis_data',
                    name = 'EIS DATA',
                    underlying_instrument=params['UNDERLYING'],
                    start_date=start_date,# change to start_date:thrusday
                    end_date=end_date, # change to end_date
                    expiry_type=params['EXPIRY_TYPE'])

        logger.info(f'eis data object loaded')

        # Load preprocessing data for the specified date range
        eis_data.load_preprocessing_data(start_date= str(datetime.strptime(start_date,'%Y%m%d').date()) ,end_date = str(datetime.strptime(end_date,'%Y%m%d').date()))

        # Get unique dates from the loaded data
        dates = np.unique(eis_data.getData().index.strftime('%Y-%m-%d'))

        # Define the path for saving processed data
        if params['PREPROCESSED_STORE'] == "None":
            path = os.path.join('Processed_Data',params['UNDERLYING'],params['EXPIRY_TYPE'].split('_')[1].upper(),params['START_DATE_TIME'].split('-')[0])
        else:
            path = params['PREPROCESSED_STORE']

        # Perform data preprocessing
        new_preprocessing(eis_data, dates, path=path)

    except Exception as e:
        logger.critical(f'Error :  {e} , in Method multi_process at line={get_exception_line_no()}')

    


if __name__ == '__main__':
    program_start_time = datetime.now()
    
    # Create necessary directories for processed data, if they don't exist
    os.makedirs(os.path.join('Processed_Data',params['UNDERLYING'],params['EXPIRY_TYPE'].split('_')[1].upper(),params['START_DATE_TIME'].split('-')[0]),exist_ok=True)

    # Determine the number of available CPU cores
    num_processes = multiprocessing.cpu_count()
    print(num_processes)

    # Create a multiprocessing pool for parallel processing
    pool = multiprocessing.Pool(processes=num_processes)

    # Parse start date, end date, and expiry type from parameters
    start_date_time = datetime.strptime(params['START_DATE_TIME'][:10],'%Y-%m-%d')
    end_date_time = datetime.strptime(params['END_DATE_TIME'][:10],'%Y-%m-%d')
    expiry_type = params['EXPIRY_TYPE']

    # Generate a list of date ranges based on start and end dates
    date_ranges_list = get_date_ranges(start_date_time, end_date_time, expiry_type)

    # Perform parallel processing using the multi_process function
    results = pool.map(multi_process, date_ranges_list)
    
    # Close the multiprocessing pool and wait for all processes to finish
    pool.close()
    pool.join()

    program_end_time = datetime.now()

    print("=================================================================\n")
    print(f"Total Pre processing time : {program_end_time-program_start_time}\n")
    print("=================================================================\n")
    #print(datetime.now())