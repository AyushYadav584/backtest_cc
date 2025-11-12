from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
from tradelib.strategies.strategy_components.straddle_component import StraddleComponent
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from tradelib.strategies.strategy_components.hedge_component import HedgeComponent
from tradelib.strategies.strategy_components.fut_hedge_component import FutureHedgeComponent
from tradelib.strategies.strategy_components.unwind_component import UnwindComponent
from tradelib.strategies.strategy_components.settelment_component import SettelmentComponent
from tradelib.strategies.strategy_components.gamma_hedge_component import GammaHedgeComponent

from tradelib_global_constants import trade_interval_time, unwind_trade_side,strategy_trade_side,hedge_trade_side,  hedge_interval_time, OTM_outstrike, gamma_hedge, m2m_side

class StraddleStrategy(TradeStrategy):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> None:
        super().__init__("straddle_strategy", trading_platform, portfolio, blotter)

        self.m2m_side = m2m_side

        unwind_component = SettelmentComponent(trading_platform, self.portfolio, self.blotter, unwind_trade_side)
        self.add_component(unwind_component)

        straddle_component = StraddleComponent(trading_platform, self.portfolio, self.blotter, trade_interval_time, OTM_outstrike, trade_side=strategy_trade_side)
        self.add_component(straddle_component)

        hedge_component = FutureHedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time, hedge_trade_side)
        self.add_component(hedge_component)
