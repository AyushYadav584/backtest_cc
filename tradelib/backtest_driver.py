from datetime import datetime, date, timedelta, time
from tradelib_logger import logger, change_log_file_handler
from algo_driver import AlgoDriver
from models.Portfolio import Portfolio
from trading_platform.BacktestTradingPlatform import BacktestTradingPlatform
from trading_platform._TradingPlatform import TradingPlatform
from tradelib_global_constants import date_format, currency, data_dir, spot_move_threshold, check_future_price, check_option_prices, check_intrinsic_value, check_bid_ask, bid_ask_move_threshold, check_price_problem_start_time
from tradelib_utils import is_data_available_for_date, get_holiday_list
from tradelib_trade_utils import is_trading_date
import numpy as np
from strategies._strategy import TradeStrategy
from typing import List
from strategies.strategy_components._strategy_component import StrategyComponent
from strategies.strategy_factory import StrategyFactory
from multiprocessing import Pool
from tradelib.tradelib_utils import get_expiry_from_pre_process

class BacktestDriver:
    def __init__(self, start_date: date, end_date: date, trade_start_time: time, trade_end_time: time, data_dir: str, output_dir: str,strategy_name: str, strategy_components: List[StrategyComponent]=[], risk_free_rate:float=None, steps:float=None, underlying:str=None, dividend:str=None) -> None:
        self.trading_platform = BacktestTradingPlatform(data_dir, risk_free_rate, steps, underlying, dividend, spot_move_threshold, check_future_price, check_option_prices, check_intrinsic_value, check_bid_ask, bid_ask_move_threshold, check_price_problem_start_time)
        self.output_dir = output_dir
        self.logger = logger.getLogger("backtest_driver")
        self.portfolio = Portfolio(currency, self.trading_platform, self.output_dir)
        self.algo_driver = AlgoDriver(strategy_name, self.output_dir,self.trading_platform, self.portfolio, trade_start_time, trade_end_time, strategy_components)
        self.start_date = start_date
        self.end_date = end_date
        self.holiday_list = get_holiday_list(self.start_date.year)


    def single_process_driver(self, start_date, expiry_date):
        if start_date > self.end_date or start_date > expiry_date:
            return

        print("Started for ", start_date, "-", expiry_date)
        end_date_str = expiry_date.strftime('%Y-%m-%d')
        change_log_file_handler(f"multi_{end_date_str}")        
        logger.info('#'*100)
        logger.info(f'starting trade simulator for the period {start_date.strftime("%Y-%m-%d")} - {expiry_date.strftime("%Y-%m-%d")}')
        
        while start_date <= expiry_date:
            if is_trading_date(date=start_date, trading_platform=self.trading_platform):
                self.logger.info(f'{"-"*20} trading day: {start_date.strftime(date_format)} {"-"*20}')
                self.algo_driver.drive(start_date)
            else:
                if start_date.weekday() in [5, 6]:
                    self.logger.info(f"date: {start_date.strftime(date_format)} is a weekend")
                elif start_date in self.holiday_list:
                    
                    self.logger.info(f"date: {start_date.strftime(date_format)} is holiday")
                else:
                    self.logger.critical(f"trading day data not available for: {start_date.strftime(date_format)}")

            start_date = start_date + timedelta(days=1)

        
    def run_backtest_multiprocess(self, num_processes):
        """
        Runs the backtest using multiple processes.
        """
        expiry_list = get_expiry_from_pre_process(data_dir=data_dir)

        # Filter the expiry dates
        filtered_exp_dates = [date1 for date1 in expiry_list if self.start_date <= date1 <= self.end_date]

        pool = Pool(processes=num_processes)
        start_date_pointer = self.start_date

        for exp in filtered_exp_dates:
            pool.apply_async(self.single_process_driver, (start_date_pointer, exp))

            start_date_pointer = exp + timedelta(days=1)

        pool.close()
        pool.join()