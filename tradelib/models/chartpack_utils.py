import numpy as np
import pandas as pd
from tradelib_logger import logger
from datetime import datetime, timedelta
from tradelib_global_constants import *

logger = logger.getLogger("chartpack_utils")


def get_expiry_list_from_date_range(start_date:datetime, end_date:datetime, expiry_type:str):
    '''
    Returns a list of expiry days
    '''
    expiry_list = list()
    start_date_pointer = datetime(year=start_date.year,month=start_date.month,day=start_date.day)
    exp_day_of_week = expiry_day_of_week
    if expiry_type == 'nearest_weekly':
        while start_date_pointer.date() <= end_date.date():
            if start_date_pointer.weekday() == exp_day_of_week:
                tmp_date = start_date_pointer
                while holiday(tmp_date):
                    tmp_date -= timedelta(days=1)
                
                if tmp_date >= start_date:
                    expiry_list.append(tmp_date)

            start_date_pointer += timedelta(days=1)

        # Correction for bnf exp with new rules:
        if underlying == "BANKNIFTY" and start_date.year >= 2023:
            correct_expiry_list = []
            for i in expiry_list:
                if i.strftime("%Y-%m-%d") in BNF_EXP_DICT.keys():
                    c_date = datetime.strptime(BNF_EXP_DICT[i.strftime("%Y-%m-%d")], "%Y-%m-%d")
                    correct_expiry_list.append(datetime(year=c_date.year,month=c_date.month,day=c_date.day))
                else:
                    correct_expiry_list.append(i)

            return correct_expiry_list
    
    elif expiry_type == 'nearest_monthly':
        month_add_factor = 0
        while start_date_pointer.date() <= end_date.date():
            tmp_date = start_date_pointer + timedelta(days=month_add_factor) # move the day to the next month
            next_monthly_expiry = find_last_weekday_of_month(tmp_date.year, tmp_date.month, expiry_day_of_week)
            # if start_date_pointer.weekday() == exp_day_of_week:
            while holiday(next_monthly_expiry):
                next_monthly_expiry -= timedelta(days=1)
            
            if next_monthly_expiry >= start_date:
                expiry_list.append(next_monthly_expiry)

            start_date_pointer = next_monthly_expiry + timedelta(days=1)
            if month_add_factor == 0:
                month_add_factor = 7 # minimum days we should add to move the day to the next month

        # logger.warning(f'expiry_type={expiry_type} is not implemented yet in the function get_expiry_list_from_date_range()')
    else:
        logger.warning(f'expiry_type={expiry_type} is not supported')
    
    return expiry_list


def find_last_weekday_of_month(year:int, month:int, day_of_week:int):
    '''
    Returns the last day of week for the requested month and the day_of_week
    '''
    # Get the first day of the next month
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    first_of_next_month = datetime(next_year, next_month, 1)

    # Find the last day of the current month
    last_day = first_of_next_month - timedelta(days=1)

    # Iterate backwards from the last day until we find the day we are looking for
    current_day = last_day
    while current_day.weekday() != day_of_week:
        current_day -= timedelta(days=1)

    return current_day


def date_difference(date1: datetime, date2: datetime) -> int:
    '''This function return difference between two dates'''

    # difference between dates in timedelta
    delta = date2 - date1
    return delta.days


def get_market_holidays_by_year(year:int)->list:
    '''
    This function gets the holiday list for a given year
    '''

    # with open(f"{params['HOLIDAY_LIST_STORE']}holidays_{year}.json", 'r') as f:
    #     loaded_list = json.load(f)
    # print(HOLIDAY_LIST)
    date_list = list()
    for dt in HOLIDAY_LIST:
        date_time = datetime.strptime(dt,params['DATE_TIME_FORMAT'])
        if date_time.year == year:
            date_list.append(date_time.date())

    return date_list


def get_no_holidays_in_between(from_date:datetime, to_date:datetime):
    '''
    compute the number of holidays between from_date and to_date
    '''

    # if the dates are np.datetime64 need conver them to datetime
    if isinstance(from_date, np.datetime64):
        from_date = datetime.utcfromtimestamp(from_date.astype('O')/1e9)
    if isinstance(to_date, np.datetime64):
        to_date = datetime.utcfromtimestamp(to_date.astype('O')/1e9)

    holiday_list = get_market_holidays_by_year(from_date.year)
    holiday_list.extend(get_market_holidays_by_year(to_date.year))
    holiday_list = list(set(holiday_list))

    holiday_counter = 0
    new_date = from_date
    while new_date <= to_date:
        if (weekend(new_date)) or (new_date.date() in holiday_list):
            holiday_counter += 1
        new_date += timedelta(days=int(1))

    return holiday_counter


def weekend(q_date_time:datetime):
    '''
    checking weekend
    '''
    logger.debug(f'checking whether the date {q_date_time} with day {q_date_time.weekday()} is a weekend')

    is_weekend = False
    if q_date_time.weekday() == 5:
        is_weekend = True
        logger.debug('#'*100)
        logger.debug(f'requested trading day {q_date_time} is a saturday and not a trading day')
        logger.debug('#'*100)
    elif q_date_time.weekday() == 6:
        is_weekend = True
        logger.debug('#'*100)
        logger.debug(f'requested trading day {q_date_time} is a sunday and not a trading day')
        logger.debug('#'*100)
    else:
        is_weekend = False

    return is_weekend


def holiday(q_date_time:datetime):
    '''
    # TODO: to be implemented to check whether new_start_date is a holiday
    '''

    logger.debug(f'checking whether the trading day {q_date_time} with day {q_date_time.weekday()} is a holiday')
    holiday_list = get_market_holidays_by_year(q_date_time.year)
    # print(holiday_list)

    is_holiday = False
    if weekend(q_date_time):
        is_holiday = True
    elif q_date_time.date() in holiday_list:
        is_holiday = True
        logger.debug('#'*100)
        logger.debug(f'requested trading day {q_date_time} is a holiday and not a trading day')
        logger.debug('#'*100)
    else:
        is_holiday = False

    return is_holiday