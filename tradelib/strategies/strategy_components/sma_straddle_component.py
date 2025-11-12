from datetime import datetime, date, time, timedelta
from typing import Tuple, List
import copy
from collections import deque
import numpy as np
import pandas as pd
import talib

from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option, get_static_otm_option, get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date, get_atm_iv, get_delta_based_otm_option

from models.Trade import Trade
from models.Instrument import Instrument
from models.Option import Option
from tradelib_logger import logger,get_exception_line_no
from trading_platform._TradingPlatform import TradingPlatform
from models.OptionDetailed import OptionDetailed
from models.Portfolio import Portfolio
from models.Blotter import Blotter

from tradelib_global_constants import underlying, tolerance, strict_condor, strict_tolerance, steps, unit_size, unwind_time, expiry_info, gamma_hedge, sma_daily_entry_limit, m2m_side, is_take_profit, is_stop_loss, take_profit_threshold, stop_loss_threshold

from tradelib_blackscholes_utils import getInstrumentDetailsWithBlackscholes

class SMAStraddleComponent(StrategyComponent):
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, outstrike: float, trade_side, entry_cool_off_time, exit_cool_off_time, signal_strat_time, signal_end_time, signal_tolerance, fast_lookback_period, slow_lookback_period, signal_window, signal_upper, signal_lower, signal_variable, execute_on_day_start:bool=True, contract_quota: int = None) -> None:
        super().__init__("sma_straddle_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side, contract_quota)
        self.outstrike = outstrike
        self.tolerance = tolerance
        self.strict_condor = strict_condor
        self.strict_tolerance = strict_tolerance
        self.steps = steps
        self.underlying = underlying
        self.unit_size = unit_size
        self.unwind_time = unwind_time

        self.signal_strat_time = signal_strat_time
        self.signal_end_time = signal_end_time

        self.entry_cool_off_time = timedelta(minutes=entry_cool_off_time)
        self.exit_cool_off_time = timedelta(minutes=exit_cool_off_time)

        self.last_entry_trade_datetime = None
        self.last_exit_trade_datetime = None
        self.last_trade_datetime = None

        # for cross over strategy
        self.signal_tolerance = signal_tolerance
        self.slow_lookback_period = slow_lookback_period
        self.fast_lookback_period = fast_lookback_period

        # for thresold strategy
        self.signal_window = signal_window
        self.signal_upper = signal_upper
        self.signal_lower = signal_lower

        # select the timeseries on which you add tecnical indicator
        self.signal_variable = signal_variable

        # self.vs_queue = deque(maxlen=self.signal_window+1)
        # self.iv_queue = deque(maxlen=self.signal_window+1)
        # # self.rv_queue = deque(maxlen=self.slow_lookback_period)
        # # self.spot_queue = deque(maxlen=self.slow_lookback_period)
        # self.vr_queue = deque(maxlen=self.signal_window+1)

        self.vs_queue = deque(maxlen=self.slow_lookback_period)
        self.iv_queue = deque(maxlen=self.slow_lookback_period)
        self.vr_queue = deque(maxlen=self.slow_lookback_period)

        # attaching expiry should give fexibility to trade condors from different expiries
        # need to think about it. expiry should be handled by unwind component
        # self._expiry = expiry_date

        self.prev_signal = None

        self.max_daily_trade = sma_daily_entry_limit
        self.init_contract_quota = contract_quota

    def reinitailse_on_day_start(self):
        self._time_skip_counter = self._time_skip_count if self.execute_on_day_start else 0
        self.max_daily_trade = sma_daily_entry_limit
        self.prev_signal = None

        # These queue should be reinitialized but P/L is less with reinitialized
        # self.vs_queue = deque(maxlen=self.signal_window+1)
        # self.iv_queue = deque(maxlen=self.signal_window+1)
        # self.vr_queue = deque(maxlen=self.signal_window+1)

        # Cross over
        self.vs_queue = deque(maxlen=self.slow_lookback_period)
        self.iv_queue = deque(maxlen=self.slow_lookback_period)
        self.vr_queue = deque(maxlen=self.slow_lookback_period)

        self.portfolio.reinitailse_morning_cash_on_day_start(self.portfolio.getPortfolioValue(timestamp=None, m2m_side=m2m_side))

    
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

    def generate_entry_trades(self, timestamp: datetime) -> List[Trade]:
        final_trade_list = []
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)
            spot = self.trading_platform.getSpot(timestamp)

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
                
                trade_list.append(Trade(atm_ce, -self.unit_size, "trade"))
                trade_list.append(Trade(atm_pe, -self.unit_size, "trade"))
                
                self.logger.info(f'{self.name} ATM PE position: {-self.unit_size}, ATM CE position: {-self.unit_size}')

                final_trade_list.extend(trade_list)

            if (len(final_trade_list) != 0) and (self.max_daily_trade > 0):
                self.max_daily_trade -= 1
                return final_trade_list
            
            else:
                return []
            
        
        except Exception as e:
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e}")
            return final_trade_list

    def generate_trades_based_on_signal(self, timestamp: datetime, signal:int) -> List[Trade]:
        final_trade_list = []
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)
            spot = self.trading_platform.getSpot(timestamp)

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
                
                if signal == -1:
                    trade_list.append(Trade(atm_ce, -self.unit_size, "trade"))
                    trade_list.append(Trade(atm_pe, -self.unit_size, "trade"))
                
                    self.logger.info(f'{self.name} ATM PE position: {-self.unit_size}, ATM CE position: {-self.unit_size}')

                if signal == 1:
                    trade_list.append(Trade(atm_ce, self.unit_size, "trade"))
                    trade_list.append(Trade(atm_pe, self.unit_size, "trade"))
                
                    self.logger.info(f'{self.name} ATM PE position: {self.unit_size}, ATM CE position: {self.unit_size}')

                final_trade_list.extend(trade_list)

            if (len(final_trade_list) != 0) and (self.max_daily_trade > 0):
                self.max_daily_trade -= 1
                return final_trade_list
            
            else:
                return []
            
        
        except Exception as e:
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e}")
            return final_trade_list

    def generate_exit_trades(self, timestamp: datetime) -> List[Trade]:
        trade_list: List[Trade] = []
        for key, val in self.portfolio.ins_map.items():
            ins: Instrument = val.instrument
            position = val.position
            if ins.instrument_type == "option":
                ins: Option = ins

                try:
                    insDetailed = getInstrumentDetailsWithBlackscholes(ins, timestamp, self.trading_platform, self.logger)
                    trade_list.append(Trade(insDetailed, -position, 'unwind'))
                    self.logger.info(f'{self.name} Trade idkey: {insDetailed.idKey()}, position: {-position}')
                except Exception as e:
                    self.logger.info(e)

        if len(trade_list):
            self.set_contract_quota(contract_quota=self.init_contract_quota)
        
        return trade_list

    def is_cool_off_period_over(self, current_time: datetime, last_trade_time: datetime, cool_off_period:int):
        if last_trade_time != None:
            is_cool_off_over =  current_time - last_trade_time > cool_off_period
        else:
          is_cool_off_over = True

        return is_cool_off_over

    def is_valid_time_to_trade(self, timestamp: datetime, is_entry:bool):
        try:
            c1 = timestamp.time() < self.unwind_time
            c2 = timestamp.time() >= self.signal_strat_time
            c3 = timestamp.time() <= self.signal_end_time if is_entry else True

            return c1 and c2 and c3
        except Exception as e:
            logger.critical(f"Error in is_valid_time_to_trade {get_exception_line_no()} :: {e}")

    def take_profit_signal(self, portfolio_value, take_profit_threshold):
        return portfolio_value >= take_profit_threshold

    def stop_loss_signal(self, portfolio_value, stop_loss_threshold):
        return portfolio_value <= stop_loss_threshold

    def get_signal(self, timestamp: datetime):
        """
        1: Entry
        -1: Exit
        0: do nothing

        Args:
            timestamp (datetime): _description_
        """
        try:
            iv = get_atm_iv(trading_platform=self.trading_platform, timestamp=timestamp, _logger=logger)
            rv = self.trading_platform.getRV(timestamp=timestamp)

            # stop loss and take profit
            p_value = self.portfolio.getPortfolioValue(timestamp=timestamp, m2m_side=m2m_side)
            morning_cash = self.portfolio.getMorningCash()
            daily_portfolio_value = p_value - morning_cash

            # take profit
            if is_take_profit and self.take_profit_signal(portfolio_value=daily_portfolio_value, take_profit_threshold=take_profit_threshold):
                logger.info(f"{timestamp},ZT100,take_profit,{daily_portfolio_value},{take_profit_threshold},{p_value},{morning_cash}")
                return -2

            # stop loss
            if is_stop_loss and self.stop_loss_signal(portfolio_value=daily_portfolio_value, stop_loss_threshold=stop_loss_threshold):
                logger.info(f"{timestamp},ZT100,stop_loss,{daily_portfolio_value},{stop_loss_threshold},{p_value},{morning_cash}")
                return -2

            # Storing the queues based on signal variables
            if ((self.signal_variable == 'vs') or (self.signal_variable == 'vr')):
                if iv == None or rv == None:
                    #One of them is None then return the do nothing signal
                    logger.warning(f"At time {timestamp} one of {rv=} or {iv=} is None")
                    return 0
                else:
                    vs = iv - rv
                    vr = iv/rv
                    self.vs_queue.appendleft(vs)
                    self.vr_queue.appendleft(vr)
                
            elif (self.signal_variable == 'iv'):
                if iv == None:
                    #One of them is None then return the do nothing signal
                    logger.warning(f"At time {timestamp} {iv=} is None")
                    return 0
                else:
                    self.iv_queue.appendleft(iv)


            if self.signal_variable == 'vs':
                sma_input = self.vs_queue
            elif self.signal_variable == 'vr':
                sma_input = self.vr_queue
            elif self.signal_variable == 'iv':
                sma_input = self.iv_queue
            
            ### SIMPLE THRESOLD
            # if len(sma_input) <= (self.signal_window):
            #     #If the queue is not fullfiled return the do nothing signal
            #     logger.warning(f"At time {timestamp} the len of {self.signal_variable} queue {len(list(sma_input))} is less then equal to {self.signal_window = }")
            #     return 0
            
            # sma_list = talib.SMA(np.array(list(sma_input)[::-1], dtype=np.float64), timeperiod=self.signal_window)
            # sma_val = sma_list[-1]
            # logger.info(f"At time {timestamp} for SMA input {sma_input} {sma_list=} {sma_val=} {self.signal_upper=} {self.signal_lower=}")

            # if sma_val is None:
            #     logger.warning(f"At time {timestamp} SMA val is None for SMA input {sma_input} {sma_val=} {self.signal_upper=} {self.signal_lower=}")
            #     return 0 

            # exit_bool = sma_val < self.signal_lower
            # entry_bool = sma_val > self.signal_upper


            ### CROSS OVER
            if len(sma_input) < self.slow_lookback_period:
                #If the queue is not fullfiled return the do nothing signal
                logger.warning(f"At time {timestamp} the len of sma_input {len(list(sma_input))} is less then {self.slow_lookback_period}")
                return 0
            
            sma_slow_curr = np.mean(list(sma_input)[:self.slow_lookback_period])
            sma_fast_curr = np.mean(list(sma_input)[:self.fast_lookback_period])

            lower_bound = sma_slow_curr - self.signal_tolerance * abs(sma_slow_curr)
            upper_bound = sma_slow_curr + self.signal_tolerance * abs(sma_slow_curr)

            # Currect
            exit_bool = sma_fast_curr < lower_bound #-1
            entry_bool = sma_fast_curr > upper_bound #+1


            # logger.info(f"SMA_SIGNAL,{timestamp},{sma_slow_curr},{sma_fast_curr},{self.slow_lookback_period},{self.fast_lookback_period},{exit_bool},{entry_bool}")

            if exit_bool==True and entry_bool==False:
                if self.prev_signal == -1:
                    logger.info(f"SMA_SIGNAL,{timestamp},{sma_slow_curr},{sma_fast_curr},{self.slow_lookback_period},{self.fast_lookback_period},{exit_bool},{entry_bool},{self.prev_signal},-1,0")
                    return 0
                else:
                    logger.info(f"SMA_SIGNAL,{timestamp},{sma_slow_curr},{sma_fast_curr},{self.slow_lookback_period},{self.fast_lookback_period},{exit_bool},{entry_bool},{self.prev_signal},-1,-1")

                    self.prev_signal = -1
                    return -1

            elif exit_bool==False and entry_bool==True:
                if self.prev_signal == 1:
                    logger.info(f"SMA_SIGNAL,{timestamp},{sma_slow_curr},{sma_fast_curr},{self.slow_lookback_period},{self.fast_lookback_period},{exit_bool},{entry_bool},{self.prev_signal},1,0")
                    return 0
                else:
                    logger.info(f"SMA_SIGNAL,{timestamp},{sma_slow_curr},{sma_fast_curr},{self.slow_lookback_period},{self.fast_lookback_period},{exit_bool},{entry_bool},{self.prev_signal},1,1")

                    self.prev_signal = 1
                    return 1

            elif exit_bool==True and entry_bool==True:
                return 0

            elif exit_bool==False and entry_bool==False:
                return 0

        except Exception as e:
            logger.critical(f'Error :: get_signal :: line {get_exception_line_no()} :: {e}')
            return 0
    

    def generate_trades(self, timestamp: datetime) -> List[Trade]:
        trade_list = []
        unwind_trade_list = []
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)
            spot = self.trading_platform.getSpot(timestamp)
            nearest_expiry_date = component_expiry_list[0]

            unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)
            if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                return trade_list

            signal = self.get_signal(timestamp=timestamp)

            if signal == 1:
                # is_entry_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_exit_trade_datetime, cool_off_period=self.entry_cool_off_time)
                is_entry_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_trade_datetime, cool_off_period=self.entry_cool_off_time)

                is_portfolio_empty = self.portfolio.is_portfolio_empty()
                is_valid_time = self.is_valid_time_to_trade(timestamp=timestamp, is_entry=True)

                logger.info(f"At time {timestamp} is_entry_cool_off_over = {is_entry_cool_off_over} {is_portfolio_empty = } {is_valid_time = }")

                # if is_entry_cool_off_over and is_portfolio_empty and is_valid_time:
                if is_entry_cool_off_over and is_valid_time:
                    # self.last_entry_trade_datetime = timestamp
                    self.last_trade_datetime = timestamp

                    if not is_portfolio_empty:
                        unwind_trade_list = self.generate_exit_trades(timestamp)

                    trade_list = self.generate_trades_based_on_signal(timestamp,signal=signal)

                    trade_list.extend(unwind_trade_list)
                    # trade_list = self.generate_entry_trades(timestamp)

                if self.init_contract_quota is not None:    
                    if (len(trade_list) != 0) and self.contract_quota>0:
                        self.contract_quota -= 1

                    else:
                        trade_list = []
                    

            elif signal == -1:
                # is_exit_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_entry_trade_datetime, cool_off_period=self.exit_cool_off_time)
                is_exit_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_trade_datetime, cool_off_period=self.exit_cool_off_time)

                # is_exit_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_exit_trade_datetime, cool_off_period=self.exit_cool_off_time)
                is_portfolio_empty = self.portfolio.is_portfolio_empty()
                is_valid_time = self.is_valid_time_to_trade(timestamp=timestamp, is_entry=False)

                logger.info(f"At time {timestamp} is_exit_cool_off_over = {is_exit_cool_off_over} {is_portfolio_empty = } {is_valid_time = }")
                # if is_exit_cool_off_over and not is_portfolio_empty and is_valid_time:
                if is_exit_cool_off_over and is_valid_time:
                    # self.last_exit_trade_datetime = timestamp
                    self.last_trade_datetime = timestamp
                    # trade_list = self.generate_exit_trades(timestamp)

                    if not is_portfolio_empty:
                        unwind_trade_list = self.generate_exit_trades(timestamp)

                    trade_list = self.generate_trades_based_on_signal(timestamp,signal=signal)

                    trade_list.extend(unwind_trade_list)

            elif signal == -2:
                is_portfolio_empty = self.portfolio.is_portfolio_empty()
                is_valid_time = self.is_valid_time_to_trade(timestamp=timestamp, is_entry=False)

                if not is_portfolio_empty and is_valid_time:
                # if is_exit_cool_off_over and is_valid_time:
                    # self.last_exit_trade_datetime = timestamp
                    trade_list = self.generate_exit_trades(timestamp)
                    # trade_list = self.generate_trades_based_on_signal(timestamp,signal=signal)

            else:
                trade_list = []

            return trade_list



        except Exception as e:
            logger.critical(f"Error :: generate_trades :: line {get_exception_line_no()} :: {e}")
            return trade_list
        

