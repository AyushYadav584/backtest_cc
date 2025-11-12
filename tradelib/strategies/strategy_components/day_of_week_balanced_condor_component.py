'''
This is the trade generator model
'''

from datetime import datetime, date, time, timedelta
from typing import Tuple, List
import copy

from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry, is_holiday_in_a_week
from tradelib_trade_utils import *

from models.Trade import Trade
from tradelib_logger import logger,get_exception_line_no
from trading_platform._TradingPlatform import TradingPlatform
from models.OptionDetailed import OptionDetailed
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from tradelib_global_constants import *

class DayofWeekBalancedCondorComponent(StrategyComponent):
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, delta_outstrike: float, tolerance: int, strict_condor:bool, strict_tolerance: bool, underlying:str, unit_size:int, unwind_time, trade_side, execute_on_day_start:bool=True ) -> None:
        super().__init__("day_of_week_balanced_condor_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side)

        self.delta_outstrike = delta_outstrike
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

        # attaching expiry should give fexibility to trade condors from different expiries
        # need to think about it. expiry should be handled by unwind component
        # self._expiry = expiry_date

    def total_number_of_trading_days_in_a_week(self, start_date, end_date):
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
            logger.critical(f"Error :: total_number_of_trading_days_in_a_week :: error line {get_exception_line_no()} :: {e}")
         
    def generate_signal(self, timestamp:datetime):
        try:
            return day_of_week_signal_strength
            # get the theoretical_dates from the curr_date
            theoretical_dates = get_theoretical_date(info_list=expiry_info, current_date=timestamp.date())
            exp_day = expiry_info[0][0]
            # theoretical_dates = {'Thursday': [date(2023, 9, 7)]}

            theoretical_dates_exp_date = theoretical_dates.get(exp_day)[0]
            # theoretical_dates_exp_date = theoretical_dates.get('Thursday')[0]
            theoretical_dates_start_date = theoretical_dates_exp_date-timedelta(days=6)

            # is_holiday_in_week, holiday_count = is_holiday_in_a_week(start_date=theoretical_dates_start_date, end_date=theoretical_dates_exp_date)
            total_number_of_days_in_week = self.total_number_of_trading_days_in_a_week(start_date=theoretical_dates_start_date, end_date=theoretical_dates_exp_date)

            if total_number_of_days_in_week == 5:
                logger.info(f"Signal Strength :: start_date={theoretical_dates_start_date} end_date={theoretical_dates_exp_date} signal_vector={day_of_week_signal_strength}")
                return day_of_week_signal_strength

            else:
                start_date = theoretical_dates_start_date
                # total_number_of_days_in_week = 5
                # total_number_of_days_in_week = self.total_number_of_trading_days_in_a_week(start_date=theoretical_dates_start_date, end_date=theoretical_dates_exp_date)
                week_signals = {}

                while start_date <= theoretical_dates_exp_date:

                    if start_date.weekday() in [5, 6]:
                        start_date += timedelta(days=1)
                        continue

                    if is_trading_date(date=start_date, trading_platform=self.trading_platform):
                    # if True:
                        if total_number_of_days_in_week > 0:
                            week_signals[start_date.weekday()] = day_of_week_signal_strength[start_date.weekday()]

                            total_number_of_days_in_week -= day_of_week_signal_strength[start_date.weekday()]
                        else:
                            week_signals[start_date.weekday()] = 0

                    else:
                        week_signals[start_date.weekday()] = 0

                    start_date += timedelta(days=1)

                logger.info(f"Signal Strength :: start_date={theoretical_dates_start_date} end_date={theoretical_dates_exp_date} signal_vector={week_signals}")
                return week_signals

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
        current_time = timestamp.time()
        if delta_condor_trade_stop_time < current_time or current_time < delta_condor_trade_start_time:
            return final_trade_list

        
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)
            spot = self.trading_platform.getSpot(timestamp)

            # set trade size based on signal
            trade_mul = self.get_day_of_week_signal(timestamp=timestamp)
            unit_size = self.unit_size * trade_mul

            for nearest_expiry_date in component_expiry_list:
                unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)

                if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                    self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                    continue
                    # return final_trade_list

                options_pair = find_options_with_target_premium(
                    trading_platform=self.trading_platform,
                    underlying=self.underlying,
                    target_price=target_option_premium_sum,
                    expiry_date=nearest_expiry_date,
                    timestamp=timestamp,
                    logger=self.logger
                )

                if not options_pair:
                    self.logger.warning(f"{self.name} No suitable options found for target premium sum")
                    continue
                
                call_option, put_option = options_pair

                trade_list = []
                # atm_pe, atm_ce, otm_pe, otm_ce = None, None, None, None
                
                # # Used to calculate moneyness based on prices from PE and CE options of the same delta to avoid P/C imbalance 
                # delta_pe = get_delta_based_otm_option(self.trading_platform, self.underlying, delta_atm_outstrike, self.tolerance, self.strict_tolerance, "PE", nearest_expiry_date, timestamp, self.logger)
                # if (delta_pe == None):
                #     self.logger.critical(f"ATM PE not found, skipping {self.name}")
                #     continue

                # delta_ce = get_delta_based_otm_option(self.trading_platform, self.underlying, delta_atm_outstrike, self.tolerance, self.strict_tolerance, "CE", nearest_expiry_date, timestamp, self.logger)
                # if delta_ce == None:
                #     self.logger.critical(f"ATM CE not found, skipping {self.name}")
                #     continue
                
                # pe_moneyness = abs(delta_pe.strike/spot-1)
                # ce_moneyness = abs(delta_ce.strike/spot-1)
                # balanced_outstrike = (ce_moneyness+pe_moneyness)/2
                
                # print(balanced_outstrike)

                # balance = (delta_ce.mid + delta_pe.mid)/2

                # unbalance_ce = 2*delta_ce.mid - balance
                # unbalance_pe = 2*delta_pe.mid - balance
                
                # balanced_pe = get_static_otm_option_by_price(
                #     trading_platform=self.trading_platform,
                #     underlying=self.underlying,
                #     target_price=unbalance_ce,
                #     tolerance=100000,  # max allowed difference from target price
                #     strict_tolerance=True,
                #     opt_type="PE",
                #     nearest_expiry_date=nearest_expiry_date,
                #     timestamp=timestamp,
                #     _logger=self.logger
                # )

                # balanced_ce = get_static_otm_option_by_price(
                #     trading_platform=self.trading_platform,
                #     underlying=self.underlying,
                #     target_price=unbalance_pe,
                #     tolerance=100000,
                #     strict_tolerance=True,
                #     opt_type="CE",
                #     nearest_expiry_date=nearest_expiry_date,
                #     timestamp=timestamp,
                #     _logger=self.logger
                # )

                # print('Balanced PE, CE:', balanced_ce.strike, balanced_pe.strike)
                
                # Uses the balanced outstrike calculated above 
                # balanced_pe = get_static_otm_option(self.trading_platform, self.underlying, atm_pe.strike, balanced_outstrike, self.steps, self.tolerance, self.strict_tolerance, "PE", nearest_expiry_date, timestamp, self.logger)
                # if balanced_pe == None:
                #     self.logger.critical(f"OTM PE not found, and strict condor is true. skipping {self.name}")
                #     continue

                # balanced_ce = get_static_otm_option(self.trading_platform, self.underlying, atm_ce.strike, balanced_outstrike, self.steps, self.tolerance, self.strict_tolerance, "CE", nearest_expiry_date, timestamp, self.logger)
                # if balanced_ce == None:
                #     self.logger.critical(f"OTM CE not found, and strict condor is true. skipping {self.name}")
                #     continue

                if unit_size != 0:
                    trade_list.append(Trade(call_option, -unit_size, "trade"))
                    trade_list.append(Trade(put_option, -unit_size, "trade"))
                    # if otm_ce != None:
                    #     trade_list.append(Trade(otm_ce, unit_size, "trade"))
                    # if otm_pe != None:
                    #     trade_list.append(Trade(otm_pe, unit_size, "trade"))
                    
                    # self.logger.info(f'{self.name} ATM PE position: {-unit_size}, ATM CE position: {-unit_size}, OTM PE position: {unit_size if otm_ce!=None else 0}, OTM CE position: {unit_size if otm_ce!=None else 0}')
                    
                    self.logger.info(f'{self.name} Call Option Strike: {call_option.strike}, Put Option Strike: {put_option.strike}, Unit Size: {unit_size}')

                    # self.logger.info(f'{self.name} ATM PE position: {-unit_size}, ATM CE position: {-unit_size}')

                final_trade_list.extend(trade_list)

            return final_trade_list
        except Exception as e:
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e}")
            return final_trade_list