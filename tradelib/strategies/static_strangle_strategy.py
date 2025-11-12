from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
from tradelib.strategies.strategy_components.static_strangle_component import StaticStrangleComponent
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from tradelib.strategies.strategy_components.hedge_component import HedgeComponent
from tradelib.strategies.strategy_components.unwind_component import UnwindComponent

from tradelib_global_constants import trade_interval_time, hedge_interval_time, OTM_outstrike

class StaticStrangleStrategy(TradeStrategy):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> None:
        super().__init__("static_strangle_strategy", trading_platform, portfolio, blotter)

        unwind_component = UnwindComponent(trading_platform, self.portfolio, self.blotter)
        self.add_component(unwind_component)

        static_strangle_component = StaticStrangleComponent(trading_platform, self.portfolio, self.blotter, trade_interval_time, OTM_outstrike)
        self.add_component(static_strangle_component)

        hedge_component = HedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time)
        self.add_component(hedge_component)
