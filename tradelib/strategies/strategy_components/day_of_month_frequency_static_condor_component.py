'''
This is the trade generator model
'''

from datetime import datetime, date, time, timedelta
from typing import Tuple, List
import copy

from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry, is_holiday_in_a_week
from tradelib_trade_utils import get_atm_option, get_static_otm_option, get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date, is_trading_date

from models.Trade import Trade
from tradelib_logger import logger,get_exception_line_no
from trading_platform._TradingPlatform import TradingPlatform
from models.OptionDetailed import OptionDetailed
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from tradelib_global_constants import underlying, tolerance, strict_condor, strict_tolerance, steps, unit_size, unwind_time, expiry_info, day_of_month_signal_strength, day_of_month_signal_frequency

class DayofMonthFrequencyStaticCondorComponent(StrategyComponent):
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, outstrike: float, trade_side, execute_on_day_start:bool=True) -> None:
        super().__init__("day_of_month_frequency_static_condor_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side)

        self.outstrike = outstrike
        self.tolerance = tolerance
        self.strict_condor = strict_condor
        self.strict_tolerance = strict_tolerance
        self.steps = steps
        self.underlying = underlying
        self.unit_size = unit_size
        self.unwind_time = unwind_time
        # self.day_of_week_signal_strength = day_of_week_signal_strength

        self._signal_check_date = None
        self._signal_of_the_day = None

        self.last_trade_time = None

        self._nearest_expiry = None
        self._monthly_signal_dict = None

        # attaching expiry should give fexibility to trade condors from different expiries
        # need to think about it. expiry should be handled by unwind component
        # self._expiry = expiry_date


    def get_first_trading_day(self, nearest_expiry_date) -> datetime:
        """
        Returns the first trading day for the nearest expiry date
        Eg: 
            Current Date: Nov 15 2024
            Nearest Expiry Date: Nov 27 2024 (for monthly BNF)

        Returns: 
            First Trading Date after the Last Expiry Date
            Last expiry Date: Oct 30 2024
            Returns: Oct 31 2024
        """
        try:
            expiry_date_list = self.trading_platform.get_expiry_list()

            if nearest_expiry_date in expiry_date_list:
                nearest_expiry_index = expiry_date_list.index(nearest_expiry_date)
            else:
                raise ValueError
            
            if nearest_expiry_index:
                last_expiry_date = expiry_date_list[nearest_expiry_index - 1]
                first_trading_day = last_expiry_date + timedelta(days=1)
            else:
                last_expiry_date = datetime(nearest_expiry_date.year, 1, 1).date()
                first_trading_day = last_expiry_date 

            while not is_trading_date(date=first_trading_day, trading_platform=self.trading_platform):
                first_trading_day = first_trading_day + timedelta(days=1)
                
            return first_trading_day
        
        except Exception as e:
            logger.critical(f"Error :: get_first_trading_day :: error line {get_exception_line_no()} :: {e}")
         
    def total_number_of_trading_days_in_a_month(self, start_date, end_date):
        try:
            iter_date = end_date
            day_count = 0

            while iter_date >= start_date:
                # use is trading day function
                if is_trading_date(date=iter_date, trading_platform=self.trading_platform):
                # if True:
                    day_count += 1

                iter_date -= timedelta(days=1)

            return day_count

        except Exception as e:
            logger.critical(f"Error :: total_number_of_trading_days_in_a_month :: error line {get_exception_line_no()} :: {e}")
         
    def generate_signal(self, timestamp:datetime):
        try:
            # get the theoretical_dates from the curr_date
            component_expiry_list = self.get_component_expiry_list(timestamp)
            nearest_exp_date = get_unwind_date_for_an_expiry(expiry_date=component_expiry_list[0])

            if self._nearest_expiry != nearest_exp_date:    

                first_trading_day = self.get_first_trading_day(component_expiry_list[0])

                # is_holiday_in_week, holiday_count = is_holiday_in_a_week(start_date=theoretical_dates_start_date, end_date=theoretical_dates_exp_date)
                total_number_of_days_in_month = self.total_number_of_trading_days_in_a_month(start_date=first_trading_day, end_date=nearest_exp_date)

                iter_date = nearest_exp_date
                day_count = 0

                month_signals_dict = {}

                while iter_date >= first_trading_day:
                    # use is trading day function
                    if is_trading_date(date=iter_date, trading_platform=self.trading_platform):
                    # if True:
                        month_signals_dict[iter_date] = day_of_month_signal_frequency.get(day_count)
                        day_count += 1

                    iter_date -= timedelta(days=1)

                logger.info(f"Signal Strength :: start_date={first_trading_day} end_date={nearest_exp_date} signal_vector={month_signals_dict}")
                
                self._monthly_signal_dict = month_signals_dict
                self._nearest_expiry = nearest_exp_date
                
            
            return self._monthly_signal_dict
            
        except Exception as e:
            logger.critical(f"Error :: generate_signal :: error line {get_exception_line_no()} :: {e}")

    def get_day_of_month_signal(self, timestamp: datetime):
        try:
            if self._signal_check_date != timestamp.date():

                signal_strength_dict = self.generate_signal(timestamp=timestamp)
                self._signal_of_the_day = signal_strength_dict.get(timestamp.date())
                self._signal_check_date = timestamp.date()

            return self._signal_of_the_day

        except Exception as e:
            logger.critical(f"Error: get_day_of_month_signal :: error line {get_exception_line_no()} :: {e}")

    def get_component_expiry_list(self, timestamp: datetime):

        theoretical_dates = get_theoretical_date(info_list=expiry_info, current_date=timestamp.date())
        actual_expiry_dates = get_actual_expiry_dates(theoretical_dates_dict=theoretical_dates, trading_platform = self.trading_platform)

        # print(actual_expiry_dates)

        exp_list = []
        for day in actual_expiry_dates.keys():
            # print(i)
            for j, date in enumerate(actual_expiry_dates[day]):
                if date == None:
                    
                    theory_date = theoretical_dates[day][j]
                    self.logger.info(f"{theory_date} ({day}) is not an expiry going for early expiry.")
                    # print(f"{theory_date} ({day}) is not an expiry going for early expiry.")

                    exp_date = get_early_expiry_date(theory_date, timestamp.date(), trading_platform=self.trading_platform, _logger = self.logger)
                    # print(exp_date)
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

    def is_cool_off_period_over(self, current_time: datetime, last_trade_time: datetime, cool_off_period:int):
        if last_trade_time != None:
            is_cool_off_over = ((current_time - last_trade_time).total_seconds() / 60) >= cool_off_period
            
        else:
          is_cool_off_over = True

        return is_cool_off_over

    def generate_trades(self, timestamp: datetime) -> List[Trade]:
        final_trade_list = []
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)
            spot = self.trading_platform.getSpot(timestamp)

            # set trade size based on signal
            trade_interval = self.get_day_of_month_signal(timestamp=timestamp)

            if self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_trade_time, cool_off_period=trade_interval):

                for nearest_expiry_date in component_expiry_list:
                    unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)

                    if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                        self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                        continue
                        # return final_trade_list
                    
                    trade_list = []
                    atm_pe, atm_ce, otm_pe, otm_ce = None, None, None, None
                    
                    # ATM trades
                    atm_pe = get_atm_option(self.trading_platform, self.underlying, spot, "PE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
                    if (atm_pe == None):
                        self.logger.critical(f"ATM PE not found, skipping {self.name}")
                        continue

                    atm_ce = get_atm_option(self.trading_platform, self.underlying, spot, "CE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
                    if atm_ce == None:
                        self.logger.critical(f"ATM CE not found, skipping {self.name}")
                        continue
                    
                    # OTM trades
                    otm_pe = get_static_otm_option(self.trading_platform, self.underlying, atm_pe.strike, self.outstrike, self.steps, self.tolerance, self.strict_tolerance, "PE", nearest_expiry_date, timestamp, self.logger)
                    if otm_pe == None:
                        if self.strict_condor == True:
                            self.logger.critical(f"OTM PE not found, and strict condor is true. skipping {self.name}")
                            continue

                    otm_ce = get_static_otm_option(self.trading_platform, self.underlying, atm_ce.strike, self.outstrike, self.steps, self.tolerance, self.strict_tolerance, "CE", nearest_expiry_date, timestamp, self.logger)
                    if otm_ce == None:
                        if self.strict_condor == True:
                            self.logger.critical(f"OTM CE not found, and strict condor is true. skipping {self.name}")
                            continue

                    if self.unit_size != 0:
                        trade_list.append(Trade(atm_ce, -self.unit_size, "trade"))
                        trade_list.append(Trade(atm_pe, -self.unit_size, "trade"))
                        if otm_ce != None:
                            trade_list.append(Trade(otm_ce, self.unit_size, "trade"))
                        if otm_pe != None:
                            trade_list.append(Trade(otm_pe, self.unit_size, "trade"))
                        
                        self.logger.info(f'{self.name} ATM PE position: {-self.unit_size}, ATM CE position: {-self.unit_size}, OTM PE position: {self.unit_size if otm_ce!=None else 0}, OTM CE position: {self.unit_size if otm_ce!=None else 0}')

                    final_trade_list.extend(trade_list)

            if len(final_trade_list):
                self.last_trade_time = timestamp

                
            return final_trade_list
        except Exception as e:
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e}")
            return final_trade_list