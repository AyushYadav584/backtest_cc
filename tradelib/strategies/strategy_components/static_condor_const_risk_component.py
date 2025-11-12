# # WORK HALTED DUE TO ALGO NOT BEING FINALISED

from strategies.strategy_components import StrategyComponent
from trading_platform import TradingPlatform
from models.Blotter import Blotter
from models.Portfolio import Portfolio
from models.Trade import Trade
from models.Instrument import Instrument
from models.Option import Option
# from models.MutableNumber import MutableNumber
from datetime import time, datetime
from typing import List
from tradelib_blackscholes_utils import getInstrumentDetailsWithBlackscholes

import numpy as np

from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry, round_to_lot_size, get_exception_line_no, get_options_intraday_filename_2, is_file_exist
from tradelib_trade_utils import get_atm_option, get_static_otm_option, get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date
from tradelib_global_constants import underlying, tolerance, strict_condor, strict_tolerance, steps, unit_size, unwind_time, expiry_info, exchange_end_time
from tradelib_global_constants import rampup_period, total_trade_time_in_day, trade_interval_time, rampup_days, option_legs, unit_size, rollover_period, non_rollover_period, expiry_weight_vector

class ConstantRiskStaticCondorComponent(StrategyComponent):
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, outstrike: float, tolerance: float, strict_condor: bool, strict_tolerance: bool, unwind_time:time, execute_on_day_start:bool=True) -> None:
        super().__init__("constant_risk_static_condor_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start)

        self.outstrike = outstrike
        self.tolerance = tolerance
        self.strict_condor = strict_condor
        self.strict_tolerance = strict_tolerance
        self.steps = trading_platform.steps
        self.underlying = trading_platform.underlying
        self.unit_size = trading_platform.unit_size
        self.unwind_time = unwind_time
        # self.nearest_expiries_num = nearest_expiries_num

        self.is_rampup = True
        self.rampup_period = rampup_period  # Total backtest time (9:20 to 3:30) = 375 min * 3 (No of days of ramup)
        self.rampup_expiry_trade_vector = None

        self.rollover_expiry_index = 1
        self.contract_budget = (total_trade_time_in_day / trade_interval_time) * rampup_days * (expiry_info[0][1] * option_legs * unit_size)  # (Total backtest time in one day / Trade_interval) * (No. of rampup days) * (No. of expiry * condor(4 trades) * lot_size)
        self.contract_budget_iterator = 0

        self.rollover_period = rollover_period # 375 * 2
        # self.rollover_time = 375 * 2
        self.rollover_period_iterator = 0

        self.trades_to_roll_per_trade_time = 0
        self.expiry_count = self.number_of_expiry_from_expiry_info(expiry_info)

        self.non_rollover_period = non_rollover_period # 375 * 3
        self.non_rollover_period_iterator = 0
        self.curr_non_rollover_expiry = 0
        self.trades_to_non_rollover_per_trade_time = None # np array
        self.non_rollover_info = np.zeros(self.expiry_count)
        self.is_non_rollover = True
        self.is_non_rollover_info_time = True

        self.curr_roll_over_expiry = 0

        self.expiry_weight_vector = expiry_weight_vector # np.array([0.5, 0.5])
        self.total_contract_tracker = 0
        self.near_week_trades = 0
        # self.

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

    def set_rampup_info(self):
        self.rampup_expiry_trade_vector = self.contract_budget * self.expiry_weight_vector / (self.rampup_period / trade_interval_time) / option_legs # 5 for trade_interval and 4 for condor

    def rampup_trades(self, timestamp):
        try:
            final_trade_list = []

            component_expiry_list = (self.get_component_expiry_list(timestamp))
            spot = self.trading_platform.getSpot(timestamp)
            self.logger.info(f"The component expiry list = {component_expiry_list}")

            if np.any(self.rampup_expiry_trade_vector == None):
                self.set_rampup_info()

            rampup_expiry_trade_vector = self.rampup_expiry_trade_vector.tolist()

            for i, nearest_expiry_date in enumerate(component_expiry_list):
                unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)

                if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                    self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                    continue
                    # return final_trade_list
                        
                trade_list = []
                atm_pe, atm_ce, otm_pe, otm_ce = None, None, None, None
                
                self.logger.debug(f"for expiry {nearest_expiry_date}")
                # ATM trades
                # self.logger.info(f"Going for ATM PE")
                atm_pe = get_atm_option(self.trading_platform, self.underlying, spot, "PE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
                if (atm_pe == None):
                    self.logger.critical(f"ATM PE not found, skipping {self.name}, trading expiry = {component_expiry_list[0]} in place of expiry = {nearest_expiry_date}")
                    # component_expiry_list.append(component_expiry_list[0])
                    # rampup_expiry_trade_vector.append(rampup_expiry_trade_vector[i])
                    continue

                # self.logger.info(f"Going for ATM CE")
                atm_ce = get_atm_option(self.trading_platform, self.underlying, spot, "CE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
                if atm_ce == None:
                    self.logger.critical(f"ATM CE not found, skipping {self.name}, trading expiry = {component_expiry_list[0]} in place of expiry = {nearest_expiry_date}")
                    # component_expiry_list.append(component_expiry_list[0])
                    # rampup_expiry_trade_vector.append(rampup_expiry_trade_vector[i])
                    continue
                
                # OTM trades
                # self.logger.info(f"Going for OTM PE")
                otm_pe = get_static_otm_option(self.trading_platform, self.underlying, atm_pe.strike, self.outstrike, self.steps, self.tolerance, self.strict_tolerance, "PE", nearest_expiry_date, timestamp, self.logger)
                if otm_pe == None:
                    if self.strict_condor == True:
                        self.logger.critical(f"OTM PE not found, and strict condor is true. skipping {self.name}, trading expiry = {component_expiry_list[0]} in place of expiry = {nearest_expiry_date}")
                        # component_expiry_list.append(component_expiry_list[0])
                        # rampup_expiry_trade_vector.append(rampup_expiry_trade_vector[i])
                        continue

                # self.logger.info(f"Going for OTM CE")
                otm_ce = get_static_otm_option(self.trading_platform, self.underlying, atm_ce.strike, self.outstrike, self.steps, self.tolerance, self.strict_tolerance, "CE", nearest_expiry_date, timestamp, self.logger)
                if otm_ce == None:
                    if self.strict_condor == True:
                        self.logger.critical(f"OTM CE not found, and strict condor is true. skipping {self.name},  trading expiry = {component_expiry_list[0]} in place of expiry = {nearest_expiry_date}")
                        # component_expiry_list.append(component_expiry_list[0])
                        # rampup_expiry_trade_vector.append(rampup_expiry_trade_vector[i])
                        continue

                rampup_trade_size = round_to_lot_size(rampup_expiry_trade_vector[i], self.trading_platform.unit_size)
                
                trade_list.append(Trade(atm_ce, -rampup_trade_size, 'trade'))
                trade_list.append(Trade(atm_pe, -rampup_trade_size, 'trade'))
                if otm_ce != None:
                    trade_list.append(Trade(otm_ce, rampup_trade_size, 'trade'))
                if otm_pe != None:
                    trade_list.append(Trade(otm_pe, rampup_trade_size, 'trade'))
                
                self.logger.info(f'{self.name} ATM PE position: {-rampup_trade_size}, ATM CE position: {-rampup_trade_size}, OTM PE position: {rampup_trade_size if otm_ce!=None else 0}, OTM CE position: {rampup_trade_size if otm_ce!=None else 0}')

                # self.logger.info(f'{trade_list}')
                self.total_contract_tracker += 4*abs(rampup_trade_size)
                self.logger.debug(f"Total contracts in portfolio = {self.total_contract_tracker} at {timestamp = } in rampup")

                if nearest_expiry_date == component_expiry_list[0]:
                    self.near_week_trades += 4*abs(rampup_trade_size)
                    self.logger.debug(f"{timestamp = }, {self.near_week_trades = }")

                final_trade_list.extend(trade_list)

            return final_trade_list
        
        except Exception as e:
            final_trade_list = []
            self.logger.critical(f"error while executing skipping {self.name}. {e} :: {get_exception_line_no()}")
            return final_trade_list

    def get_next_rollover_expiry_index(self, expiry_list_length):
        current_rollover_expiry_index = self.rollover_expiry_index

        self.rollover_expiry_index += 1

        if self.rollover_expiry_index == expiry_list_length:
            self.rollover_expiry_index = 1
        
        return current_rollover_expiry_index

    def set_roll_over_info(self, nearest_expiry):
        total_contract_after_rampup = 0

        for key, val in self.portfolio.ins_map.items():
            ins: Instrument = val.instrument
            position = val.position
            if ins.instrument_type == "option":
                ins: Option = ins
                if (ins.expiry == nearest_expiry):
                    total_contract_after_rampup += abs(position)

            self.trades_to_roll_per_trade_time = (total_contract_after_rampup / (self.rollover_period / trade_interval_time)) / option_legs # 5-> trade_interval, 4->legs in condor


        self.logger.debug(f"Total Number of trades after rampup/nonrollover {total_contract_after_rampup}")


    def get_non_rollover_trade_size(self, adjust_vector:list) -> np.array:
         # amount to adjust in contracts in non rollover period
        trading_time_rollover = self.non_rollover_period / trade_interval_time # trade_intervals

        self.trades_to_non_rollover_per_trade_time =  (adjust_vector / trading_time_rollover) / option_legs # condor legs -> 4

        self.logger.debug(f"adjustment: {adjust_vector}")
        self.logger.debug(f"No. of rollover trading time: {trading_time_rollover}, {self.trades_to_non_rollover_per_trade_time = }")


    def get_short_instrument_from_portfolio_for_an_expiry(self, timestamp:datetime, nearest_expiry):
        short_CE_trade_list = []
        short_PE_trade_list = []

        result_dic = {}

        for key, val in self.portfolio.ins_map.items():
            ins: Instrument = val.instrument
            position = val.position
            # self.logger.debug(f"get_short_instrument_from_portfolio_for_an_expiry :: {position = }")
            if ins.instrument_type == "option":
                ins: Option = ins
                if (ins.expiry == nearest_expiry) & (position<0):
                    if (ins.opt_type == 'CE'):
                        try:
                            insDetailed = getInstrumentDetailsWithBlackscholes(ins, timestamp, self.trading_platform, self.logger)
                            short_CE_trade_list.append(Trade(insDetailed, position))
                            # self.logger.info(f'{self.name} Trade idkey: {insDetailed.idKey()}, position: {-position}')
                        except Exception as e:
                            self.logger.info(e)

                    if (ins.opt_type == 'PE'):
                        try:
                            insDetailed = getInstrumentDetailsWithBlackscholes(ins, timestamp, self.trading_platform, self.logger)
                            short_PE_trade_list.append(Trade(insDetailed, position))
                            # self.logger.info(f'{self.name} Trade idkey: {insDetailed.idKey()}, position: {-position}')
                        except Exception as e:
                            self.logger.info(e)

        result_dic['CE'] = short_CE_trade_list
        result_dic['PE'] = short_PE_trade_list

        return result_dic

    def number_of_expiry_from_expiry_info(self, expiry_info):
        expiry_count = 0
        for (day, count) in expiry_info:
            expiry_count += count
        
        return expiry_count

    def rollover_trades(self, timestamp):
        # final_trade_list = []
        try:
            trade_list = []

            component_expiry_list = (self.get_component_expiry_list(timestamp))
            spot = self.trading_platform.getSpot(timestamp)

            nearest_expiry = component_expiry_list[0]
            unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry)

            if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                return trade_list

            if len(component_expiry_list) > 1:
                curr_rollover_expiry = component_expiry_list[self.curr_roll_over_expiry + 1]
                self.curr_roll_over_expiry = (self.curr_roll_over_expiry + 1) % (self.expiry_count - 1)
            else:
                curr_rollover_expiry = nearest_expiry

            self.logger.info(f"nearest_expiry: {nearest_expiry.strftime('%Y-%m-%d')}, rolling_over_to: {curr_rollover_expiry.strftime('%Y-%m-%d')}")

            unwind_count = self.trades_to_roll_per_trade_time
            self.logger.debug(f"{unwind_count = }")
            portfolio_short_trades_dict = self.get_short_instrument_from_portfolio_for_an_expiry(timestamp, nearest_expiry)
            ce_strike_count = len(portfolio_short_trades_dict["CE"])
            i = 0
            pe_trade = None
            ce_trade = None
            # is_run = True

            while unwind_count >= 0:
                # self.logger.debug(f"{unwind_count = } {self.trading_platform.unit_size = }")

                unwind_count_remaining = round_to_lot_size(unwind_count, self.trading_platform.unit_size)
                if unwind_count_remaining == 0:
                    self.logger.info(f"can't unwind anymore, unwind_count: {unwind_count}, which after rounding: {unwind_count_remaining}")
                    break

                while i < ce_strike_count:
                    ce_trade = portfolio_short_trades_dict['CE'][i]
                    strike = ce_trade.instrument.strike

                    for trade in portfolio_short_trades_dict['PE']:
                        if trade.instrument.strike == strike:
                            pe_trade = trade
                            break

                    if pe_trade != None:
                        break

                    i += 1
                else:
                    self.logger.debug(f"Not found any instrument of expiry {nearest_expiry} for unwind at rollover period at time {timestamp}")
                    break

                minimum_position = min(abs(ce_trade.position), abs(pe_trade.position))
                trading_min_pos = round_to_lot_size(minimum_position, self.trading_platform.unit_size)
                actual_trade_pos = min(trading_min_pos, unwind_count_remaining)
                self.logger.info(f"actual_trade_pos: {actual_trade_pos}")

                if (4*abs(actual_trade_pos)) > self.near_week_trades:
                    self.logger.info(f"cannot unwind {4*abs(actual_trade_pos)} near weeks, near weeks left = {self.near_week_trades}")
                    break

                otm_ce_strike = round_to_step(strike + strike*(self.outstrike/100), self.steps)
                otm_pe_strike = round_to_step(strike - strike*(self.outstrike/100), self.steps)

                ins_otm_ce = Option(strike=otm_ce_strike, expiry=nearest_expiry, underlying=underlying, opt_type='CE')
                ins_otm_pe = Option(strike=otm_pe_strike, expiry=nearest_expiry, underlying=underlying, opt_type='PE')
                ins_atm_ce = Option(strike=ce_trade.instrument.strike, expiry=nearest_expiry, underlying=underlying, opt_type='CE')
                ins_atm_pe = Option(strike=pe_trade.instrument.strike, expiry=nearest_expiry, underlying=underlying, opt_type="PE")

                otm_ce = getInstrumentDetailsWithBlackscholes(ins_otm_ce, timestamp, self.trading_platform, self.logger)
                otm_pe = getInstrumentDetailsWithBlackscholes(ins_otm_pe, timestamp, self.trading_platform, self.logger)
                atm_ce = getInstrumentDetailsWithBlackscholes(ins_atm_ce, timestamp, self.trading_platform, self.logger)
                atm_pe = getInstrumentDetailsWithBlackscholes(ins_atm_pe, timestamp, self.trading_platform, self.logger)

                atm_ce_trade_position = actual_trade_pos
                atm_pe_trade_position = actual_trade_pos
                otm_ce_trade_position = -actual_trade_pos
                otm_pe_trade_position = -actual_trade_pos

                trade_list.append(Trade(otm_ce,otm_ce_trade_position, 'unwind'))
                trade_list.append(Trade(otm_pe,otm_pe_trade_position, 'unwind'))
                trade_list.append(Trade(atm_ce,atm_ce_trade_position, 'unwind'))
                trade_list.append(Trade(atm_pe,atm_pe_trade_position, 'unwind'))

                self.logger.info(f'Rollover unwind trades ATM PE {atm_pe.idKey()} position: {atm_pe_trade_position}, ATM CE {atm_ce.idKey()} position: {atm_ce_trade_position}, OTM PE {otm_pe.idKey()} position: {otm_pe_trade_position if otm_pe!=None else 0}, OTM CE {otm_ce.idKey()} position: {otm_ce_trade_position if otm_ce!=None else 0}')

                atm_ce = get_atm_option(self.trading_platform, self.trading_platform.underlying, spot, "CE", curr_rollover_expiry, self.trading_platform.steps, timestamp, self.logger)
                if (atm_ce == None):
                    # self.logger.critical(f"ATM CE not found, skipping {self.name}")
                    self.logger.debug(f"Not found ATM CE instrument of expiry {curr_rollover_expiry} for trade at rollover period at time {timestamp}")
                    trade_list = []
                    break

                atm_pe = get_atm_option(self.trading_platform, self.trading_platform.underlying, spot, "PE", curr_rollover_expiry, self.trading_platform.steps, timestamp,self.logger)
                if (atm_pe == None):
                    self.logger.debug(f"Not found ATM PE instrument of expiry {curr_rollover_expiry} for trade at rollover period at time {timestamp}")
                    trade_list = []
                    break

                otm_ce = get_static_otm_option(self.trading_platform, self.trading_platform.underlying, atm_ce.strike, self.outstrike, self.trading_platform.steps, self.tolerance, self.strict_tolerance, "CE", curr_rollover_expiry, timestamp, self.logger)
                if otm_ce == None:
                    if self.strict_condor == True:
                        self.logger.debug(f"Not found OTM CE instrument of expiry {curr_rollover_expiry} for trade at rollover period at time {timestamp}")
                        trade_list = []
                        break

                otm_pe = get_static_otm_option(self.trading_platform, self.trading_platform.underlying, atm_pe.strike, self.outstrike, self.trading_platform.steps, self.tolerance, self.strict_tolerance, "PE", curr_rollover_expiry, timestamp, self.logger)
                if otm_pe == None:
                    if self.strict_condor == True:
                        self.logger.debug(f"Not found OTM PE instrument of expiry {curr_rollover_expiry} for trade at rollover period at time {timestamp}")
                        trade_list = []
                        break

                trade_list.append(Trade(atm_ce, -actual_trade_pos, 'trade'))
                trade_list.append(Trade(atm_pe, -actual_trade_pos, 'trade'))
                if otm_ce != None:
                    trade_list.append(Trade(otm_ce, actual_trade_pos, 'trade'))
                if otm_pe != None:
                    trade_list.append(Trade(otm_pe, actual_trade_pos, 'trade'))

                unwind_count -= min(unwind_count, actual_trade_pos)

                self.logger.info(f'Rollover new trades ATM PE {atm_pe.idKey()} position: {-actual_trade_pos}, ATM CE {atm_ce.idKey()} position: {-actual_trade_pos}, OTM PE {otm_pe.idKey()} position: {actual_trade_pos if otm_pe!=None else 0}, OTM CE {otm_ce.idKey()} position: {actual_trade_pos if otm_ce!=None else 0}')
                
                self.total_contract_tracker = self.total_contract_tracker - 4*abs(actual_trade_pos) + 4*abs(actual_trade_pos)
                self.logger.debug(f"Total contracts in portfolio = {self.total_contract_tracker} at {timestamp = } in rollover")

                self.near_week_trades -= 4*abs(actual_trade_pos)
                self.logger.debug(f"{timestamp = }, {self.near_week_trades = }")

                if unwind_count == 0:
                    self.logger.info(f"can't unwind anymore, unwind_count: {unwind_count}")
                    break

            return trade_list

        except Exception as e:
            trade_list = []
            self.logger.critical(f"Error in roll over {e} :: {get_exception_line_no()}")
            return trade_list

    def non_rollover_trade_info(self):
        result_dict = {}
        result_vector = []
        for key, val in self.portfolio.ins_map.items():
            ins: Instrument = val.instrument
            position = val.position
            if ins.instrument_type == "option":
                ins: Option = ins
                result_dict[ins.expiry] = result_dict.get(ins.expiry, 0) + abs(position)

        self.logger.debug(f"{result_dict = }")
        for i in np.sort(list(result_dict.keys())):
            result_vector.append(result_dict[i])

        result_vector.append(0)
        self.logger.debug(f"{result_vector = }")

        return np.array(result_vector) 
        # return dict(sorted(result_dict.items()))

    def non_roll_over_trades(self, timestamp):

        try:
            trade_list = []
            component_expiry_list = (self.get_component_expiry_list(timestamp))
            
            nearest_expiry = component_expiry_list[0]
            unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry)

            if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades (Non Rollover)")
                return trade_list


            if not np.all(self.non_rollover_info == 0):
                self.logger.debug(f"inside non-rollover")
                # component_expiry_list = self.get_component_expiry_list(timestamp)
                spot = self.trading_platform.getSpot(timestamp)

                self.logger.debug(f"Before :: {self.non_rollover_info = }")

                neg_idx = np.argmin(self.trades_to_non_rollover_per_trade_time)
                unwind_expiry = component_expiry_list[neg_idx]
                unwind_count = self.trades_to_non_rollover_per_trade_time[neg_idx]

                self.logger.debug(f"{unwind_count = } - Non Rollover")
                self.logger.debug(f"{unwind_expiry = } - Non Rollover")
                self.logger.debug(f"{self.trades_to_non_rollover_per_trade_time = } - Non Rollover")

                is_run = False

                # trades_to_non_rollover_per_trade_time = np.delete(self.trades_to_non_rollover_per_trade_time, neg_idx)

                # curr_non_rollover_exp_idx = self.curr_non_rollover_expiry
                # curr_non_rollover_expiry = component_expiry_list[curr_non_rollover_exp_idx]
                # self.curr_non_rollover_expiry += 1
                # if self.curr_non_rollover_expiry == len(component_expiry_list):
                #     self.curr_non_rollover_expiry = 0

                # unwind_count = self.trading_platform.unit_size

                if unwind_count < 0 and self.non_rollover_info[neg_idx] < 0:
                    if abs(unwind_count) < self.trading_platform.unit_size and abs(unwind_count) != 0:
                        unwind_count = self.trading_platform.unit_size

                    unwind_count_remaining = abs(round_to_lot_size(unwind_count, self.trading_platform.unit_size))

                    self.logger.debug(f"{unwind_count_remaining = }")
                    portfolio_short_trades_dict = self.get_short_instrument_from_portfolio_for_an_expiry(timestamp, unwind_expiry)
                    ce_strike_count = len(portfolio_short_trades_dict["CE"])
                    pe_trade = None
                    ce_trade = None
                    is_run = True
                    i = 0

                    while i < ce_strike_count:
                        ce_trade = portfolio_short_trades_dict['CE'][i]
                        strike = ce_trade.instrument.strike

                        for trade in portfolio_short_trades_dict['PE']:
                            if trade.instrument.strike == strike:
                                pe_trade = trade
                                break

                        if pe_trade != None:
                            break

                        i += 1
                    else:
                        is_run = False
                        self.logger.debug(f"Not found any instrument of expiry {unwind_expiry} for unwind at non rollover period at time {timestamp}")

                    if is_run:
                        minimum_position = min(abs(ce_trade.position), abs(pe_trade.position))
                        trading_min_pos = round_to_lot_size(minimum_position, self.trading_platform.unit_size)
                        actual_trade_pos = min(trading_min_pos, unwind_count_remaining)

                        otm_ce_strike = round_to_step(strike + strike*(self.outstrike/100), self.steps)
                        otm_pe_strike = round_to_step(strike - strike*(self.outstrike/100), self.steps)

                        ins_otm_ce = Option(strike=otm_ce_strike, expiry=unwind_expiry, underlying=underlying, opt_type='CE')
                        ins_otm_pe = Option(strike=otm_pe_strike, expiry=unwind_expiry, underlying=underlying, opt_type='PE')
                        ins_atm_ce = Option(strike=ce_trade.instrument.strike, expiry=unwind_expiry, underlying=underlying, opt_type='CE')
                        ins_atm_pe = Option(strike=pe_trade.instrument.strike, expiry=unwind_expiry, underlying=underlying, opt_type="PE")

                        otm_ce = getInstrumentDetailsWithBlackscholes(ins_otm_ce, timestamp, self.trading_platform, self.logger)
                        otm_pe = getInstrumentDetailsWithBlackscholes(ins_otm_pe, timestamp, self.trading_platform, self.logger)
                        atm_ce = getInstrumentDetailsWithBlackscholes(ins_atm_ce, timestamp, self.trading_platform, self.logger)
                        atm_pe = getInstrumentDetailsWithBlackscholes(ins_atm_pe, timestamp, self.trading_platform, self.logger)

                        atm_ce_trade_position = actual_trade_pos
                        atm_pe_trade_position = actual_trade_pos
                        otm_ce_trade_position = -actual_trade_pos
                        otm_pe_trade_position = -actual_trade_pos
                        
                        trade_list.append(Trade(otm_ce,otm_ce_trade_position, 'unwind'))
                        trade_list.append(Trade(otm_pe,otm_pe_trade_position, 'unwind'))
                        trade_list.append(Trade(atm_ce,atm_ce_trade_position, 'unwind'))
                        trade_list.append(Trade(atm_pe,atm_pe_trade_position, 'unwind'))

                        self.non_rollover_info[neg_idx] += 4*abs(actual_trade_pos)
                        self.logger.debug(f"non rollover period after unwind {self.non_rollover_info = }")

                        self.logger.info(f'Non Rollover unwind trades ATM PE {atm_pe.idKey()} position: {atm_pe_trade_position}, ATM CE {atm_ce.idKey()} position: {atm_ce_trade_position}, OTM PE {otm_pe.idKey()} position: {otm_pe_trade_position if otm_pe!=None else 0}, OTM CE {otm_ce.idKey()} position: {otm_ce_trade_position if otm_ce!=None else 0}')
                        
                        self.total_contract_tracker -= 4*abs(actual_trade_pos)
                        self.logger.debug(f"Total contracts in portfolio = {self.total_contract_tracker} at {timestamp = } in unwind_non_rollover")

                        if unwind_expiry == component_expiry_list[0]:
                            self.near_week_trades -= 4*abs(actual_trade_pos)
                            self.logger.debug(f"{timestamp = }, {self.near_week_trades = }")

                else:
                    unwind_expiry = None
                    
                ###############################################
                for i, curr_non_rollover_expiry in enumerate(component_expiry_list):
                    self.logger.debug(f"for expiry {curr_non_rollover_expiry}")
                    self.logger.debug(f"for expiry {self.non_rollover_info[i]}") 

                    if curr_non_rollover_expiry != unwind_expiry and self.non_rollover_info[i] != 0:
                        if is_file_exist(get_options_intraday_filename_2(self.underlying, timestamp=timestamp, expiry_date=curr_non_rollover_expiry)):
                            self.logger.warning(f"Data not available for {timestamp} and expiry {curr_non_rollover_expiry}")
                            continue

                        unwind_count_non_rollover = self.trades_to_non_rollover_per_trade_time[i]

                        if abs(unwind_count_non_rollover) < self.trading_platform.unit_size and abs(unwind_count_non_rollover) != 0:
                            unwind_count_non_rollover = self.trading_platform.unit_size

                        non_rollover_trade_size = round_to_lot_size(unwind_count_non_rollover, self.trading_platform.unit_size)

                        atm_ce = get_atm_option(self.trading_platform, self.trading_platform.underlying, spot, "CE", curr_non_rollover_expiry, self.trading_platform.steps, timestamp, self.logger)
                        if (atm_ce == None):
                            self.logger.critical(f"ATM CE not found, skipping {self.name}")
                            continue

                        atm_pe = get_atm_option(self.trading_platform, self.trading_platform.underlying, spot, "PE", curr_non_rollover_expiry, self.trading_platform.steps, timestamp,self.logger)
                        if (atm_pe == None):
                            self.logger.critical(f"ATM PE not found, skipping {self.name}")
                            continue

                        otm_ce = get_static_otm_option(self.trading_platform, self.trading_platform.underlying, atm_ce.strike, self.outstrike, self.trading_platform.steps, self.tolerance, self.strict_tolerance, "CE", curr_non_rollover_expiry, timestamp, self.logger)
                        if otm_ce == None:
                            if self.strict_condor == True:
                                self.logger.critical(f"OTM CE not found, and strict condor is true. skipping {self.name}")
                                continue

                        otm_pe = get_static_otm_option(self.trading_platform, self.trading_platform.underlying, atm_pe.strike, self.outstrike, self.trading_platform.steps, self.tolerance, self.strict_tolerance, "PE", curr_non_rollover_expiry, timestamp, self.logger)
                        if otm_pe == None:
                            if self.strict_condor == True:
                                self.logger.critical(f"OTM PE not found, and strict condor is true. skipping {self.name}")
                                continue
                        
                        #####################################################################################################################
                        if ((self.total_contract_tracker + 4*abs(non_rollover_trade_size)) >= self.contract_budget) and not is_run:
                            self.logger.debug(f"cannot trade as contract budget is={self.total_contract_tracker} and unwind={is_run}")
                            trade_list = []
                            break

                        if is_run:
                            if (self.total_contract_tracker - (4*abs(actual_trade_pos)) + (4*abs(non_rollover_trade_size))) > self.contract_budget:
                                self.logger.debug(f"cannot trade as contract budget would be={(self.total_contract_tracker - (4*abs(actual_trade_pos)) + (4*abs(non_rollover_trade_size)))} and unwind={is_run}")
                                
                                self.logger.debug(f"before update {self.near_week_trades = }, {self.total_contract_tracker = }, {self.non_rollover_info = }")
                                self.non_rollover_info[neg_idx] -= 4*abs(actual_trade_pos)
                                self.total_contract_tracker += 4*abs(actual_trade_pos)

                                if unwind_expiry == component_expiry_list[0]:
                                    self.near_week_trades += 4*abs(actual_trade_pos)
                                
                                trade_list = []
                                
                                self.logger.debug(f"updated {self.near_week_trades = }, {self.total_contract_tracker = }, {self.non_rollover_info = }")
                                break
                        #####################################################################################################################

                        trade_list.append(Trade(atm_ce, -non_rollover_trade_size, 'trade'))
                        trade_list.append(Trade(atm_pe, -non_rollover_trade_size, 'trade'))
                        if otm_ce != None:
                            trade_list.append(Trade(otm_ce, non_rollover_trade_size, 'trade'))
                        if otm_pe != None:
                            trade_list.append(Trade(otm_pe, non_rollover_trade_size, 'trade'))

                        self.logger.info(f'Non-Rollover new trades ATM PE {atm_pe.idKey()} position: {-non_rollover_trade_size}, ATM CE {atm_ce.idKey()} position: {-non_rollover_trade_size}, OTM PE {otm_pe.idKey()} position: {non_rollover_trade_size if otm_pe!=None else 0}, OTM CE {otm_ce.idKey()} position: {non_rollover_trade_size if otm_ce!=None else 0}')

                        self.non_rollover_info[i] -= 4*non_rollover_trade_size

                        self.total_contract_tracker += 4*abs(non_rollover_trade_size)
                        self.logger.debug(f"Total contracts in portfolio = {self.total_contract_tracker} at {timestamp = } in rampup_non_rollover")

                        if (curr_non_rollover_expiry == component_expiry_list[0] and is_run):
                            self.near_week_trades += 4*abs(actual_trade_pos)
                            self.logger.debug(f"{timestamp = }, {self.near_week_trades = }")

                self.logger.debug(f"After :: {self.non_rollover_info = }") 

            return trade_list

        except Exception as e:
            trade_list = []
            self.logger.critical(f"Error in non-roll over {e} :: {get_exception_line_no()}")
            return trade_list

    def get_total_position_from_trade_list(self, trade_list) -> int:
        total_position = 0

        if len(trade_list) != 0:
            for trade in trade_list:
                total_position += abs(trade.position)

        return total_position

    def generate_trades(self, timestamp: datetime):
        trade_list = []

        # nearest_expiry = self.get_component_expiry_list(timestamp)[0]
        component_expiry_list = (self.get_component_expiry_list(timestamp))
        nearest_expiry = component_expiry_list[0]
        unwind_date = get_unwind_date_for_an_expiry(nearest_expiry)

        try:
            if self.is_rampup:
                self.logger.info("Rampup Time")
                if self.contract_budget_iterator < self.contract_budget:
                    trade_list = self.rampup_trades(timestamp)

                    self.contract_budget_iterator += self.get_total_position_from_trade_list(trade_list)

                self.logger.info(f"Contract remaning: {self.contract_budget - self.contract_budget_iterator}")
                self.logger.debug(f"Before RampUP period is {self.rampup_period} at time {timestamp}")

                self.rampup_period -= 5
                self.non_rollover_period_iterator += 5
                if self.rampup_period == 0:
                    self.is_rampup = False
                    self.set_roll_over_info(nearest_expiry)

                self.logger.debug(f"After RampUP period is {self.rampup_period} at time {timestamp}")
                self.logger.debug(f"After Ramp Up Status {self.is_rampup}")

            else:
                # non rollover period
                if self.non_rollover_period_iterator < self.non_rollover_period:

                    self.logger.debug(f"Before non rollover period is {self.non_rollover_period-self.non_rollover_period_iterator} at time {timestamp}")
                    
                    # going for non rollover trades.
                    trade_list = self.non_roll_over_trades(timestamp)
                    self.non_rollover_period_iterator += 5

                    self.logger.debug(f"After non rollover period is {self.non_rollover_period-self.non_rollover_period_iterator} at time {timestamp}")

                    if timestamp.time() == exchange_end_time:
                        try:
                            self.trades_to_non_rollover_per_trade_time = (self.non_rollover_info / ((self.non_rollover_period - self.non_rollover_period_iterator) / 5)) / 4
                        except:
                            pass

                    self.logger.debug(f"{self.trades_to_non_rollover_per_trade_time = }, inside generate trade at time = {timestamp}")

                    if self.non_rollover_period_iterator == self.non_rollover_period:
                        self.set_roll_over_info(nearest_expiry)

                    unwind_date = get_unwind_date_for_an_expiry(expiry_date=component_expiry_list[0])
                    if timestamp >= datetime.combine(unwind_date, exchange_end_time):
                        
                        # reset the non_rollover_period_iterator to zero
                        self.logger.debug(f"Reset the rollover and non_rollover variables at {timestamp}")
                        self.non_rollover_period_iterator = 0
                        self.rollover_period_iterator = 0
                        non_rollover_info = self.non_rollover_trade_info()

                        self.logger.info(f"The total contract at {timestamp} is {non_rollover_info.sum()}")

                        self.logger.debug(f"{non_rollover_info = }")
                        expiry_trade_vector = self.contract_budget * self.expiry_weight_vector
                        self.logger.debug(f'{expiry_trade_vector = }')
                        self.non_rollover_info = expiry_trade_vector - non_rollover_info
                        self.logger.debug(f"{self.non_rollover_info}")
                        self.get_non_rollover_trade_size(adjust_vector=self.non_rollover_info)

                        self.total_contract_tracker = non_rollover_info.sum()

                        self.near_week_trades = non_rollover_info[0]
                        self.logger.debug(f"Now new near week is = {self.near_week_trades}")

                # rollover period
                else:
                    self.logger.debug(f"Before rollover period is {self.rollover_period-self.rollover_period_iterator} at time {timestamp}")
                    # going for rollover trades.
                    trade_list = self.rollover_trades(timestamp)
                    self.rollover_period_iterator += 5
                    self.logger.debug(f"After rollover period is {self.rollover_period-self.rollover_period_iterator} at time {timestamp}")

                    unwind_date = get_unwind_date_for_an_expiry(expiry_date=component_expiry_list[0])
                    if timestamp >= datetime.combine(unwind_date, exchange_end_time):
                        
                        # reset the non_rollover_period_iterator to zero
                        self.logger.debug(f"Reset the rollover and non_rollover variables at {timestamp}")
                        self.non_rollover_period_iterator = 0
                        self.rollover_period_iterator = 0
                        non_rollover_info = self.non_rollover_trade_info()

                        self.logger.info(f"The total contract at {timestamp} is {non_rollover_info.sum()}")

                        self.logger.debug(f"{non_rollover_info = }")
                        expiry_trade_vector = self.contract_budget * self.expiry_weight_vector
                        self.logger.debug(f'{expiry_trade_vector = }')
                        self.non_rollover_info = expiry_trade_vector - non_rollover_info
                        self.logger.debug(f"{self.non_rollover_info}")
                        self.get_non_rollover_trade_size(adjust_vector=self.non_rollover_info)

                        self.total_contract_tracker = non_rollover_info.sum()

                        self.near_week_trades = non_rollover_info[0]
                        self.logger.debug(f"Now new near week is = {self.near_week_trades}")

            self.logger.info(f"final total contracts in portfolio at time = {timestamp}, contracts = {self.total_contract_tracker}")




            #     if self.rollover_period_iterator < self.rollover_period:
            #         self.logger.debug(f"Before rollover period is {self.rollover_period_iterator} at time {timestamp}")

            #         trade_list = self.rollover_trades(timestamp)

            #         self.rollover_period_iterator += 5
            #         self.logger.debug(f"After rollover period is {self.rollover_period-self.rollover_period_iterator} at time {timestamp}")

            #     else:
            #         if self.is_non_rollover_info_time:
            #             self.logger.debug(f"Inside non-rollover info")

            #             non_rollover_info = self.non_rollover_trade_info()
            #             expiry_trade_vector = self.contract_budget * self.expiry_weight_vector
            #             self.non_rollover_info = expiry_trade_vector - non_rollover_info
            #             self.is_non_rollover_info_time = False

            #             self.logger.debug(f"Non-rollover info: {non_rollover_info}, expiry_trade_vector: {expiry_trade_vector}, deficit: {self.non_rollover_info}")

            #         trade_list = self.non_roll_over_trades(timestamp)

            #         self.non_rollover_period_iterator += 5
            #         if self.non_rollover_period_iterator >= self.non_rollover_period:
            #             self.non_rollover_period_iterator = 0
            #             self.rollover_period_iterator = 0
            #             self.is_non_rollover_info_time = True

            # unwind_date = get_unwind_date_for_an_expiry(expiry_date=component_expiry_list[0])
            # if timestamp >= datetime.combine(unwind_date, exchange_end_time):
            #     pass

            return trade_list
        except Exception as e:
            self.logger.critical(f"Some unhandled error occured in {self.name}: {e} :: {get_exception_line_no()}")
            return trade_list

