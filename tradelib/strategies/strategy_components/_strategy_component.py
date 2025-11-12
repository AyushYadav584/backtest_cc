'''
This module will conatain the base class for all the componenents for trading strategies
'''

from abc import ABC, abstractmethod
from datetime import datetime, time
from trading_platform import TradingPlatform
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Trade import Trade
# from models.MutableNumber import MutableNumber
from logging import Logger
from tradelib_utils import is_component_execution_time
from tradelib_global_constants import date_time_format, gamma_hedge_time
from tradelib_logger import logger

from typing import List

class StrategyComponent(ABC):

    def __init__(self, name: str, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count: int, execute_on_day_start: bool, trade_side:str='mid', contract_quota: int = None) -> None:
        self.name = name
        self.logger = logger.getLogger(name)
        self.trading_platform = trading_platform
        self.trade_list: List[Trade] = []
        self.portfolio = portfolio
        self.blotter = blotter
        self._time_skip_count = skip_count
        self.execute_on_day_start = execute_on_day_start
        self._time_skip_counter = self._time_skip_count if self.execute_on_day_start else 0
        self.trade_side = trade_side
        self.contract_quota = contract_quota


    def update_portfolio(self, timestamp: datetime):
        self.portfolio.updatePortfolio(self.trade_list, timestamp, self.trade_side)
        self.blotter.addTradeList(self.trade_list, self.name, timestamp)
        self.trade_list.clear()

    # def set_dn(self, dn):
    #     self.dn = dn
        
    # def change_contract_budget(self):
    #     if self.contract_budget != None:
    #         self.contract_budget.n -= self.dn

    def set_contract_quota(self, contract_quota):
        self.contract_quota = contract_quota

    def execute_trade(self, timestamp: datetime):
        _is_component_execution_time, self._time_skip_counter = is_component_execution_time(skip_count=self._time_skip_count, skip_counter=self._time_skip_counter)
        if _is_component_execution_time:
            self.logger.info(f'{"-"*20} {self.name} Trade time: {timestamp.strftime(date_time_format)} {"-"*20}')

            self.trade_list = self.generate_trades(timestamp)

            if (len(self.trade_list) > 0):
                self.update_portfolio(timestamp)
                self.logger.info(f"{self.name} - took trades.")
            else:
                self.logger.info(f"{self.name} - had no trades in it's trading list for this timestamp.")

            self.logger.info(f'{"-"*20} {self.name} executed {"-"*20}')

    @abstractmethod
    def generate_trades(self, timestamp: datetime) -> List[Trade]:
        pass

    # TODO: add abstract method of get_component expiry list
    
    def reinitailse_on_day_start(self):
        self._time_skip_counter = self._time_skip_count if self.execute_on_day_start else 0
