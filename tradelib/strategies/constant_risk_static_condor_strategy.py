from ._strategy import TradeStrategy
from trading_platform import TradingPlatform
# from tradelib.strategies.strategy_components.static_condor_component import StaticCondorComponent
from tradelib.strategies.strategy_components.static_condor_const_risk_component import ConstantRiskStaticCondorComponent
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from models.Backtest import Backtest
# from models.MutableNumber import MutableNumber
from tradelib.strategies.strategy_components.hedge_const_risk_component import ConstantRiskHedgeComponent
from tradelib.strategies.strategy_components.hedge_component import HedgeComponent
from tradelib.strategies.strategy_components.unwind_component import UnwindComponent

from tradelib_global_constants import underlying, tolerance, strict_condor, strict_tolerance, steps, unit_size, unwind_time, expiry_info, trade_interval_time, hedge_interval_time, OTM_outstrike

# from tradelib_global_constants import 

class ConstantRiskStaticCondorStrategy(TradeStrategy):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter) -> None:
        super().__init__("constant_risk_static_condor_strategy", trading_platform, portfolio, blotter)

        # self.contact_budge = MutableNumber(300)

        unwind_component = UnwindComponent(trading_platform, self.portfolio, self.blotter)
        self.add_component(unwind_component)

        constant_risk_static_condor_component = ConstantRiskStaticCondorComponent(trading_platform=trading_platform, 
                                blotter=self.blotter,
                                portfolio=self.portfolio,
                                skip_count = trade_interval_time, 
                                outstrike = OTM_outstrike, 
                                tolerance = tolerance, 
                                strict_condor=strict_condor, 
                                strict_tolerance=strict_tolerance, 
                                unwind_time=unwind_time)

        self.add_component(constant_risk_static_condor_component)

        
        hedge_component = ConstantRiskHedgeComponent(trading_platform, self.portfolio, self.blotter, hedge_interval_time)
        self.add_component(hedge_component)
