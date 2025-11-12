from datetime import datetime, time, date
from tradelib.models.Portfolio import Portfolio
from tradelib.trading_platform import TradingPlatform
from ._strategy_component import StrategyComponent
from tradelib_logger import logger
from models.Trade import Trade
from models.Instrument import Instrument
from models.Option import Option
from models.Future import Future
from models.OptionDetailed import OptionDetailed
from models.Blotter import Blotter
from typing import List
from tradelib_blackscholes_utils import getInstrumentDetailsWithBlackscholes
from tradelib_global_constants import unwind_time, expiry_info, data_dir, meta_data_file_name, date_format
from tradelib.tradelib_global_constants import intraday_trade

from tradelib_utils import get_theoretical_date, get_unwind_date_for_an_expiry
from tradelib.tradelib_trade_utils import get_atm_option,get_actual_expiry_dates, get_early_expiry_date, get_late_expiry_date
import json, os

class SettelmentComponent(StrategyComponent):
    def __init__(self, trading_platform: TradingPlatform, portfolio: Portfolio, blotter: Blotter, trade_side, skip_count=1, execute_on_day_start=True, contract_quota:int = None) -> None:
        super().__init__("settelment_component", trading_platform, portfolio, blotter, skip_count, execute_on_day_start, trade_side, contract_quota)
        self.unwind_time = unwind_time
        self.init_contract_quota = contract_quota


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
        final_trade_list: List[Trade] = []

        
        current_time = timestamp.time()
        if time(16, 0) < current_time or current_time < time(9, 30):
            return final_trade_list


        # unwind_dict = json.load(open(os.path.join(data_dir, meta_data_file_name)))['Unwind_dates']
        # json.load(open(os.path.join(data_dir, "meta_data.json")))

        if intraday_trade:
            if self.unwind_time == timestamp.time():
                trade_list: List[Trade] = []
                for key, val in self.portfolio.ins_map.items():
                    ins: Instrument = val.instrument
                    position = val.position
                    # if ins.instrument_type == "option":
                    #     ins: Option = ins
                    #     try:
                    #         insDetailed = getInstrumentDetailsWithBlackscholes(ins, timestamp, self.trading_platform, self.logger)
                    #         trade_list.append(Trade(insDetailed, -position, 'unwind'))
                    #         self.logger.info(f'{self.name} Trade idkey: {insDetailed.idKey()}, position: {-position}')
                    #     except Exception as e:
                    #         self.logger.info(e)
                    
                    if ins.instrument_type == "future":
                        ins: Option = ins
                        try:
                            insDetailed = getInstrumentDetailsWithBlackscholes(ins, timestamp, self.trading_platform, self.logger)
                            trade_list.append(Trade(insDetailed, -position, 'unwind'))
                            self.logger.info(f'{self.name} Trade idkey: {insDetailed.idKey()}, position: {-position}')
                        except Exception as e:
                            self.logger.info(e)

                final_trade_list.extend(trade_list)
        else:

            component_expiry_list = self.get_component_expiry_list(timestamp)

            for nearest_expiry_date in component_expiry_list:
                
                trade_list: List[Trade] = []
                unwind_date = get_unwind_date_for_an_expiry(expiry_date=nearest_expiry_date)
                
                if datetime.combine(unwind_date, self.unwind_time) == timestamp:
                    # print(f'{"-"*20} Unwinding time {"-"*20}', timestamp)
                    self.logger.info(f'{"-"*20} Unwinding time {"-"*20}')

                    if unwind_date != nearest_expiry_date:
                        print(f'Data not available for the expiry {nearest_expiry_date}. Going for a early unwind on {unwind_date}')
                        self.logger.info(f'Data not available for the expiry {nearest_expiry_date}. Going for a early unwind on {unwind_date}')

                    for key, val in self.portfolio.ins_map.items():
                        ins: Instrument = val.instrument
                        position = val.position
                        # if ins.instrument_type == "option":
                        #     ins: Option = ins
                        #     if (ins.expiry == nearest_expiry_date):
                        #         try:
                        #             insDetailed = getInstrumentDetailsWithBlackscholes(ins, timestamp, self.trading_platform, self.logger)
                        #             trade_list.append(Trade(insDetailed, -position, 'unwind'))
                        #             self.logger.info(f'{self.name} Trade idkey: {insDetailed.idKey()}, position: {-position}')
                        #         except Exception as e:
                        #             self.logger.info(e)

                        if ins.instrument_type == "future":
                            ins: Future = ins
                            try:
                                insDetailed = getInstrumentDetailsWithBlackscholes(ins, timestamp, self.trading_platform, self.logger)
                                trade_list.append(Trade(insDetailed, -position, 'unwind'))
                                self.logger.info(f'{self.name} Trade idkey: {insDetailed.idKey()}, position: {-position}')
                            except Exception as e:
                                self.logger.info(e)

                    self.portfolio.settelportfolio(timestamp, nearest_expiry_date)

                final_trade_list.extend(trade_list)

        return final_trade_list

    def execute_trade(self, timestamp: datetime):
        self.trade_list = self.generate_trades(timestamp)
        if (len(self.trade_list) > 0):
            self.update_portfolio(timestamp)
            self.blotter.addTradeList(self.trade_list, self.name, timestamp)
            self.trade_list.clear()
            self.portfolio.clearPortfolio(timestamp)
            self.logger.info(f'{"-"*20} {self.name} executed {"-"*20}')

            self.set_contract_quota(contract_quota=self.init_contract_quota)


