from strategies import StrategyFactory
from trading_platform import TradingPlatform
from datetime import datetime, date, time
from tradelib_logger import logger, get_exception_line_no
from datetime import date
from models.Portfolio import Portfolio
from models.Backtest import Backtest
from models.Blotter import Blotter
from tradelib_global_constants import underlying, interval, strategy_to_execute, date_time_format
import copy
from strategies.strategy_components._strategy_component import StrategyComponent
from typing import List

from tradelib_global_constants import MAINTENANCE_START, MAINTENANCE_END

class AlgoDriver:
    def __init__(self, strategy_name:str, output_dir:str, trading_platform: TradingPlatform, portfolio:Portfolio, start_time:time, end_time: time, strategy_components: List[StrategyComponent]=[]) -> None:
        self.trading_platform = trading_platform
        self._time_interval_cntr = 0
        self.logger = logger.getLogger("algo_driver")
        self.output_dir = output_dir
        self.portfolio = portfolio
        self.blotter = Blotter(output_dir)
        self.backtest = Backtest(portfolio, self.trading_platform, output_dir)
        self.interval = interval
        self.underlying = underlying
        self.end_time = end_time
        self.start_time = start_time
        self.strategy_to_execute = strategy_to_execute
        self.strategy = StrategyFactory().build(strategy_name, strategy_components, self.trading_platform, self.portfolio, self.blotter, self.backtest)

    # TODO: change to date from str
    def drive(self, date: date):
        try:
            start_date_time = datetime.combine(date, self.start_time) # datetime.strptime(dat + " " + self.start_time, date_time_format)
            end_date_time = datetime.combine(date, self.end_time)

            itr_date_time = copy.copy(start_date_time)
            while itr_date_time <= end_date_time:

                ## Add maintenance time
                if (underlying == 'SPXW') and (itr_date_time.time() >= MAINTENANCE_START and itr_date_time.time() <= MAINTENANCE_END):
                    itr_date_time = itr_date_time + self.interval
                    continue

                self._time_interval_cntr += 1
                if (itr_date_time.time() == self.start_time):
                    self.strategy.reinitailse_on_day_start()

                timestr = itr_date_time.strftime(date_time_format)
                self.logger.info(f'{"-"*20} timestamp: {timestr} {"-"*20}')

                spot = self.trading_platform.getSpot(itr_date_time)
                self.logger.info(f'spot: {spot}')

                ## Check future price problem. & continue
                if spot == None:
                    self.logger.warning(f"At time {itr_date_time} the underlying price have some problem.")
                    itr_date_time = itr_date_time + self.interval
                    continue

                try:
                    self.backtest.addBacktestEntry(itr_date_time, False, self.strategy.m2m_side)
                    self.logger.info("Backtest entry added before strategy execution")

                    self.strategy.execute(itr_date_time)
                    self.logger.info(f'{"-"*20} strategy: {self.strategy.name} executed {"-"*20}')

                    self.backtest.addBacktestEntry(itr_date_time, True, self.strategy.m2m_side)
                    self.logger.info("2nd Backtest entry added after strategy execution")

                    if itr_date_time.date() == datetime(2024, 6, 27, 9, 30).date():
                        self.portfolio.saveToCSV(itr_date_time)

                except Exception as e:
                    logger.critical(e)
                itr_date_time = itr_date_time + self.interval
            self.portfolio.saveToCSV(end_date_time)
            self.logger.info('portfolio dumped')
            self.blotter.saveToCsvAndClear(start_date_time, end_date_time)
            self.logger.info('blotter dumped')
            self.backtest.saveToCsvAndClear(end_date_time.date())
            self.logger.info('backtest dumped')
        except Exception as e:
            logger.critical(f"Error :: algo driver :: {get_exception_line_no()} :: {e}")