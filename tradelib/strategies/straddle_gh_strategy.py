from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
# from tradelib.strategies.strategy_components.straddle_component import StraddleComponent
from tradelib.strategies.strategy_components.straddle_gh_component import StraddleGammaHedgeComponent
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from tradelib.strategies.strategy_components.hedge_component import HedgeComponent
from tradelib.strategies.strategy_components.unwind_component import UnwindComponent
from tradelib.strategies.strategy_components.gamma_hedge_component import GammaHedgeComponent

from tradelib_global_constants import trade_interval_time, hedge_interval_time, OTM_outstrike, gamma_hedge

class StraddleGammaHedgeStrategy(TradeStrategy):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> None:
        super().__init__("straddle_gh_strategy", trading_platform, portfolio, blotter)

        unwind_component = UnwindComponent(trading_platform, self.portfolio, self.blotter)
        self.add_component(unwind_component)

        straddle_component = StraddleGammaHedgeComponent(trading_platform, self.portfolio, self.blotter, trade_interval_time, OTM_outstrike)
        self.add_component(straddle_component)

        gamma_hedge_component = GammaHedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time, OTM_outstrike)
        self.add_component(gamma_hedge_component)

        hedge_component = HedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time)
        self.add_component(hedge_component)
