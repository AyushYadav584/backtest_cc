'''
This module will be responsible for taking care of the backtest processing.
'''

import multiprocessing
from datetime import datetime,timedelta

from modules._logger import logger,get_exception_line_no
from tradelib.processors.controllers import Algo
from tradelib.tradelib_utils import get_expiry_list_from_date_range
from tradelib.tradelib_utils import holiday
from tradelib.tradelib_utils import get_time_interval_list
from tradelib.tradelib_utils import set_trading_end_time
from modules.global_variables import params
from tradelib.strategies import TradeStrategy
from tradelib.processors import Processor

logger = logger.getLogger("BacktestProcessor")

class BacktestProcessor(Processor):

    def __init__(self, algo: Algo) -> None:
        super().__init__(algo)


    def process_single_expiry(self, start_datetime:datetime, expiry_datetime:datetime):
        '''
        responsible for processing a single expiry
        '''
        
        start_datetime_pointer = start_datetime

        while start_datetime_pointer.date() <= expiry_datetime.date():
            logger.info('*'*100)
            logger.info('initiating new trading day for date {0}'.format(start_datetime_pointer.strftime('%Y-%m-%d')))
            print('*'*100)
            print('initiating new trading day for date {0}'.format(start_datetime_pointer.strftime('%Y-%m-%d')))
            
            # check whether new_start_date is a holiday
            if holiday(start_datetime_pointer):
                print(f"{start_datetime_pointer.strftime('%Y-%m-%d')} is a holiday")
                logger.info(f"{start_datetime_pointer.strftime('%Y-%m-%d')} is a holiday")
                # increment the date
                start_datetime_pointer = start_datetime_pointer + timedelta(days=1)
                continue

            # TODO: check whether data is available for the day

            if start_datetime_pointer.date() == expiry_datetime.date():
                end_date_time_pointer = expiry_datetime
            else:
                # will push the date to trade end_date (e.g. 2021-03-10 15:30:00)
                end_date_time_pointer = set_trading_end_time(start_datetime_pointer)

            time_interval_list = get_time_interval_list(start_datetime=start_datetime_pointer,
                                                end_datetime=end_date_time_pointer,
                                                time_delta_type=params["INTERVAL_TYPE"],
                                                time_delta_value=params["INTERVAL_VALUE"])

            # start the driver
            self._algo.driver(time_interval_list)


    def process_date_range(self, start_date:datetime, end_date:datetime):
        '''
        TODO: this function need to be implemented later when we have a date-range smaller than an expiry to process
        '''
        pass


    def process(self, start_date:datetime, end_date:datetime):
        '''
        This function will process a date range
        '''
        try:
            # get the llst of expiry dates within the given date range
            exp_dates = get_expiry_list_from_date_range(start_date=start_date,end_date=end_date,expiry_type=params["EXPIRY_TYPE"])
            start_date_pointer = start_date

            # TODO: while running for smaller period (e.g. 2 days) then expiry list can be empty 
            #       and subsequent logic will fail and backtwst will not run.
            #       So, we need to add functionality to run the backtest for a single day as well.
            #       If we run for single day, no unwind should be involved.
            #       Following is a rough implementation.
            #       NEED TO DISCUSS FURTHER

            if (len(exp_dates) == 0) :
                while start_date_pointer <= end_date:
                    logger.info(f'precessing for day {start_date_pointer}')
                    logger.critical("day wise backtest run is not implmented yet")
            else:
                # TODO: few days may get excluded after the last expiry day, need to take care
                pool = multiprocessing.Pool()
                for exp in exp_dates:
                    # TODO: we can run this function as multiprocess
                    pool.apply_async(self.process_single_expiry, (start_date_pointer, exp))
                    start_date_pointer = exp + timedelta(days=1)

                pool.close()
                pool.join()
            
        except Exception as ex:
            logger.critical(f"exception within process() at line:{get_exception_line_no()}. ERROR:{ex}")