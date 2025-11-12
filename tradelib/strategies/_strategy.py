'''
This module is responsible for defining the TradeStrategy base class
'''

from abc import ABC,abstractmethod
from .strategy_components import StrategyComponent
from typing import List
from datetime import datetime
from trading_platform import TradingPlatform
from models.Backtest import Backtest
from models.Blotter import Blotter
from models.Portfolio import Portfolio


# NEED timestamp
class TradeStrategy(ABC):
    # need to have in concrete class

    def __init__(self, name: str, trading_platform: TradingPlatform, portfolio:Portfolio, blotter: Blotter) -> None:
        self.name = name
        self.blotter = blotter
        self._components: List[StrategyComponent] = list()
        self.trading_platform = trading_platform
        self.portfolio = portfolio

    def execute(self, timestamp: datetime):
        '''
        This method will get executed at each time step of the trading period.
        
        The task of this method is to delegate the tasks of each strategy components 
        and each component is responsible for executing their respective tasks.
        '''

        for component in self._components:
            component.execute_trade(timestamp)

    def reinitailse_on_day_start(self):
        for component in self._components:
            component.reinitailse_on_day_start()

    def add_component(self, component:StrategyComponent):
        self._components.append(component)

    def remove_component(self, component:StrategyComponent):
        self._components.remove(component)