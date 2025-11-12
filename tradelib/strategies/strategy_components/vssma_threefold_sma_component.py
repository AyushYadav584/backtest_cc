from datetime import datetime, date, time, timedelta
from tracemalloc import take_snapshot
from typing import Tuple, List
import copy
import os
from collections import deque
import numpy as np
import csv
from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option, get_static_otm_option, get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date, get_atm_iv
import os
from models.Trade import Trade
from models.Instrument import Instrument
from models.Option import Option
from tradelib_logger import logger,get_exception_line_no
from trading_platform._TradingPlatform import TradingPlatform
from models.OptionDetailed import OptionDetailed
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from tradelib_global_constants import (underlying, tolerance, strict_condor, strict_tolerance, steps, unit_size, unwind_time, expiry_info, gamma_hedge, output_dir_folder, m2m_side,
                                       vssma_iv_threshold_flag, vssma_iv_exit_threshold, 
                                       iv_rv_fast_lookback_period, iv_rv_slow_lookback_period,
                                       iv_rv_signal_tolerance, vssma_threefold_signal_flag, vssma_ignore_rvsma_flag,
                                       vssma_take_profit_flag, vssma_takeprofit_value)
from tradelib_blackscholes_utils import getInstrumentDetailsWithBlackscholes

class VSSMAStraddleThreefoldComponent(StrategyComponent):
    
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, outstrike: float, trade_side, entry_cool_off_time, exit_cool_off_time, signal_strat_time, signal_end_time, signal_tolerance, fast_lookback_period, slow_lookback_period, execute_on_day_start:bool=True) -> None:
        super().__init__("vssma_straddle_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side)
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

        self.signal_tolerance = signal_tolerance
        self.iv_rv_signal_tolerance = iv_rv_signal_tolerance
        self.entry_cool_off_time = timedelta(minutes=entry_cool_off_time)
        self.exit_cool_off_time = timedelta(minutes=exit_cool_off_time)

        self.last_entry_trade_datetime = None
        self.last_exit_trade_datetime = None

        self.slow_lookback_period = slow_lookback_period
        self.fast_lookback_period = fast_lookback_period
        self.iv_rv_slow_lookback_period = iv_rv_slow_lookback_period
        self.iv_rv_fast_lookback_period = iv_rv_fast_lookback_period
        self.vssma_iv_exit_threshold = vssma_iv_exit_threshold
        self.vs_queue = deque(maxlen=self.slow_lookback_period)
        self.iv_queue = deque(maxlen=self.iv_rv_slow_lookback_period)
        self.rv_queue = deque(maxlen=self.iv_rv_slow_lookback_period)
        self.entry_iv = 0
        self.current_portfolio_value = 0
        # attaching expiry should give fexibility to trade condors from different expiries
        # need to think about it. expiry should be handled by unwind component
        # self._expiry = expiry_date

    def get_portolio_state(self) -> int:
        """"
        Returns:
            int: 0 if empty, 1 if in long position, -1 if in short position
        """
        if self.portfolio.is_portfolio_empty():
            return 0
        else:
            total_position = 0
            ins_map = self.portfolio.ins_map
            for key, val in ins_map.items():
                total_position+= val.position
            if total_position > 0:
                return 1
            elif total_position < 0:
                return -1
        return 0
        
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

    def generate_strategy_trades(self, timestamp: datetime, signal : int) -> List[Trade]:
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
                
                trade_list.append(Trade(atm_ce, -self.unit_size*signal, "trade"))
                trade_list.append(Trade(atm_pe, -self.unit_size*signal, "trade"))
                
                self.logger.info(f'{self.name} ATM PE position: {-self.unit_size}, ATM CE position: {-self.unit_size}')

                final_trade_list.extend(trade_list)

            return final_trade_list
        
        except Exception as e:
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e}")
            return final_trade_list

    def generate_closeout_trades(self, timestamp: datetime) -> List[Trade]:
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

    def is_iv_check_ok(self, iv:float) -> bool:
        """
        Check if exit iv is greater than entry iv + vssma_iv_exit_threshold if vssma_iv_threshold_flag is True
        """
        if vssma_iv_threshold_flag:
            if self.entry_iv > (iv + self.vssma_iv_exit_threshold):
                return True
            return False
        return True

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

            if iv == None or rv == None:
                #One of them is None then return the do nothing signal
                logger.warning(f"At time {timestamp} one of {rv=} or {iv=} is None")
                return 0

            vs = iv - rv
            self.vs_queue.appendleft(vs)
            self.iv_queue.appendleft(iv)
            self.rv_queue.appendleft(rv)
            if len(self.vs_queue) < self.slow_lookback_period:
                #If the queue is not fullfiled return the do nothing signal
                logger.warning(f"At time {timestamp} the len of vs_queue {len(list(self.vs_queue))} is less then {self.slow_lookback_period}")
                return 0
            if len(self.iv_queue) < self.iv_rv_slow_lookback_period or len(self.rv_queue) < self.iv_rv_slow_lookback_period:
                #If the queue is not fullfiled return the do nothing signal
                logger.warning(f"At time {timestamp} the len of iv_queue {len(list(self.iv_queue))} or rv_queue {len(list(self.rv_queue))} is less then {self.slow_lookback_period}")
                return 0
            
            #VS SPREAD MOMENTUM
            vs_sma_slow_curr = np.mean(list(self.vs_queue)[:self.slow_lookback_period])
            vs_sma_fast_curr = np.mean(list(self.vs_queue)[:self.fast_lookback_period])
            lower_bound = vs_sma_slow_curr - self.signal_tolerance * abs(vs_sma_slow_curr)
            upper_bound = vs_sma_slow_curr + self.signal_tolerance * abs(vs_sma_slow_curr)

            exit_bool = vs_sma_fast_curr < lower_bound
            entry_bool = vs_sma_fast_curr > upper_bound
            self.logger.info(f" SPANDAN : At time {timestamp} vs_sma_slow_curr: {vs_sma_slow_curr}, vs_sma_fast_curr: {vs_sma_fast_curr}, lower_bound: {lower_bound}, upper_bound: {upper_bound}, exit_bool: {exit_bool}, entry_bool: {entry_bool}")

            #THREEFOLD SMA SIGNAL
            if(vssma_threefold_signal_flag == True):
                iv_sma_slow_curr = np.mean(list(self.iv_queue)[:self.iv_rv_slow_lookback_period])
                iv_sma_fast_curr = np.mean(list(self.iv_queue)[:self.iv_rv_fast_lookback_period])
                rv_sma_slow_curr = np.mean(list(self.rv_queue)[:self.iv_rv_slow_lookback_period])
                rv_sma_fast_curr = np.mean(list(self.rv_queue)[:self.iv_rv_fast_lookback_period])
                self.logger.info(f" SPANDAN : At time {timestamp} iv_slow_curr: {iv_sma_slow_curr}, iv_fast_curr: {iv_sma_fast_curr}, rv_slow_curr: {rv_sma_slow_curr}, rv_fast_curr: {rv_sma_fast_curr}")

                iv_lower_bound = iv_sma_slow_curr  - self.iv_rv_signal_tolerance * abs(iv_sma_slow_curr)
                iv_upper_bound = iv_sma_slow_curr + self.iv_rv_signal_tolerance * abs(iv_sma_slow_curr)
                rv_lower_bound = rv_sma_slow_curr - self.iv_rv_signal_tolerance * abs(rv_sma_slow_curr)
                rv_upper_bound = rv_sma_slow_curr + self.iv_rv_signal_tolerance*abs(rv_sma_slow_curr)

                exit_bool = exit_bool and (iv_sma_fast_curr<iv_lower_bound) and (rv_sma_fast_curr > rv_lower_bound if vssma_ignore_rvsma_flag == False else True)
                entry_bool = entry_bool and (iv_sma_fast_curr > iv_upper_bound) and (rv_sma_fast_curr < rv_upper_bound if vssma_ignore_rvsma_flag == False else True)

            iv_dir = os.path.join(output_dir_folder, "iv_vs_rv")
            os.makedirs(iv_dir, exist_ok=True)
            with open(os.path.join(iv_dir,f"{timestamp.date().strftime('%Y%m%d')}_iv_vs_rv.csv"), 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, iv, rv, vs, vs_sma_slow_curr, vs_sma_fast_curr, lower_bound, upper_bound, exit_bool, entry_bool])
            
            
            if exit_bool==True and entry_bool==False:
                return -1
            # VSSMA_VS_SPREAD OR FLAG : SPANDAN
            elif exit_bool==False and entry_bool==True:
                # If the vs is greater than the threshold then return entry signal depending on vssma_vs_entry_threshold_flag
                return 1

            elif exit_bool==True and entry_bool==True:
                return 0

            elif exit_bool==False and entry_bool==False:
                return 0
            return 0
        except Exception as e:
            logger.critical(f'Error :: get_signal :: line {get_exception_line_no()} :: {e}')
            return 0
    

    def generate_trades(self, timestamp: datetime) -> List[Trade]:
        trade_list = []
        signals_dir = os.path.join(output_dir_folder, "signals")
        os.makedirs(signals_dir, exist_ok=True)
        filepath = os.path.join(signals_dir, f"{timestamp.date().strftime('%Y%m%d')}_signals.csv")
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)
            spot = self.trading_platform.getSpot(timestamp)
            nearest_expiry_date = component_expiry_list[0]

            unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)
            if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                return trade_list
            
            iv =get_atm_iv(trading_platform=self.trading_platform, timestamp=timestamp, _logger=logger)
            rv = self.trading_platform.getRV(timestamp=timestamp)
            signal = self.get_signal(timestamp=timestamp)
            portfolio_state = self.get_portolio_state()
            if signal == 1:
                is_entry_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_exit_trade_datetime, cool_off_period=self.entry_cool_off_time)

                # is_entry_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_entry_trade_datetime, cool_off_period=self.entry_cool_off_time)
                # is_portfolio_empty = self.portfolio.is_portfolio_empty()
                # portfolio_state = self.get_portolio_state()
                is_valid_time = self.is_valid_time_to_trade(timestamp=timestamp, is_entry=True)
                with open(filepath, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, "SHORT SIGNAL", signal, portfolio_state, is_entry_cool_off_over, is_valid_time,iv,rv])
                if is_entry_cool_off_over and (portfolio_state == 0) and is_valid_time:
                    with open(filepath, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([timestamp, "SHORT TRADE", signal, portfolio_state, is_entry_cool_off_over, is_valid_time,iv,rv])
                    self.last_entry_trade_datetime = timestamp
                    trade_list = self.generate_strategy_trades(timestamp, signal)
                    self.entry_iv = iv
                    self.current_portfolio_value =  self.portfolio.getPortfolioValue(timestamp,m2m_side)
                
            #Take Profit or Stop Loss
            elif(vssma_take_profit_flag == True and (self.portfolio.getPortfolioValue(timestamp,m2m_side))>= (self.current_portfolio_value + vssma_takeprofit_value*self.trading_platform.getSpot(timestamp)*unit_size*2/100) and (portfolio_state == -1)):
                is_valid_time = self.is_valid_time_to_trade(timestamp=timestamp, is_entry=False)
                with open(filepath, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, "STOP LOSS", 100, portfolio_state, "STOP LOSS NO COOLOFF", is_valid_time,iv,rv])
                self.last_exit_trade_datetime = timestamp
                trade_list = self.generate_closeout_trades(timestamp)
                # return trade_list
            
            elif signal == -1:
                is_exit_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_entry_trade_datetime, cool_off_period=self.exit_cool_off_time)
                 
                # is_exit_cool_off_over = self.is_cool_off_period_over(current_time=timestamp, last_trade_time=self.last_exit_trade_datetime, cool_off_period=self.exit_cool_off_time)
                # is_portfolio_empty = self.portfolio.is_portfolio_empty()
                # portfolio_state = self.get_portolio_state()
                is_valid_time = self.is_valid_time_to_trade(timestamp=timestamp, is_entry=False)
                iv_check_ok  = self.is_iv_check_ok(iv=iv)
                with open(filepath, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, "LONG SIGNAL", signal, portfolio_state, is_exit_cool_off_over, is_valid_time,iv,rv])
                                                                                            #IV ENTRY> IV EXIT
                if is_exit_cool_off_over and (portfolio_state == -1) and is_valid_time and iv_check_ok:
                    with open(filepath, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([timestamp, "CLOSEOUT", signal, portfolio_state, is_exit_cool_off_over, is_valid_time,iv,rv])
                    self.last_exit_trade_datetime = timestamp
                    trade_list = self.generate_closeout_trades(timestamp)
                
                
            else:
                trade_list = []
            return trade_list

        except Exception as e:
            logger.critical(f"Error :: generate_trades :: line {get_exception_line_no()} :: {e}")
            return trade_list