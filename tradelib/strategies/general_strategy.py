from tradelib.trading_platform import TradingPlatform
from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from typing import List
from .strategy_components._strategy_component import StrategyComponent

class GeneralStrategy(TradeStrategy):
    def __init__(self, name: str, component_list: List[StrategyComponent], trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, backtest: Backtest) -> None:
        super().__init__(name, trading_platform, portfolio, blotter, backtest)
        for component in component_list:
            self.add_component(component)
