'''
this class is responsible for building strategies
'''
from ._strategy import TradeStrategy
from .static_condor_strategy import StaticCondorStrategy
from .delta_condor_strategy import DeltaCondorStrategy
from .constant_risk_static_condor_strategy import ConstantRiskStaticCondorStrategy
from .straddle_strategy import StraddleStrategy
from .static_strangle_strategy import StaticStrangleStrategy
from .delta_strangle_strategy import DeltaStrangleStrategy
from .straddle_gh_strategy import StraddleGammaHedgeStrategy
from .day_of_week_static_condor_strategy import DayofWeekStaticCondorStrategy
from .day_of_month_static_condor_strategy import DayofMonthStaticCondorStrategy
from .day_of_month_frequency_static_condor_strategy import DayofMonthFrequencyStaticCondorStrategy
from .day_of_month_dual_signal_static_condor_strategy import DayofMonthDualSignalStaticCondorStrategy
from .vssma_straddle_strategy import VSSMAStraddleStrategy
from .signal_straddle_strategy import SignalStraddleStrategy
from .macd_signal_straddle_strategy import MacdSignalStraddleStrategy
from .rsi_condor_strategy import RsiCondorStrategy
from .static_condor_gamma_cleanup_strategy import StaticCondorGammaCleanupStrategy
# from .rsi_straddle_strategy import RSIStraddleStrategy
# from .rsi_strangle_strategy import RSIStrangleStrategy
# from .sma_straddle_strategy import SMAStraddleStrategy
from .day_of_week_delta_condor_strategy import DayofWeekStaticDeltaStrategy
# from .vssma_threefold_strategy import VSSMAStraddleThreefoldStrategy
from trading_platform import TradingPlatform
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
from .general_strategy import GeneralStrategy
from .strategy_components._strategy_component import StrategyComponent
from typing import List

class StrategyFactory():
    def build(self, strategy_name: str, component_list: List[StrategyComponent], trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, backtest: Backtest):
        if (len(component_list) == 0):
            return self.fromName(strategy_name, trading_platform, portfolio, blotter)
        else:
            return self.fromComponentList(strategy_name, component_list, trading_platform, portfolio, blotter, backtest)


    def fromName(self, strategy_name: str, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> TradeStrategy:
        if strategy_name == "STATIC_CONDOR_STRATEGY":
            return StaticCondorStrategy(trading_platform, portfolio, blotter)

        elif strategy_name == "DELTA_CONDOR_STRATEGY":
            return DeltaCondorStrategy(trading_platform, portfolio, blotter)

        elif strategy_name == "CONSTANT_RISK_CONDOR_STRATEGY":
            return ConstantRiskStaticCondorStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "STRADDLE_STRATEGY":
            return StraddleStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "STATIC_STRANGLE_STRATEGY":
            return StaticStrangleStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "DELTA_STRANGLE_STRATEGY":
            return DeltaStrangleStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "STRDDLE_STRATEGY_GH":
            return StraddleGammaHedgeStrategy(trading_platform, portfolio, blotter)

        elif strategy_name == "DAY_OF_WEEK_STATIC_CONDOR_STRATEGY":
            return DayofWeekStaticCondorStrategy(trading_platform, portfolio, blotter)

        elif strategy_name == "DAY_OF_WEEK_DELTA_CONDOR_STRATEGY":
            return DayofWeekStaticDeltaStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "DAY_OF_MONTH_STATIC_CONDOR_STRATEGY":
            return DayofMonthStaticCondorStrategy(trading_platform, portfolio, blotter)

        elif strategy_name == "DAY_OF_MONTH_FREQUENCY_STATIC_CONDOR_STRATEGY":
            return DayofMonthFrequencyStaticCondorStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "DAY_OF_MONTH_DUAL_SIGNAL_STATIC_CONDOR_STRATEGY":
            return DayofMonthDualSignalStaticCondorStrategy(trading_platform, portfolio, blotter)

        elif strategy_name == "VSSMA_STRADDLE_STRATEGY":
            return VSSMAStraddleStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "SIGNAL_STRADDLE_STRATEGY":
            return SignalStraddleStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "MACD_SIGNAL_STRADDLE_STRATEGY":
            return MacdSignalStraddleStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "RSI_CONDOR_STRATEGY":
            return RsiCondorStrategy(trading_platform, portfolio, blotter)
        
        elif strategy_name == "VSSMA_THREEFOLD_STRATEGY":
            return VSSMAStraddleThreefoldStrategy(trading_platform, portfolio, blotter)

        # elif strategy_name == "RSI_STRADDLE_STRATEGY":
        #     return RSIStraddleStrategy(trading_platform, portfolio, blotter)

        # elif strategy_name == "RSI_STRANGLE_STRATEGY":
        #     return RSIStrangleStrategy(trading_platform, portfolio, blotter)

        # elif strategy_name == "SMA_STRADDLE_STRATEGY":
        #     return SMAStraddleStrategy(trading_platform, portfolio, blotter)

        elif strategy_name == "STATIC_CONDOR_GAMMA_CLEANUP_STRATEGY":
            return StaticCondorGammaCleanupStrategy(trading_platform, portfolio, blotter)
        
        else:
            print(f"Strategy {strategy_name} has not built yet!")
            return None

        
    def fromComponentList(self, strategy_name: str, component_list: List[StrategyComponent], trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter):
        return GeneralStrategy(strategy_name, component_list, trading_platform, portfolio, blotter)
