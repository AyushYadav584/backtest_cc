from datetime import datetime, date, time
from tradelib.models.Portfolio import Portfolio
from tradelib.trading_platform import TradingPlatform
from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_lot_size, round_to_step, moneyness_percentage, get_theoretical_date, get_unwind_date_for_an_expiry, get_options_intraday_filename_2, is_file_exist
from tradelib_trade_utils import get_atm_option,get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date
from tradelib_logger import logger
from models.Greeks import Greeks
from models.Trade import Trade
from models.Option import Option
from models.Blotter import Blotter
from models.OptionDetailed import OptionDetailed
from typing import List, Tuple

from tradelib_global_constants import underlying, steps, lot_size, take_later_expiry_hedge, delta_threshold, unwind_time, date_format, expiry_info, exchange_end_time

class ConstantRiskHedgeComponent(StrategyComponent):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, execute_on_day_start=False) -> None:
        super().__init__("constant_risk_hedge_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start)
        self.delta_threshold = delta_threshold
        # TODO all should be in trading platform
        self.steps = steps
        self.lot_size = lot_size
        self.underlying = underlying
        self.unwind_time = unwind_time
        self.take_later_expiry_hedge = take_later_expiry_hedge

        self.non_rollover_period = 375 * 3
        self.non_rollover_period_iterator = 0

        self.skip_count = skip_count


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
                        exp_list.append(exp_date)
                        self.logger.info(f"Found early expiry for {theory_date} ({day}) is {exp_date} ({exp_date.strftime('%A')})")

                else:
                    exp_list.append(date)

        return exp_list

    def generate_trades(self, timestamp: datetime) -> List[Trade]:
        trade_list, flag = [], 0 # flag to be set to 1 , if unwind time has passed

        component_expiry_list = self.get_component_expiry_list(timestamp)

        # nearest_expiry_date = None
        nearest_expiry_date = component_expiry_list[0]
        far_week_expiry_date = component_expiry_list[1]
        i = 1

        if self.non_rollover_period_iterator > self.non_rollover_period:
            while len(component_expiry_list) > i:
                nearest_expiry_date_holder = component_expiry_list[i]

                if not is_file_exist(get_options_intraday_filename_2(self.underlying, timestamp=timestamp, expiry_date=nearest_expiry_date_holder)):
                    i += 1
                    self.logger.debug(f"Data not available for expiry={nearest_expiry_date_holder}, time={timestamp}")
                    continue

                nearest_expiry_date = nearest_expiry_date_holder
                break

        self.non_rollover_period_iterator += self.skip_count

        unwind_date = get_unwind_date_for_an_expiry(expiry_date=component_expiry_list[0])
        if timestamp >= datetime.combine(unwind_date, exchange_end_time):
            self.non_rollover_period_iterator = 0

        unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)
        if timestamp >= datetime.combine(unwind_date, self.unwind_time):
            # self.logger.info(f"{self.name} this expiry day unwind time has passed, skipping hedge.")
            self.logger.info(f"{self.name} this expiry day unwind time has passed, hedge with far week = {far_week_expiry_date}.")
            # self.non_rollover_period_iterator = 0
            # return trade_list
            flag = 1

        # if nearest_expiry_date == None:
        #     self.logger.info("no next expiry found to take trade, skipping hedge.")
        #     return trade_list
        if flag:
            self.logger.debug(f"taking hedges using expiry = {far_week_expiry_date}, since expiry time has passed")
        else:
            self.logger.debug(f"taking hedges using expiry = {nearest_expiry_date}")

        portfolio_greeks: Greeks = self.portfolio.getPortfolioGreeks(timestamp)
        self.logger.info(f"current portfolio_delta: {portfolio_greeks.delta}")

        if abs(portfolio_greeks.delta) >= self.delta_threshold:
            try:
                spot = self.trading_platform.getSpot(timestamp)
                
                atm_strike = round_to_step(spot, self.steps)
                if flag:
                    atm_pe = get_atm_option(self.trading_platform, self.underlying, atm_strike, "PE", far_week_expiry_date, spot, timestamp, self.logger)
                else:
                    atm_pe = get_atm_option(self.trading_platform, self.underlying, atm_strike, "PE", nearest_expiry_date, spot, timestamp, self.logger)

                if atm_pe == None:
                    self.logger.critical("ATM PE Not found, skipping hedge")
                    return trade_list

                if flag:
                    atm_ce = get_atm_option(self.trading_platform, self.underlying, atm_strike, "CE", far_week_expiry_date, spot, timestamp, self.logger)
                else:
                    atm_ce = get_atm_option(self.trading_platform, self.underlying, atm_strike, "CE", nearest_expiry_date, spot, timestamp, self.logger)

                if atm_ce == None:
                    self.logger.critical("ATM CE Not found, skipping hedge")
                    return trade_list

                synthetic_future_delta = atm_ce.delta - atm_pe.delta
                self.logger.info(f"synthetic future delta: {synthetic_future_delta}")
                trade_qty = (portfolio_greeks.delta/synthetic_future_delta)
                lot_size = round_to_lot_size(trade_qty, self.lot_size, "ROUND")

                if (lot_size != 0):
                    trade_list.append(Trade(atm_ce, -lot_size, 'hedge'))
                    trade_list.append(Trade(atm_pe, lot_size, 'hedge'))
                    self.logger.info(f"{self.name} ATM PE({atm_pe.strike}) position: {lot_size}, ATM CE({atm_ce.strike}) position: {-lot_size}")
                else:
                    self.logger.info("determined position of synthetic future: 0, skipping hedge")
                return trade_list

            except Exception as e:
                logger.critical(e)
                return trade_list
            
        else:
            self.logger.info(f"delta threshold {self.delta_threshold} not reached, skipping hedge")
            return trade_list
