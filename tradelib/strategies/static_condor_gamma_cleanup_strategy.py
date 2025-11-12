from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
from tradelib.strategies.strategy_components.static_condor_component import StaticCondorComponent
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from tradelib.strategies.strategy_components.hedge_component import HedgeComponent
from tradelib.strategies.strategy_components.fut_hedge_component import FutureHedgeComponent
from tradelib.strategies.strategy_components.unwind_component import UnwindComponent
from tradelib.strategies.strategy_components.gamma_cleanup_component import GammaCleanupComponent
from tradelib.tradelib_global_constants import hedge_by_option

from tradelib_global_constants import trade_interval_time, hedge_interval_time, OTM_outstrike, strategy_trade_side, hedge_trade_side, unwind_trade_side, m2m_side, gamma_threshold, gamma_condor, otm_strike_tolerance, gamma_cleanup_trade_interval_time

class StaticCondorGammaCleanupStrategy(TradeStrategy):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> None:
        super().__init__("static_condor_gamma_cleanup_strategy", trading_platform, portfolio, blotter)

        self.m2m_side = m2m_side

        unwind_component = UnwindComponent(trading_platform, self.portfolio, self.blotter, unwind_trade_side)
        self.add_component(unwind_component)

        static_condor_component = StaticCondorComponent(trading_platform, self.portfolio, self.blotter, trade_interval_time, OTM_outstrike, strategy_trade_side)
        self.add_component(static_condor_component)

        gamma_cleanup_component = GammaCleanupComponent(trading_platform, self.portfolio, self.blotter, skip_count=gamma_cleanup_trade_interval_time, outstrike=OTM_outstrike, trade_side=strategy_trade_side, gamma_threshold=gamma_threshold, gamma_condor=gamma_condor, otm_strike_tolerance=otm_strike_tolerance)
        self.add_component(gamma_cleanup_component)
        
        if hedge_by_option:
            hedge_component = HedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time, hedge_trade_side)
        else:
            hedge_component = FutureHedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time)
        self.add_component(hedge_component)