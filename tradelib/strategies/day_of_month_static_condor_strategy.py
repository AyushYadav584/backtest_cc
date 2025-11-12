from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
from tradelib.strategies.strategy_components.day_of_month_static_condor_component import DayofMonthStaticCondorComponent
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from tradelib.strategies.strategy_components.hedge_component import HedgeComponent
from tradelib.strategies.strategy_components.fut_hedge_component import FutureHedgeComponent
from tradelib.strategies.strategy_components.unwind_component import UnwindComponent
from tradelib.tradelib_global_constants import hedge_by_option

from tradelib_global_constants import trade_interval_time, hedge_interval_time, OTM_outstrike, strategy_trade_side, hedge_trade_side, unwind_trade_side, m2m_side

class DayofMonthStaticCondorStrategy(TradeStrategy):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> None:
        super().__init__("day_of_month_static_condor_strategy", trading_platform, portfolio, blotter)

        self.m2m_side = m2m_side

        unwind_component = UnwindComponent(trading_platform, self.portfolio, self.blotter, unwind_trade_side)
        self.add_component(unwind_component)

        day_of_month_static_condor_component = DayofMonthStaticCondorComponent(trading_platform, self.portfolio, self.blotter, trade_interval_time, OTM_outstrike, strategy_trade_side)

        self.add_component(day_of_month_static_condor_component)
        
        if hedge_by_option:
            hedge_component = HedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time, hedge_trade_side)
        else:
            hedge_component = FutureHedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time)
        self.add_component(hedge_component)