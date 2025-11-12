'''
This is the trade generator model
'''

from datetime import datetime, date, time
from typing import Tuple, List
import copy
import numpy as np

from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_step, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option, get_static_otm_option, get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date

from models.Trade import Trade
from tradelib_logger import logger,get_exception_line_no
from trading_platform._TradingPlatform import TradingPlatform
from models.OptionDetailed import OptionDetailed
from models.Portfolio import Portfolio
from models.Blotter import Blotter
from tradelib_global_constants import underlying, tolerance, strict_condor, strict_tolerance, steps, unit_size, unwind_time, expiry_info

class GammaCleanupComponent(StrategyComponent):
    # TODO: have lifecycle hooks for components
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, outstrike: float, trade_side, gamma_threshold, gamma_condor, otm_strike_tolerance, execute_on_day_start:bool=True) -> None:
        super().__init__("gamma_cleamup_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side)
        self.outstrike = outstrike
        self.tolerance = tolerance
        self.strict_condor = strict_condor
        self.strict_tolerance = strict_tolerance
        self.steps = steps
        self.underlying = underlying
        self.unit_size = unit_size
        self.unwind_time = unwind_time

        self.delta_threshold_for_gamma_cleanup = gamma_threshold/100
        self.is_gamma_condor = gamma_condor
        self.otm_strike_tolerance = otm_strike_tolerance

        # attaching expiry should give fexibility to trade condors from different expiries
        # need to think about it. expiry should be handled by unwind component
        # self._expiry = expiry_date

    def generate_unwind_list(self, timestamp):
        final_unwind_list = []
        try:
            df = self.portfolio.getPortfolioInstrumentDetailedDF(timestamp=timestamp)
            p_df = df.copy()

            callDf = df[(df['position'] < 0) & (df['type']=="CE")]
            instrument_strikes = callDf.loc[(callDf['delta'] >= (1 - self.delta_threshold_for_gamma_cleanup)) | (callDf['delta'] <= self.delta_threshold_for_gamma_cleanup), "strike"].to_list()

            logger.info(f"call strikes for gamma cleanup {instrument_strikes}")
            # logger.info(f"At time {timestamp} p df {df[['strike', 'type', 'position', 'delta', 'gamma']]}")

            if len(instrument_strikes):
                # logger.info(f"within gamma function for cleanup, instrument strikes = {instrument_strikes}")
                if not self.is_gamma_condor:
                    df = df[df['position'] < 0]

                for s in instrument_strikes:
                    unwind_list = []
                    try:
                        # get trade size
                        trade_size = min(abs(df.loc[df['strike']==s, "position"].to_numpy()))

                        # get ATM options
                        atm_call, atm_put = df.loc[df['strike']==s, "instrument_details"].to_numpy()

                        if self.is_gamma_condor:
                            # get OTM options
                            otm_call, otm_put, _, proper_otm_found = self.get_otm_based_on_given_strike(strike=s, portfolio_df=p_df, otm_pct=self.outstrike)

                            # if all otms are not found within given threshold dont take the trade
                            if not proper_otm_found:
                                continue

                            # create the unwind list
                            unwind_list.append(Trade(atm_call, trade_size, 'gamma_unwind'))
                            unwind_list.append(Trade(atm_put, trade_size, 'gamma_unwind'))
                            unwind_list.append(Trade(otm_call, -trade_size, 'gamma_unwind'))
                            unwind_list.append(Trade(otm_put, -trade_size, 'gamma_unwind'))

                        elif not self.is_gamma_condor:
                            # create the unwind list
                            unwind_list.append(Trade(atm_call, trade_size, 'gamma_unwind'))
                            unwind_list.append(Trade(atm_put, trade_size, 'gamma_unwind'))

                    except Exception as e:
                        logger.critical(f"Error :: generating unwind list :: line {get_exception_line_no()} :: {e}")

                    final_unwind_list.extend(unwind_list)
                return final_unwind_list

            else:
                # blank list if no trades to do 
                logger.info(f"No instrument found for gamma cleanup")
                return []
                
        except Exception as e:
            logger.critical(f"Error :: generate_unwind_list :: line {get_exception_line_no()} :: {e}")
            return []

    def get_otm_based_on_given_strike(self, strike, portfolio_df, otm_pct):
        try:
            out_strike_call, out_strike_put = round(strike*(1 + (otm_pct/100))), round(strike*(1 - (otm_pct/100)))

            # search nearest strike calls
            call_strikes = portfolio_df.loc[portfolio_df["type"]=="CE", "strike"].to_numpy()
            call_strikes_diff = abs(call_strikes - out_strike_call)
            otm_call = portfolio_df.loc[(portfolio_df["strike"]==call_strikes[np.where(call_strikes_diff==min(call_strikes_diff))[0][0]]) & (portfolio_df["type"]=="CE"), "instrument_details"].to_numpy()[0]
            otm_call_position = portfolio_df.loc[(portfolio_df["strike"]==call_strikes[np.where(call_strikes_diff==min(call_strikes_diff))[0][0]]) & (portfolio_df["type"]=="CE"), "position"].to_numpy()[0]

            # search nearest strike puts
            put_strikes = portfolio_df.loc[portfolio_df["type"]=="PE", "strike"].to_numpy()
            put_strikes_diff = abs(put_strikes - out_strike_put)
            otm_put = portfolio_df.loc[(portfolio_df["strike"]==put_strikes[np.where(put_strikes_diff==min(put_strikes_diff))[0][0]]) & (portfolio_df["type"]=="PE"), "instrument_details"].to_numpy()[0]
            otm_put_position = portfolio_df.loc[(portfolio_df["strike"]==put_strikes[np.where(put_strikes_diff==min(put_strikes_diff))[0][0]]) & (portfolio_df["type"]=="PE"), "position"].to_numpy()[0]

            # the strikes obtained by taking the nearest strike available to the calculated strikes
            out_put_strike, out_call_strike = put_strikes[np.where(put_strikes_diff==min(put_strikes_diff))[0][0]], call_strikes[np.where(call_strikes_diff==min(call_strikes_diff))[0][0]]

            in_range = True
            if in_range: # check if the strikes are within a given threshold else abandon the trades
                call_strike_pct, put_strike_pct = abs(((out_call_strike / strike) * 100) - 100), abs(((out_put_strike / strike) * 100) - 100)

                ## debugger
                logger.info(f"Difference found as {abs(call_strike_pct - otm_pct)} and {abs(put_strike_pct - otm_pct)} for call and put respectively, ATM: {strike}")

                if (abs(call_strike_pct - otm_pct) < self.otm_strike_tolerance) and (abs(put_strike_pct - otm_pct) < self.otm_strike_tolerance):
                    in_range = True # strikes within given threshold tolerance
                    logger.info(f"Found within given range - call strike %: {call_strike_pct} and put strike % {put_strike_pct}")
                else:
                    in_range = False # not present
                    logger.info(f"Not found within given range - call strike %: {call_strike_pct} and put strike % {put_strike_pct}")

            return otm_call, otm_put, min(abs(otm_call_position), abs(otm_put_position)), in_range

        except Exception as e:
            logger.critical(f"Error :: get_otm_based_on_given_strike :: line {get_exception_line_no()} :: {e}")
        
    def generate_new_trade_list(self, timestamp, trade_size, nearest_expiry_date):
        spot = self.trading_platform.getSpot(timestamp)

        trade_list = []
        atm_pe, atm_ce, otm_pe, otm_ce = None, None, None, None
        
        # ATM trades
        atm_pe = get_atm_option(self.trading_platform, self.underlying, spot, "PE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
        if (atm_pe == None):
            self.logger.critical(f"ATM PE not found, skipping {self.name}")
            return []

        atm_ce = get_atm_option(self.trading_platform, self.underlying, spot, "CE", nearest_expiry_date, self.trading_platform.steps, timestamp, self.logger)
        if atm_ce == None:
            self.logger.critical(f"ATM CE not found, skipping {self.name}")
            return []
        
        if self.is_gamma_condor:
            # OTM trades
            otm_pe = get_static_otm_option(self.trading_platform, self.underlying, atm_pe.strike, self.outstrike, self.steps, self.tolerance, self.strict_tolerance, "PE", nearest_expiry_date, timestamp, self.logger)
            if otm_pe == None:
                if self.strict_condor == True:
                    self.logger.critical(f"OTM PE not found, and strict condor is true. skipping {self.name}")
                    return []

            otm_ce = get_static_otm_option(self.trading_platform, self.underlying, atm_ce.strike, self.outstrike, self.steps, self.tolerance, self.strict_tolerance, "CE", nearest_expiry_date, timestamp, self.logger)
            if otm_ce == None:
                if self.strict_condor == True:
                    self.logger.critical(f"OTM CE not found, and strict condor is true. skipping {self.name}")
                    return []

        trade_list.append(Trade(atm_ce, -abs(trade_size), "gamma_trade"))
        trade_list.append(Trade(atm_pe, -abs(trade_size), "gamma_trade"))
        if self.is_gamma_condor:
            if otm_ce != None:
                trade_list.append(Trade(otm_ce, abs(trade_size), "gamma_trade"))
            if otm_pe != None:
                trade_list.append(Trade(otm_pe, abs(trade_size), "gamma_trade"))

        return trade_list

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

    def generate_trades(self, timestamp):

        final_trade_list = []
        try:
            component_expiry_list = self.get_component_expiry_list(timestamp)
            # spot = self.trading_platform.getSpot(timestamp)

            for nearest_expiry_date in component_expiry_list:
                unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)

                if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                    self.logger.warning(f"{self.name} the expiry day unwind time has passed not generating trades")
                    continue

                unwind_trade_list = self.generate_unwind_list(timestamp=timestamp)
                # logger.info(f"at time {timestamp} {unwind_trade_list}")
                final_trade_list.extend(unwind_trade_list)

                divider = 4 if self.is_gamma_condor else 2
                if len(unwind_trade_list):
                    for trade_id in range(0, len(unwind_trade_list)//divider):
                        trade_size = abs(unwind_trade_list[trade_id*divider].position)
                        new_trade_list = self.generate_new_trade_list(timestamp, trade_size, nearest_expiry_date)

                        final_trade_list.extend(new_trade_list)

            return final_trade_list

        except Exception as e:
            logger.critical(f"Error :: generate_trades :: line {get_exception_line_no()} :: {e}")