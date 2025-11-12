from datetime import datetime, date, time
from tradelib.models.Portfolio import Portfolio
from tradelib.trading_platform import TradingPlatform
from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_lot_size, round_to_step, moneyness_percentage, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option,get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date

from tradelib_logger import logger
from models.Greeks import Greeks
from models.Trade import Trade
from models.Option import Option
from models.Blotter import Blotter
from models.OptionDetailed import OptionDetailed
from typing import List, Tuple

from tradelib_global_constants import underlying, steps, lot_size, take_later_expiry_hedge, delta_threshold, unwind_time, date_format, expiry_info

class HedgeComponent(StrategyComponent):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, trade_side, execute_on_day_start=False) -> None:
        super().__init__("hedge_component_test", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side)
        self.delta_threshold = delta_threshold
        # TODO all should be in trading platform
        self.steps = steps
        self.lot_size = lot_size
        self.underlying = underlying
        self.unwind_time = unwind_time
        self.take_later_expiry_hedge = take_later_expiry_hedge

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
        trade_list = []

        component_expiry_list = self.get_component_expiry_list(timestamp)
        
        while len(component_expiry_list) > 0:
            nearest_expiry_date = component_expiry_list.pop(0)

            unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)

            if timestamp >= datetime.combine(unwind_date, self.unwind_time):
                self.logger.info(f"{self.name} this expiry day unwind time has passed")

                if self.take_later_expiry_hedge:
                    self.logger.info(f"taking the next expiry day hedge: {nearest_expiry_date.strftime(date_format)}")
                    nearest_expiry_date = None
                    continue

                else:
                    self.logger.info("not configured to take next expiry trades, skipping hedge.")
                    return trade_list

            else:
                break
        else:
            nearest_expiry_date = None

        if nearest_expiry_date == None:
            self.logger.info("no next expiry found to take trade, skipping hedge.")
            return trade_list

        portfolio_greeks: Greeks = self.portfolio.getPortfolioGreeks(timestamp)
        self.logger.info(f"current portfolio_delta: {portfolio_greeks.delta}")

        if abs(portfolio_greeks.delta) >= self.delta_threshold:
            try:
                spot = self.trading_platform.getSpot(timestamp)
                
                atm_strike = round_to_step(spot, self.steps)
                atm_pe = get_atm_option(self.trading_platform, self.underlying, atm_strike, "PE", nearest_expiry_date, spot, timestamp, self.logger)
                if atm_pe == None:
                    self.logger.critical("ATM PE Not found, skipping hedge")
                    return trade_list
                
                atm_ce = get_atm_option(self.trading_platform, self.underlying, atm_strike, "CE", nearest_expiry_date, spot, timestamp, self.logger)
                if atm_ce == None:
                    self.logger.critical("ATM CE Not found, skipping hedge")
                    return trade_list
                
                synthetic_future_delta = atm_ce.delta - atm_pe.delta
                self.logger.info(f"synthetic future delta: {synthetic_future_delta}")
                trade_qty = (portfolio_greeks.delta/synthetic_future_delta)
                lot_size = round_to_lot_size(trade_qty, self.lot_size, "FLOOR")


                if (lot_size != 0):
                    trade_list.append(Trade(atm_ce, -lot_size, "hedge"))
                    trade_list.append(Trade(atm_pe, lot_size, "hedge"))
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
