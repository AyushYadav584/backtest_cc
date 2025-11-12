'''
This is the trade generator model
'''

from datetime import datetime, date, time
from typing import Tuple, List
import copy

from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option, get_delta_based_otm_option, get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date
from models.Trade import Trade
from tradelib_logger import logger,get_exception_line_no
from trading_platform._TradingPlatform import TradingPlatform
from models.OptionDetailed import OptionDetailed
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from tradelib_global_constants import expiry_info

class DeltaStrangleComponent(StrategyComponent):
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, delta_outstrike: float, tolerance: int, strict_condor:bool, strict_tolerance: bool, underlying:str, unit_size:int, unwind_time, execute_on_day_start:bool=True ) -> None:

        super().__init__("delta_strangle_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start)

        self.delta_outstrike = delta_outstrike
        self.tolerance = tolerance
        self.strict_condor = strict_condor
        self.strict_tolerance = strict_tolerance
        self.underlying = underlying
        self.unit_size = unit_size
        self.unwind_time = unwind_time

        # attaching expiry should give fexibility to trade condors from different expiries
        # need to think about it. expiry should be handled by unwind component
        # self._expiry = expiry_date 

    def get_component_expiry_list(self, timestamp: datetime):

        theoretical_dates = get_theoretical_date(info_list=expiry_info, current_date=timestamp.date())
        actual_expiry_dates = get_actual_expiry_dates(theoretical_dates_dict=theoretical_dates, trading_platform = self.trading_platform)

        exp_list = []
        for day in actual_expiry_dates.keys():
            # print(i)
            for j, date in enumerate(actual_expiry_dates[day]):
                if date == None:
                    
                    theory_date = theoretical_dates[day][j]
                    self.logger.info(f"{theory_date} ({day}) is not an expiry going for early expiry.")

                    exp_date = get_early_expiry_date(theory_date, timestamp.date(), trading_platform=self.trading_platform, _logger = self.logger)

                    # HOT FIX for Banknifty 2023. Need to change the code.
                    if (exp_date == None) & (theory_date == timestamp.date()):
                        self.logger.info(f"{theory_date} ({day}) is not an expiry going for late expiry.")

                        exp_date = get_late_expiry_date(theory_date, trading_platform=self.trading_platform, _logger=self.logger)

                    if exp_date != None:
                        self.logger.info(f"Found early expiry for {theory_date} ({day}) is {exp_date} ({exp_date.strftime('%A')})")

                    exp_list.append(exp_date)
                    
                else:
                    exp_list.append(date)

        return exp_list

    def generate_trades(self, timestamp: datetime) -> List[Trade]:
        final_trade_list = []
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)

            spot = self.trading_platform.getSpot(timestamp)

            for nearest_expiry_date in component_expiry_list:
                unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)

                if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                    self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                    continue
                
                trade_list = []
                otm_pe, otm_ce = None, None
                
                # OTM trades
                otm_pe = get_delta_based_otm_option(self.trading_platform, self.underlying, self.delta_outstrike, self.tolerance, self.strict_tolerance, "PE", nearest_expiry_date, timestamp, self.logger)
                if otm_pe == None:
                    if self.strict_condor == True:
                        self.logger.critical(f"OTM PE not found, and strict condor is true. skipping {self.name}")
                        continue
                
                otm_ce = get_delta_based_otm_option(self.trading_platform, self.underlying, self.delta_outstrike, self.tolerance, self.strict_tolerance, "CE", nearest_expiry_date, timestamp, self.logger)
                if otm_ce == None:
                    if self.strict_condor == True:
                        self.logger.critical(f"OTM CE not found, and strict condor is true. skipping {self.name}")
                        continue
                
                if otm_ce != None:
                    trade_list.append(Trade(otm_ce, self.unit_size, "trade"))
                if otm_pe != None:
                    trade_list.append(Trade(otm_pe, self.unit_size, "trade"))
                
                self.logger.info(f'OTM PE position: {self.unit_size if otm_ce!=None else 0}, OTM CE position: {self.unit_size if otm_ce!=None else 0}')

                final_trade_list.extend(trade_list)

            return final_trade_list
        except Exception as e:
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e}")
            return final_trade_list