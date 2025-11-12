from datetime import datetime, date, time
from tradelib.models.Portfolio import Portfolio
from tradelib.trading_platform import TradingPlatform
from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_lot_size, round_to_step, moneyness_percentage, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option,get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date, get_static_otm_option

from tradelib_logger import logger
from models.Greeks import Greeks
from models.Trade import Trade
from models.Option import Option
from models.Blotter import Blotter
from models.OptionDetailed import OptionDetailed
from typing import List, Tuple

from tradelib_global_constants import underlying, steps, lot_size, take_later_expiry_hedge, delta_threshold, gamma_threshold, unwind_time, date_format, expiry_info, gamma_hedge_time, tolerance, strict_tolerance, percent_hedge, trade_with_received_money, custom_pct_to_hedge, pct_to_spend, take_money_from_long_otm, allow_frac_gamma_hedge, gamma_hege_otm_outstrike

import numpy as np

class GammaHedgeComponent(StrategyComponent):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, outstrike:int, execute_on_day_start=False) -> None:
        super().__init__("gamma_hedge_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start)
        self.delta_threshold = delta_threshold
        self.gamma_threshold = gamma_threshold
        # TODO all should be in trading platform
        self.steps = steps
        self.lot_size = lot_size
        self.underlying = underlying
        self.unwind_time = unwind_time
        self.take_later_expiry_hedge = take_later_expiry_hedge
        self.outstrike = outstrike
        self.tolerance = tolerance
        self.strict_tolerance = strict_tolerance


    def get_component_expiry_list(self, timestamp: datetime):

        theoretical_dates = get_theoretical_date(info_list=expiry_info, current_date=timestamp.date())
        actual_expiry_dates = get_actual_expiry_dates(theoretical_dates_dict=theoretical_dates, trading_platform = self.trading_platform)

        exp_list = []
        for day in actual_expiry_dates.keys():
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
        self.logger.info(f"current portfolio_gamma: {portfolio_greeks.gamma}")

        if timestamp.time() == gamma_hedge_time and abs(portfolio_greeks.gamma) >= self.gamma_threshold:
            # print('Entered in Gamma Hedge', portfolio_greeks.gamma)
            try:
                spot = self.trading_platform.getSpot(timestamp)
                
                atm_strike = round_to_step(spot, self.steps)
                atm_pe = get_atm_option(self.trading_platform, self.underlying, atm_strike, "PE", nearest_expiry_date, spot, timestamp, self.logger)
                if atm_pe == None:
                    self.logger.critical("ATM PE Not found, skipping hedge")
                    print("ATM PE Not found, skipping hedge")
                    return trade_list
                
                atm_ce = get_atm_option(self.trading_platform, self.underlying, atm_strike, "CE", nearest_expiry_date, spot, timestamp, self.logger)
                if atm_ce == None:
                    self.logger.critical("ATM CE Not found, skipping hedge")
                    print("ATM CE Not found, skipping hedge")
                    return trade_list

                otm_pe = get_static_otm_option(self.trading_platform, self.underlying, atm_pe.strike, gamma_hege_otm_outstrike, self.steps, self.tolerance, self.strict_tolerance, "PE", nearest_expiry_date, timestamp, self.logger)
                if otm_pe == None:
                    self.logger.critical(f"OTM PE not found, and strict condor is true. skipping {self.name}")

                otm_ce = get_static_otm_option(self.trading_platform, self.underlying, atm_ce.strike, gamma_hege_otm_outstrike, self.steps, self.tolerance, self.strict_tolerance, "CE", nearest_expiry_date, timestamp, self.logger)
                if otm_ce == None:
                    self.logger.critical(f"OTM CE not found, and strict condor is true. skipping {self.name}")

                gamma_of_strangle = otm_ce.gamma + otm_pe.gamma
                hedge_ratio = (portfolio_greeks.gamma / gamma_of_strangle) * percent_hedge
                hedge_sign = np.sign(hedge_ratio)
                
                # print('Gamma Hedge', timestamp, self.blotter.get_accumulated_money(update=True))
                # print('Gamma Hedge', timestamp, self.blotter.get_accumulated_money(True))
                # print('Gamma Hedge', timestamp, otm_ce.mid, otm_pe.mid)

                premium_spent, premium_rcv = self.blotter.get_accumulated_money(update=True)

                #!Implement TRADE_WITH_RECVD_MONEY
                if trade_with_received_money:
                    otm_ce_price, otm_pe_price = otm_ce.mid, otm_pe.mid

                    if custom_pct_to_hedge:
                        pct_amount_to_spend = pct_to_spend
                    else:
                        pct_amount_to_spend = np.nan_to_num((premium_spent / premium_rcv))
                        # print(timestamp, premium_spent, premium_rcv)

                    if take_money_from_long_otm and custom_pct_to_hedge:
                        amount_spendable = (pct_amount_to_spend * premium_spent)
                    else:
                        amount_spendable = (pct_amount_to_spend * premium_rcv)

                    amount_each_leg = (amount_spendable / 2)
                    hedge_qty = min((amount_each_leg / otm_ce_price), (amount_each_leg / otm_pe_price))
                    hedge_ratio = hedge_sign * min(hedge_qty, abs(hedge_ratio))

                #!Implement ALLOW_FRAC_GAMMA_HEDGE
                if allow_frac_gamma_hedge:
                    hedge_qty = round((-1) * hedge_ratio, 2)
                else:
                    hedge_qty = round((-1) * hedge_ratio)

                #!Add to Trade List
                if hedge_qty:
                    trade_list.append(Trade(otm_ce, hedge_qty, "gamma_hedge"))
                    trade_list.append(Trade(otm_pe, hedge_qty, "gamma_hedge"))

                # print(timestamp, hedge_qty)

                return trade_list

            except Exception as e:
                logger.critical(e)
                return trade_list
            
        else:
            self.logger.info(f"delta threshold {self.delta_threshold} not reached, skipping hedge")
            return trade_list
