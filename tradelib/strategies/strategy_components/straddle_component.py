'''
This is the trade generator model
'''

from datetime import datetime, date, time
from typing import Tuple, List
import copy

from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option, get_static_otm_option, get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date

from models.Trade import Trade
from tradelib_logger import logger,get_exception_line_no
from trading_platform._TradingPlatform import TradingPlatform
from models.OptionDetailed import OptionDetailed
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from tradelib_global_constants import underlying, tolerance, strict_condor, strict_tolerance, steps, unit_size, unwind_time, expiry_info, gamma_hedge,day_of_week_signal_strength, trade_start_time

class StraddleComponent(StrategyComponent):
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, outstrike: float, trade_side, execute_on_day_start:bool=True) -> None:
        super().__init__("straddle_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side)
        self.outstrike = outstrike
        self.tolerance = tolerance
        self.strict_condor = strict_condor
        self.strict_tolerance = strict_tolerance
        self.steps = steps
        self.underlying = underlying
        self.unit_size = unit_size
        self.unwind_time = unwind_time

        # attaching expiry should give fexibility to trade condors from different expiries
        # need to think about it. expiry should be handled by unwind component
        # self._expiry = expiry_date
        self._signal_check_date = None
        self._signal_of_the_day = None

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
    
    def generate_signal(self, timestamp:datetime):
        
        try:
            
            return day_of_week_signal_strength

        except Exception as e:
            logger.critical(f"Error :: generate_signal :: error line {get_exception_line_no()} :: {e}")

    def get_day_of_week_signal(self, timestamp: datetime):
        try:
            if self._signal_check_date != timestamp.date():
                signal_strength = self.generate_signal(timestamp=timestamp)
                self._signal_of_the_day = signal_strength.get(timestamp.weekday())

                
                self._signal_check_date = timestamp.date()

            return self._signal_of_the_day

        except Exception as e:
            logger.critical(f"Error: get_day_of_week_signal :: error line {get_exception_line_no()} :: {e}")


    def generate_trades(self, timestamp: datetime) -> List[Trade]:
        final_trade_list = []
        
        current_time = timestamp.time()
        
        if time(17, 0) < current_time or current_time < time(9, 30):
            return final_trade_list
        # if current_time != trade_start_time:
        #     # print('line 100')
        #     return final_trade_list
        try:
            # print('entering')
            component_expiry_list = self.get_component_expiry_list(timestamp)
            # print('line 104')
            spot = self.trading_platform.getSpot(timestamp)
            # print('line 106')

            # set trade size based on signal
            trade_mul = self.get_day_of_week_signal(timestamp=timestamp)   
            unit_size = self.unit_size*trade_mul

            for nearest_expiry_date in component_expiry_list:
                unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)

                if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                    self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                    continue
                    # return final_trade_list
                
                trade_list = []
                atm_pe, atm_ce = None, None
                
                # ATM trades
                atm_pe = get_atm_option(self.trading_platform, self.underlying, spot, "PE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
                if (atm_pe == None):
                    self.logger.critical(f"ATM PE not found, skipping {self.name}")
                    continue

                atm_ce = get_atm_option(self.trading_platform, self.underlying, spot, "CE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
                if atm_ce == None:
                    self.logger.critical(f"ATM CE not found, skipping {self.name}")
                    continue
                if unit_size != 0:
                    trade_list.append(Trade(atm_ce, -unit_size, "trade"))
                    trade_list.append(Trade(atm_pe, -unit_size, "trade"))
                
                
                
                    self.logger.info(f'{self.name} ATM PE position: {-unit_size}, ATM CE position: {-unit_size}')

                final_trade_list.extend(trade_list)

            return final_trade_list
        
        except Exception as e:
            # print('did not enter')
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e}")
            return final_trade_list