from typing import Dict, List
from models.Trade import Trade
from models.Cash import Cash
from models.Instrument import Instrument
from models.OptionDetailed import OptionDetailed
from models.Greeks import Greeks
from models.TransactionCost import TransactionCost
from datetime import datetime
from tradelib.trading_platform._TradingPlatform import TradingPlatform
import csv
from tradelib.tradelib_global_constants import m2m_side
import copy
from models.Option import Option
from models.Future import Future
import os
import numpy as np
import pandas as pd
import ast
from datetime import timedelta, date, time, datetime
from tradelib_logger import logger, get_exception_line_no
from tradelib_global_constants import allowed_fields_in_portfolio_dump, client_name, initial_cash, underlying, transaction_fee, future_multiplier
from tradelib_utils import get_portfolio_filename, serialiseInstrument, get_intrinsic_value_option
from tradelib_blackscholes_utils import getInstrumentDetailsWithBlackscholes

_logger = logger.getLogger("portfolio")

class Portfolio:
    def __init__(self, currency: str, trading_platform: TradingPlatform, output_dir: str ,timestamp : date=None , portfolio_path : str = None) -> None:
        self.weighted_price = 0
        self.currency: str = currency
        self.trading_platform = trading_platform
        self.prev_portfolio_path = portfolio_path
        self.timestamp = timestamp
        self.ins_detail_map: Dict[str, OptionDetailed] = {}
        self.ins_map: Dict[str, Trade] = {}
        self.cash = Cash(initial_cash=initial_cash)
        self.portfolio_dir = os.path.join(output_dir, 'portfolio')
        self.morning_cash = 0
        self.transaction_fees = TransactionCost()
        os.makedirs(self.portfolio_dir, exist_ok=True)  

        if(self.prev_portfolio_path!=None):
            self.initMapsandCash(timestamp)
            

    def initMapsandCash(self,timestamp):
        
     
        try:
            portfolio_df = pd.read_csv(self.prev_portfolio_path)
           
            #Cash
            cash_mask = portfolio_df["Instrument"] == "CASH"
            if cash_mask.any():
                self.cash = Cash(initial_cash=portfolio_df.loc[cash_mask, "Position_EIS"].values[0])

            # Option and future instruments
            #instrument_mask = ~cash_mask
            instruments = portfolio_df.loc[~cash_mask, ["Type_EIS", "Expiry", "Strike_EIS", "Position_EIS"]].copy()
            instruments["Expiry"] = pd.to_datetime(instruments["Expiry"])
            options_mask = instruments["Type_EIS"].isin(["CE", "PE"])
            futures_mask = ~options_mask

            # Process Options
            option_trades = {}
            option_details = {}
            if options_mask.any():
                options = instruments.loc[options_mask]
                for strike, expiry, opt_type, position in zip(options["Strike_EIS"], options["Expiry"], options["Type_EIS"], options["Position_EIS"]):
                    option_instrument = Option(strike, expiry, underlying, opt_type)
                    trade = Trade(option_instrument, position)
                    trade_key = trade.instrument.idKey()
                    option_trades[trade_key] = copy.copy(trade)
                    option_details[trade_key] = copy.copy(getInstrumentDetailsWithBlackscholes(option_instrument, timestamp, self.trading_platform, logger))

            # Process Futures
            future_trades = {}
            future_details = {}
            if futures_mask.any():
                futures = instruments.loc[futures_mask]
                for strike, expiry, fut_type, position in zip(futures["Strike_EIS"], futures["Expiry"], futures["Type_EIS"], futures["Position_EIS"]):
                    future_instrument = Future(strike, expiry, underlying, fut_type)
                    trade = Trade(future_instrument, position)
                    trade_key = trade.instrument.idKey()
                    future_trades[trade_key] = copy.copy(trade)
                    future_details[trade_key] = copy.copy(self.trading_platform.getInstrumentDetails(trade.instrument, timestamp))

            # Merge results
            self.ins_map = {**option_trades, **future_trades}
            self.ins_detail_map = {**option_details, **future_details}

            _logger.info(f"Initialized portfolio, timestamp: {timestamp}")

        except Exception as e:
            _logger.critical(f"Portfolio::initMapsandCash {e}")

    def clearPortfolio(self, timestamp: datetime):
        clear_list = []
        for key, val in self.ins_map.items():
            if val.instrument.instrument_type == "option":
                ins: Option = val.instrument
                if ins.expiry == timestamp.date():
                    clear_list.append(key)

        for clear_id in clear_list:
            del self.ins_map[clear_id]
            del self.ins_detail_map[clear_id]
        
        _logger.info("unwinded all expiring instruments")

    def saveToCSV(self, timestamp: datetime):
        '''
        saves current state of portfolio in a csv
        '''
        file_path = os.path.join(self.portfolio_dir, get_portfolio_filename(timestamp, client_name))
        with open(file_path, "w") as fp:
            writer = csv.writer(fp)
            writer.writerow(['instrument_id', 'instrument_id_key', 'instrument_object', 'position', 'current price', 'value'])
            writer.writerow([self.cash.instrument_type, self.cash.idKey(), serialiseInstrument(self.cash, False, allowed_fields_in_portfolio_dump), self.cash.value, 1, self.cash.value])
            for key, val in self.ins_map.items():
                try:
                    detailedIns = getInstrumentDetailsWithBlackscholes(val.instrument, timestamp, self.trading_platform, _logger)
                    if detailedIns.instrument_type == "option":
                        price = self.getPriceOptionM2M(detailedIns=detailedIns, position=val.position, market_side=m2m_side)
                        id = detailedIns.id
                    writer.writerow([id, val.instrument.idKey(), serialiseInstrument(val.instrument, False,allowed_fields_in_portfolio_dump), val.position, price, val.position*price])
                except Exception as e:
                    _logger.critical(e)

    def getPortfolioInstrumentDetailedDF(self, timestamp) -> pd.DataFrame:
        try:
            detailedIns_dict_list = []
            portfolio_option_df = pd.DataFrame()
            for key, val in self.ins_map.items():
                try:
                    # detailedIns: OptionDetailed = getInstrumentDetailsWithBlackscholes(val.instrument, timestamp, self.trading_platform, _logger)
                    detailedIns = self.ins_detail_map[key]

                    detailedIns_dict_list.append({'id':detailedIns.id, 'type':detailedIns.opt_type, 'strike':detailedIns.strike, 'position':val.position, 'bid_price':detailedIns.bid, 'ask_price':detailedIns.ask, 'mid_price':detailedIns.mid, 'delta':detailedIns.delta, 'gamma':detailedIns.gamma, 'theta':detailedIns.theta, 'vega':detailedIns.vega, 'sigma':detailedIns.sigma, 'instrument_details':detailedIns})

                except Exception as e:
                    _logger.critical(f"getPortfolioInstrumentDetailedDF :: {e}")

            portfolio_option_df = pd.DataFrame.from_dict(detailedIns_dict_list)
            return portfolio_option_df
        except Exception as e:
            _logger.critical(f"Error :: getPortfolioInstrumentDetailedDF :: line {get_exception_line_no()} :: {e}")

    def updatePortfolio(self, tradeList: List[Trade], timestamp: datetime, trade_side:str) -> None:
        '''
        Updates portfolio with tradelist
        '''
        try:
            _logger.debug(f"Porfolio state before update:")
            greeks = self.getPortfolioGreeks(timestamp)
            _logger.debug(f"delta: {greeks.delta}, gamma: {greeks.gamma}, vega: {greeks.vega}, theta: {greeks.theta}, sigma: {greeks.sigma}, contract_size: {self.getContractSize()}")
            cashChange = 0
            exchange_fees_change = 0
            transaction_fees_change = 0

            for trade in tradeList:
                if trade.position == 0:
                    continue

                transaction_fees_change += self.transaction_fees.calculate_transaction_cost()

                if trade.instrument.detailed == False:
                    detailedIns = self.trading_platform.getInstrumentDetails(trade.instrument, timestamp)
                else:
                    detailedIns = trade.instrument

                if trade.instrument.idKey() in self.ins_map.keys():
                    self.ins_map[trade.instrument.idKey()].position = self.ins_map[trade.instrument.idKey()].position + trade.position
                    if self.ins_map[trade.instrument.idKey()].position == 0:
                        if trade.instrument.instrument_type == 'option':
                            del self.ins_map[trade.instrument.idKey()]
                            del self.ins_detail_map[trade.instrument.idKey()]
                else:
                    self.ins_map[trade.instrument.idKey()] = copy.copy(trade)
                    self.ins_detail_map[trade.instrument.idKey()] = copy.copy(detailedIns)
                    #print(self.ins_detail_map[trade.instrument.idKey()])
                    # if trade.instrument.instrument_type == 'future':
                        # self.weighted_price = detailedIns.mid


                if detailedIns.instrument_type == "option":
                    price = self.getPriceOption(detailedIns=detailedIns, position=trade.position, market_side=trade_side)

                    # _logger.info(f"ins_detailed {detailedIns.strike} traded_price {price} ask {detailedIns.ask} bid {detailedIns.bid} mid {detailedIns.mid} position {trade.position} trade_side {trade_side}")

                    cashChange += -(price * trade.position)
                    exchange_fees_change += self.transaction_fees.calculate_exchange_cost(trade_position=trade.position, trade_price=price, instrument_type='option')

                if detailedIns.instrument_type == "future":
                    price = detailedIns.mid

                    total_position = self.ins_map[trade.instrument.idKey()].position
                    new_position = trade.position
                    old_position = total_position - new_position

                    exchange_fees_change += self.transaction_fees.calculate_exchange_cost(trade_position=trade.position, trade_price=price, instrument_type='future')

                    # _logger.info(f"At time {timestamp} Future {total_position=} {new_position=} {old_position=}")

                    if total_position: # When position is not zero
                        old_weighted_price = self.weighted_price
                        self.weighted_price = (old_weighted_price*old_position + price*new_position)/total_position

                        # new_weighted_price = (old_weighted_price*old_position + price*new_position)/total_position
                        # self.weighted_price = new_weighted_price if old_position else self.weighted_price

                    else:
                        # _logger.info(f"At time {timestamp} Future {price=} {new_position=} {self.weighted_price=} {old_position=}")
                        cashChange += (-1) * (price * new_position + old_position * self.weighted_price) * future_multiplier
                        self.weighted_price = 0
                        del self.ins_map[trade.instrument.idKey()]
                        del self.ins_detail_map[trade.instrument.idKey()]

                    # _logger.info(f"At time {timestamp} Future {total_position=} {new_position=} {old_position=} {cashChange=}") 

            # _logger.info(f"At {timestamp} :: {self.weighted_price}")
            cashChange = cashChange - (exchange_fees_change+transaction_fees_change)
            self.cash.addCash(cashChange)

            self.transaction_fees.update_cost(value=(exchange_fees_change+transaction_fees_change))
            _logger.info("updated portfolio")

        except Exception as e:
            _logger.critical(f"Error in updatePortfolio :: line :: {get_exception_line_no()} :: {e}")

    def getContractSize(self):
        position = 0
        for key, val in self.ins_map.items():
            position += abs(val.position)

        return position

    def getMarkToMarket(self, timestamp, m2m_side:str):
        total_m2m = 0
        for key, val in self.ins_map.items():
            try:
                # insDetailed: OptionDetailed = getInstrumentDetailsWithBlackscholes(val.instrument, timestamp, self.trading_platform, _logger)
                insDetailed = self.ins_detail_map[key]

                if val.instrument.instrument_type == 'option':
                    price = self.getPriceOptionM2M(detailedIns=insDetailed, position=val.position, market_side=m2m_side)
                    # _logger.info(f"ins_detailed {insDetailed.strike} traded_price {price} ask {insDetailed.ask} bid {insDetailed.bid} mid {insDetailed.mid} position {val.position} m2m_side {m2m_side}")

                    total_m2m += price*val.position

                elif val.instrument.instrument_type == 'future':
                    # _logger.info(f"ins_detailed {insDetailed.strike} traded_price {price} ask {insDetailed.ask} bid {insDetailed.bid} mid {insDetailed.mid} position {val.position} m2m_side {m2m_side} self.weighted_price {self.weighted_price}")
                    total_m2m += (insDetailed.mid - self.weighted_price) * val.position * future_multiplier
                    # pass

            except Exception as e:
                _logger.critical(f"Error :: getMarkToMarket :: line {get_exception_line_no()} :: {e}")
        return total_m2m

    def getPortfolioGreeks(self, timestamp: datetime):
        '''
        Fetches the portfolio greeks
        '''
        greeks = Greeks()
        
        
        for key, val in self.ins_map.items():
            try:
                # insDetailed: OptionDetailed = getInstrumentDetailsWithBlackscholes(val.instrument, timestamp, self.trading_platform, _logger)
                # _logger.info(f"SUMEGH_DELTA_CALCULATION {key},{insDetailed.delta},{val.position}")
                insDetailed = self.ins_detail_map[key]
                greeks.delta += insDetailed.delta * val.position
                
                greeks.theta += insDetailed.theta * val.position
                greeks.gamma += insDetailed.gamma * val.position
                greeks.vega += insDetailed.vega * val.position
                greeks.sigma += insDetailed.sigma * val.position
            except Exception as e:
                _logger.critical(e)
        
        return greeks

    def is_portfolio_empty(self) -> bool:
        if len(self.ins_map) == 0:
            return True
        else:
            return False

    def getPriceOption(self, detailedIns:Instrument, position:int, market_side:str):
        if market_side == 'market_maker':
            if np.sign(position) < 0: # Sell
                return detailedIns.ask
            else:
                return detailedIns.bid

        elif market_side.lower()=="customer":
            if np.sign(position) < 0: # sell
                return detailedIns.bid
            else:
                return detailedIns.ask

        elif market_side.lower()=="customer+":
            if np.sign(position) < 0: # sell
                return (detailedIns.bid +detailedIns.mid)/2
            else:
                return (detailedIns.ask +detailedIns.mid)/2

        elif market_side.lower()=="market_maker-":
            if np.sign(position) < 0: # sell
                return (detailedIns.ask +detailedIns.mid)/2
            else:
                return (detailedIns.bid +detailedIns.mid)/2

        elif market_side.lower()=="mid":
            return detailedIns.mid

        else:
            raise Exception(f"{market_side=} is not implemented into the codebase")

    def getPriceOptionM2M(self, detailedIns:Instrument, position:int, market_side:str):
        try:
            if market_side == 'customer':
                if np.sign(position) < 0: # Sell
                    return detailedIns.ask
                else:
                    return detailedIns.bid
                    
            elif market_side.lower()=="market_maker":
                if np.sign(position) < 0: # sell
                    return detailedIns.bid
                else:
                    return detailedIns.ask

            elif market_side.lower()=="market_maker-":
                if np.sign(position) < 0: # sell
                    return (detailedIns.bid +detailedIns.mid)/2
                else:
                    return (detailedIns.ask +detailedIns.mid)/2

            elif market_side.lower()=="customer+":
                if np.sign(position) < 0: # sell
                    return (detailedIns.ask +detailedIns.mid)/2
                else:
                    return (detailedIns.bid +detailedIns.mid)/2

            elif market_side.lower()=="mid":
                return detailedIns.mid

            else:
                raise Exception(f"{market_side=} is not implemented into the codebase")
        except Exception as e:
            raise e

    def updatePortfolioWithCorrectPrices(self, timestamp: datetime)->None:
        try:
            _logger.info(f"At time {timestamp} in updatePortfolioWithCorrectPrices")
            for key, val in self.ins_map.items():
                if val.instrument.instrument_type == 'option':
                    if self.trading_platform.is_option_price_problem(instrument=val.instrument, timestamp=timestamp):
                        insDetailed = self.ins_detail_map.get(key)
                        value_type = "old values"

                    else:
                        insDetailed: OptionDetailed = getInstrumentDetailsWithBlackscholes(val.instrument, timestamp, self.trading_platform, _logger)
                        self.ins_detail_map[key] = insDetailed
                        value_type = "new values"

                    _logger.info(f"SUMEGH At time {timestamp} instrument {key} is updated with {value_type}.")

                elif val.instrument.instrument_type == 'future':
                    insDetailed: OptionDetailed = getInstrumentDetailsWithBlackscholes(val.instrument, timestamp, self.trading_platform, _logger)
                    self.ins_detail_map[key] = insDetailed
                    value_type = "new values"

                # _logger.info(f"At time {timestamp} instrument {key} is updated with {value_type}.")

        except Exception as e:
            _logger.critical(f"Error in updatePortfolioWithCorrectPrices :: line {get_exception_line_no()} :: {e}")

    def reinitailse_morning_cash_on_day_start(self, morning_cash):
        self.morning_cash = morning_cash

    def getPortfolioValue(self, timestamp, m2m_side:str):
        return self.cash.value + self.getMarkToMarket(timestamp=timestamp, m2m_side=m2m_side)

    def getMorningCash(self):
        return self.morning_cash


    def settelportfolio(self, timestamp, expiry_date):
        try:
            spot = self.trading_platform.getSpot(timestamp)
            cashChange = 0
            instrument_delete_list = []

            for key, val in self.ins_map.items():
                ins: Instrument = val.instrument
                position = val.position
                if ins.instrument_type == "option":
                    
                    if (ins.expiry == expiry_date):
                        intrinsic_value = get_intrinsic_value_option(option_type=ins.opt_type, spot=spot, strike=ins.strike)
                        _logger.info(f"strike = {ins.strike}, spot = {spot}, opt_type = {ins.opt_type}, intrinsic_value = {intrinsic_value}")
                        
                        cashChange += intrinsic_value*position

                        instrument_delete_list.append(ins.idKey())

            for key in instrument_delete_list:
                del self.ins_map[key]
                del self.ins_detail_map[key]

            self.cash.addCash(cashChange)
            _logger.info("updated portfolio")

        except Exception as e:
            _logger.critical(f"Error in settelportfolio {get_exception_line_no()} error {e}")

            