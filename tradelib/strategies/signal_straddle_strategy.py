from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from tradelib.strategies.strategy_components.signal_straddle_component import SignalStraddleComponent
from tradelib.strategies.strategy_components.hedge_component import HedgeComponent
from tradelib.strategies.strategy_components.unwind_component import UnwindComponent
from tradelib.strategies.strategy_components.fut_hedge_component import FutureHedgeComponent
from tradelib.strategies.strategy_components.straddle_component import StraddleComponent

from tradelib_global_constants import trade_interval_time, hedge_interval_time, OTM_outstrike, unwind_trade_side, strategy_trade_side, \
                                      hedge_trade_side, m2m_side, hedge_by_option, signal_strat_time, signal_end_time, entry_cool_off_time, \
                                          exit_cool_off_time, signal_tolerance, slow_lookback_period, fast_lookback_period, rsi_contract_quota

class SignalStraddleStrategy(TradeStrategy):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> None:
        super().__init__("signal_straddle_strategy", trading_platform, portfolio, blotter)

        self.m2m_side = m2m_side

        unwind_component = UnwindComponent(trading_platform, self.portfolio, self.blotter, unwind_trade_side, contract_quota=rsi_contract_quota)
        self.add_component(unwind_component)

        # first_trade_component = StraddleComponent(trading_platform=trading_platform,
        #                                           portfolio=self.portfolio,
        #                                           blotter=self.blotter,
        #                                           skip_count=12345,
        #                                           outstrike=OTM_outstrike,
        #                                           trade_side=strategy_trade_side,
        #                                           )
        # self.add_component(first_trade_component)

        strategy_component = SignalStraddleComponent(trading_platform=trading_platform,
                                                    portfolio=self.portfolio,
                                                    blotter=self.blotter,
                                                    skip_count=1,
                                                    outstrike=OTM_outstrike,
                                                    trade_side=strategy_trade_side,
                                                    signal_strat_time=signal_strat_time,
                                                    signal_end_time=signal_end_time,
                                                    entry_cool_off_time=entry_cool_off_time, #10,
                                                    exit_cool_off_time=exit_cool_off_time, #7,
                                                    signal_tolerance=signal_tolerance, #0.12,
                                                    fast_lookback_period=fast_lookback_period, #1,
                                                    slow_lookback_period=slow_lookback_period, #5,
                                                    contract_quota=rsi_contract_quota
                                                    )
        self.add_component(strategy_component)
        
        if hedge_by_option:
            hedge_component = HedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time, hedge_trade_side)
        else:
            hedge_component = FutureHedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time)
        self.add_component(hedge_component)
