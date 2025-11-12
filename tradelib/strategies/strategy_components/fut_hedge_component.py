from datetime import datetime, date, time
from tradelib.models.Portfolio import Portfolio
from tradelib.trading_platform import TradingPlatform
from ._strategy_component import StrategyComponent
from tradelib_utils import is_component_execution_time, round_to_lot_size, round_to_step, moneyness_percentage, get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib_trade_utils import get_atm_option,get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date, get_future

from tradelib_logger import logger
from models.Greeks import Greeks
from models.Trade import Trade
from models.Option import Option
from models.Blotter import Blotter
from models.OptionDetailed import OptionDetailed
from typing import List, Tuple

from tradelib_global_constants import underlying, steps, lot_size, take_later_expiry_hedge, delta_threshold, unwind_time, date_format, expiry_info, price_move_threshold_us_hours,price_move_threshold_asia_hours, PRICE_MOVE_FLAG

class FutureHedgeComponent(StrategyComponent):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, skip_count:int, execute_on_day_start=False) -> None:
        super().__init__("future_hedge_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start)
        self.delta_threshold = delta_threshold
        # TODO all should be in trading platform
        self.steps = steps
        self.lot_size = lot_size
        self.underlying = underlying
        self.unwind_time = unwind_time
        self.take_later_expiry_hedge = take_later_expiry_hedge
        self.last_hedged_prices = {}
        self.price_move_threshold_us_hours= price_move_threshold_us_hours
        self.price_move_threshold_asia_hours= price_move_threshold_asia_hours 
        self.price_move_threshold = self.price_move_threshold_us_hours

        

    def get_future_expiry_date(self, timestamp: datetime):
        
        date_str = timestamp.date().strftime("%Y-%m-%d")
        
        
        exp_date_str = self.trading_platform.future_date_dict[date_str]
        
        exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d")

        return exp_date

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
        current_time = timestamp.time()
        trade_list = []
        if time(18, 0) <= current_time or current_time < time(9, 30):
            self.price_move_threshold= self.price_move_threshold_asia_hours
        elif time(9, 30) <= current_time or current_time < time(17,0) :
            self.price_move_threshold = self.price_move_threshold_us_hours
       

       
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
        
        if PRICE_MOVE_FLAG: 
            
            try:
                expiry_date = self.get_future_expiry_date(timestamp)
                
                es_future = get_future(
                    trading_platform=self.trading_platform,
                    timestamp=timestamp,
                    underlying=self.underlying,
                    expiry=expiry_date,
                    _logger=self.logger,
                )

                if timestamp == datetime(2025,7,28,0,5,0):

                    # print(es_future.instrument_type)
                    # print(es_future.detailed)
                    # print(es_future.underlying)
                    # print(es_future.idKey())
                    print(es_future.idKey())

                current_price = es_future.underlying_spot
                #print(current_price)
                prev_price = self.last_hedged_prices.get(expiry_date)

                if prev_price is not None:
                    point_change = abs(current_price - prev_price) 
                    
                    if point_change < self.price_move_threshold:
                        self.logger.info(
                            f"Price change {point_change:.2f}% < threshold {self.price_move_threshold}%, skipping hedge."
                        )
                        return trade_list
                else:
                    self.logger.info(
                        f"No previous hedge price found for expiry {expiry_date}, proceeding with hedge."
                    )

                self.logger.info(f"delta of the future {es_future.delta}")

                portfolio_greeks: Greeks = self.portfolio.getPortfolioGreeks(timestamp)
                temp_pos = round_to_lot_size(portfolio_greeks.delta, es_future.delta, "ROUND")
                # if timestamp == datetime(2025,6,23,0,33,0):
                #     print(temp_pos)
                lot_size = temp_pos // es_future.delta

                self.logger.info(f"delta hedge quantity {-1 * lot_size}")
                self.logger.info(f"{temp_pos=}")
                self.logger.info(f"{self.portfolio.ins_map=}")
                self.logger.info(f"{portfolio_greeks.delta=}")

                if lot_size != 0:
                    trade_list.append(Trade(es_future, lot_size * -1, "hedge"))
                    self.last_hedged_prices[expiry_date] = current_price
                else:
                    self.logger.info("determined position of synthetic future: 0, skipping hedge")

                return trade_list

            except Exception as e:
                logger.critical(e)
                return trade_list

        else:

            portfolio_greeks: Greeks = self.portfolio.getPortfolioGreeks(timestamp)

            self.logger.info(f"current portfolio_delta: {portfolio_greeks.delta}")
        
            
            
            if abs(portfolio_greeks.delta) >= self.delta_threshold:
                try:
                    
                    expiry_date = self.get_future_expiry_date(timestamp)
                    
                    

                    es_future = get_future(trading_platform=self.trading_platform, timestamp=timestamp, underlying=self.underlying, expiry=expiry_date, _logger = self.logger)

                    self.logger.info(f"delta of the future {es_future.delta}")
                    #print(es_future.underlying_spot)
                    temp_pos = round_to_lot_size(portfolio_greeks.delta, es_future.delta, "ROUND")
                    lot_size = temp_pos//es_future.delta

                    self.logger.info(f"delta hedge quantity {-1*lot_size}")

                    if (lot_size != 0):
                        trade_list.append(Trade(es_future, lot_size*-1, "hedge"))
                        # self.logger.info(f"{self.name} ATM PE({atm_pe.strike}) position: {lot_size}, ATM CE({atm_ce.strike}) position: {-lot_size}")
                    else:
                        self.logger.info("determined position of synthetic future: 0, skipping hedge")

                    return trade_list

                except Exception as e:
                    logger.critical(e)
                    return trade_list
                
            else:
                self.logger.info(f"delta threshold {self.delta_threshold} not reached, skipping hedge")
                return trade_list



# # # #price_movement
# class FutureHedgeComponent(StrategyComponent):
#     def __init__(
#         self,
#         trading_platform: TradingPlatform,
#         portfolio: Portfolio,
#         blotter,
#         skip_count: int,
#         execute_on_day_start=False,
#     ) -> None:
#         super().__init__(
#             "hedge_component",
#             trading_platform,
#             portfolio,
#             blotter,
#             skip_count,
#             execute_on_day_start,
#         )
        

#         self.steps = steps
#         self.lot_size = lot_size
#         self.underlying = underlying
#         self.unwind_time = unwind_time
#         self.take_later_expiry_hedge = take_later_expiry_hedge
#         self.price_move_threshold= price_move_threshold

#         # Percentage threshold to trigger hedge when future price moves by this percent
#         #self.price_move_percent_threshold = 0.5  # example: 0.5%

#         # Stores last hedged price per expiry date
#         self.last_hedged_prices = {}

#     def get_future_expiry_date(self, timestamp: datetime):
#         date_str = timestamp.date().strftime("%Y-%m-%d")
#         exp_date_str = self.trading_platform.future_date_dict[date_str]
#         exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d")
#         return exp_date

#     def get_component_expiry_list(self, timestamp: datetime):
#         theoretical_dates = get_theoretical_date(
#             info_list=expiry_info, current_date=timestamp.date()
#         )
#         actual_expiry_dates = get_actual_expiry_dates(
#             theoretical_dates_dict=theoretical_dates, trading_platform=self.trading_platform
#         )

#         exp_list = []
#         for day in actual_expiry_dates.keys():
#             for j, date in enumerate(actual_expiry_dates[day]):
#                 if date is None:
#                     theory_date = theoretical_dates[day][j]
#                     self.logger.info(
#                         f"{theory_date} ({day}) is not an expiry going for early expiry."
#                     )
#                     exp_date = get_early_expiry_date(
#                         theory_date,
#                         timestamp.date(),
#                         trading_platform=self.trading_platform,
#                         _logger=self.logger,
#                     )
#                     if (exp_date is None) and (theory_date == timestamp.date()):
#                         self.logger.info(
#                             f"{theory_date} ({day}) is not an expiry going for late expiry."
#                         )
#                         exp_date = get_late_expiry_date(
#                             theory_date,
#                             trading_platform=self.trading_platform,
#                             _logger=self.logger,
#                         )
#                     if exp_date is not None:
#                         exp_list.append(exp_date)
#                         self.logger.info(
#                             f"Found early expiry for {theory_date} ({day}) is {exp_date} ({exp_date.strftime('%A')})"
#                         )
#                 else:
#                     exp_list.append(date)
#         return exp_list

#     def generate_trades(self, timestamp: datetime) -> List[Trade]:
#         trade_list = []
#         component_expiry_list = self.get_component_expiry_list(timestamp)
        
#         while len(component_expiry_list) > 0:
#             nearest_expiry_date = component_expiry_list.pop(0)
#             unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)
#             if timestamp >= datetime.combine(unwind_date, self.unwind_time):
#                 self.logger.info(f"{self.name} this expiry day unwind time has passed")
#                 if self.take_later_expiry_hedge:
#                     self.logger.info(
#                         f"taking the next expiry day hedge: {nearest_expiry_date.strftime(date_format)}"
#                     )
#                     nearest_expiry_date = None
#                     continue
#                 else:
#                     self.logger.info(
#                         "not configured to take next expiry trades, skipping hedge."
#                     )
#                     return trade_list
#             else:
#                 break
#         else:
#             nearest_expiry_date = None

#         if nearest_expiry_date is None:
#             self.logger.info("no next expiry found to take trade, skipping hedge.")
#             return trade_list

#         try:
#             expiry_date = self.get_future_expiry_date(timestamp)
#             es_future = get_future(
#                 trading_platform=self.trading_platform,
#                 timestamp=timestamp,
#                 underlying=self.underlying,
#                 expiry=expiry_date,
#                 _logger=self.logger,
#             )

#             current_price = es_future.underlying_spot
#             #print(current_price)
#             prev_price = self.last_hedged_prices.get(expiry_date)

#             if prev_price is not None:
#                 point_change = abs(current_price - prev_price) 
#                 if point_change < self.price_move_threshold:
#                     self.logger.info(
#                         f"Price change {point_change:.2f}% < threshold {self.price_move_threshold}%, skipping hedge."
#                     )
#                     return trade_list
#             else:
#                 self.logger.info(
#                     f"No previous hedge price found for expiry {expiry_date}, proceeding with hedge."
#                 )

#             self.logger.info(f"delta of the future {es_future.delta}")

#             portfolio_greeks: Greeks = self.portfolio.getPortfolioGreeks(timestamp)
#             temp_pos = round_to_lot_size(portfolio_greeks.delta, es_future.delta, "ROUND")
#             lot_size = temp_pos // es_future.delta

#             self.logger.info(f"delta hedge quantity {-1 * lot_size}")

#             if lot_size != 0:
#                 trade_list.append(Trade(es_future, lot_size * -1, "hedge"))
#                 self.last_hedged_prices[expiry_date] = current_price
#             else:
#                 self.logger.info("determined position of synthetic future: 0, skipping hedge")

#             return trade_list

#         except Exception as e:
#             logger.critical(e)
#             return trade_list