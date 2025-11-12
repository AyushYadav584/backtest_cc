from datetime import datetime, date, time
from typing import List, Dict
from trading_platform._TradingPlatform import TradingPlatform
from tradelib.models.Instrument import Instrument
from tradelib.models.OptionDetailed import OptionDetailed
from tradelib.models.FutureDetailed import FutureDetailed
from tradelib.models.Option import Option
from tradelib.models.Trade import Trade
from tradelib.models.Future import Future
import os
import pandas as pd
import numpy as np
from tradelib_logger import logger, get_exception_line_no
from tradelib_global_constants import date_format, DIVIDEND_MAP, data_dir, rv_window, annualizing_parameter
from tradelib_utils import get_options_intraday_filename, get_expiry_dates_on_weekday, round_to_step, get_expiry_from_pre_process, get_trading_days_from_pre_process, get_spot_intraday_filename,get_options_intraday_filename_2, is_file_exist, get_future_expiry_date_from_trading_date
import copy

# TODO: partial exceution allow or not
# TODO: allow underlying object pass

_logger = logger.getLogger("trading platform")
class BacktestTradingPlatform(TradingPlatform):
    def __init__(self, option_data_dir: str, risk_free_rate: float=None, steps: float=None,underlying: str=None, dividend: float=None, spot_move_threshold: float=90.0, check_future_price: bool=False, check_option_prices: bool=False, check_intrinsic_value: bool=False, check_bid_ask: bool=False, bid_ask_move_threshold: float=1, check_price_problem_start_time: time=time(0,0,0)) -> None:
        self.option_data_dir = option_data_dir
        super().__init__(underlying, dividend, steps, risk_free_rate)
        self.intraday_options_df: pd.Dataframe = None
        self.lowest_level_options_df: pd.DataFrame = None #min level data

        self.intraday_options_dict: dict = {}
        self.lowest_level_options_dict: dict = {}

        self.spot_date = None
        self.intraday_spot_df = pd.DataFrame()
        self.spot = None
        self.spot_datetime = None
        self.is_spot_problem = None

        self.rv_date = None
        self.intraday_rv_df = pd.DataFrame()
        self.rv = None
        self.rv_datetime = None

        self.date: date = None
        self.timestamp: datetime = None
        self.expiry_date = None
        self.cache: Dict[str, Instrument] = {} # this map caches the data from searching dataframe
        self.expiry_list = get_expiry_from_pre_process(data_dir=data_dir)
        self.trading_date_list = get_trading_days_from_pre_process(data_dir=data_dir)
        self.future_date_dict = get_future_expiry_date_from_trading_date(data_dir=data_dir)

        self.spot_move_threshold = spot_move_threshold
        self.check_future_price = check_future_price

        self.check_option_prices = check_option_prices
        self.check_price_problem_start_time = check_price_problem_start_time
        self.check_intrinsic_value = check_intrinsic_value
        self.check_bid_ask = check_bid_ask
        self.bid_ask_move_threshold = bid_ask_move_threshold


    def __checkAndReinitialiseDF(self, timestamp:datetime, expiry_date: date) -> None:
        '''
        Reinitialised the intraday DF if the date is changed.
        '''

        date_curr: date = timestamp.date()

        if date_curr != self.date:
            del self.intraday_options_dict
            self.intraday_options_dict = {}

            self.date = date_curr

        if expiry_date not in self.intraday_options_dict.keys():
            try:
                filepath = os.path.join(self.option_data_dir, get_options_intraday_filename_2(self.underlying, timestamp, expiry_date))
                if is_file_exist(filepath):
                    df = pd.read_csv(filepath)

                    df['Date Time'] = pd.to_datetime(df['Date Time'])
                    df.set_index('Date Time', inplace=True)

                    self.intraday_options_dict[expiry_date] = df

                else:
                    self.intraday_options_dict[expiry_date] = pd.DataFrame()
                    raise Exception(f"Data not exist for tradingday: {date_curr} expiryday: {expiry_date}")
                    # df = pd.DataFrame()

            except Exception as e:
                raise Exception(e)

        
        del self.lowest_level_options_df
        if len(self.intraday_options_dict[expiry_date]) != 0:
            try:
                self.lowest_level_options_df = self.intraday_options_dict[expiry_date].loc[timestamp]

            except Exception as e:
                self.lowest_level_options_df = pd.DataFrame()
                raise Exception(f"Data not found at time {timestamp} for expiry {expiry_date} :: {e}")

        else:
            self.lowest_level_options_df = pd.DataFrame()

    def __getOptionDetailedFromDF(self, ins: Option, timestamp: datetime)-> OptionDetailed:
        '''
        Fetches the detailed option values for a timestamp from the intraday dataframe

        None:
        All of the Exceptions are taken care by utils file.
        '''
        insDetailed = None

        if len(self.lowest_level_options_df) == 0:
            raise Exception(f"Data not available for the trading date {timestamp} and expiry date {ins.expiry.strftime(date_format)}.")

        insdf = self.lowest_level_options_df[(self.lowest_level_options_df['Strike'] == int(ins.strike)) & (self.lowest_level_options_df['ExpiryDate'] == ins.expiry.strftime(date_format)) & (self.lowest_level_options_df['Type'] == ins.opt_type) & (self.lowest_level_options_df['Instrument'] == ins.underlying)]
        
        # insdf = self.intraday_options_df.loc[timestamp][(self.intraday_options_df.loc[timestamp]['Strike'] == int(ins.strike)) & (self.intraday_options_df.loc[timestamp]['ExpiryDate'] == ins.expiry.strftime("%Y-%m-%d")) & (self.intraday_options_df.loc[timestamp]['Type'] == ins.opt_type) & (self.intraday_options_df.loc[timestamp]['Instrument'] == ins.underlying)]
        
        if len(insdf) == 0:
            raise Exception(f"No data found in market for instrument {ins.idKey()} for the {timestamp}.")

        insData = insdf.loc[timestamp]
        insDetailed = OptionDetailed(timestamp, insData['ExchToken'], insData['Strike'], pd.to_datetime(insData['ExpiryDateTime']).date(), insData['Instrument'], insData['Type'], insData['BidPrice'], insData['AskPrice'], insData['Delta'], insData['Theta'], insData['Gamma'], insData['Vega'], insData['Sigma'], insData['Spot'])
        # insDetailed = OptionDetailed(timestamp, insData['ExchToken'], insData['Strike'], pd.to_datetime(insData['ExpiryDateTime']).date(), insData['Instrument'], insData['Type'], insData['BidPrice'], insData['AskPrice'], insData['Delta'], insData['Theta'], insData['Gamma'], insData['Vega'], insData['Sigma'], self.getSpot(timestamp=timestamp))

        return insDetailed

    def __getFutureDetailedFromDF(self, ins: Future, timestamp: datetime)-> FutureDetailed:
        '''
        Fetches the detailed option values for a timestamp from the intraday dataframe

        None:
        All of the Exceptions are taken care by utils file.
        '''
        insDetailed = None

        if len(self.lowest_level_options_df) == 0:
            raise Exception(f"Data not available for the trading date {timestamp} and expiry date {ins.expiry.strftime(date_format)}.")

        # insdf = self.lowest_level_options_df[(self.lowest_level_options_df['Strike'] == int(ins.strike)) & (self.lowest_level_options_df['ExpiryDate'] == ins.expiry.strftime(date_format)) & (self.lowest_level_options_df['Type'] == ins.opt_type) & (self.lowest_level_options_df['Instrument'] == ins.underlying)]

        insdf = self.lowest_level_options_df
        
        # insdf = self.intraday_options_df.loc[timestamp][(self.intraday_options_df.loc[timestamp]['Strike'] == int(ins.strike)) & (self.intraday_options_df.loc[timestamp]['ExpiryDate'] == ins.expiry.strftime("%Y-%m-%d")) & (self.intraday_options_df.loc[timestamp]['Type'] == ins.opt_type) & (self.intraday_options_df.loc[timestamp]['Instrument'] == ins.underlying)]
        
        if len(insdf) == 0:
            raise Exception(f"No data found in market for instrument {ins.idKey()} for the {timestamp}.")

        # _logger.info(f"Type of insdf {type(insdf)}")
        # _logger.info(f"Type of insdf {(insdf[insdf['Type'] == 'ES'].loc[timestamp])}")
        if isinstance(insdf, pd.DataFrame):
            insdf = insdf[insdf['Type'] == 'ES'].loc[timestamp]

        # insData = insdf
        insData = insdf
        # print(insData)
        insDetailed = FutureDetailed(timestamp, insData['ExchToken'], insData['Strike'], pd.to_datetime(insData['ExpiryDateTime']).date(), insData['Instrument'], insData['Type'], insData['BidPrice'], insData['AskPrice'], insData['Delta'], insData['Theta'], insData['Gamma'], insData['Vega'], insData['Sigma'], insData['Spot'])
        # insDetailed = OptionDetailed(timestamp, insData['ExchToken'], insData['Strike'], pd.to_datetime(insData['ExpiryDateTime']).date(), insData['Instrument'], insData['Type'], insData['BidPrice'], insData['AskPrice'], insData['Delta'], insData['Theta'], insData['Gamma'], insData['Vega'], insData['Sigma'], self.getSpot(timestamp=timestamp))

        return insDetailed

    def __getInstrumentDetailsFromDF(self, ins: Instrument, timestamp: datetime) -> Instrument:
        '''
        Fetches detailed instrument values from intraday dataframe

        None:
        All of the Exceptions are taken care by utils file.
        '''
        insDetailed = None

        try:
            if ins.instrument_type == "option":
                insDetailed: Instrument = self.__getOptionDetailedFromDF(ins, timestamp)

            elif ins.instrument_type == "future":
                insDetailed: Instrument = self.__getFutureDetailedFromDF(ins, timestamp)

            if insDetailed == None:
                raise Exception("For instrument type data fetcher not implemented.")

        except Exception as e:
            # print(f"{timestamp} :: {e} :: {get_exception_line_no()}")
            raise e

        return insDetailed

    def getFutureDetailedFromDF(self, timestamp):
        return self.__getFutureDetailedFromDF(timestamp=timestamp, type='ES')

    def getAllInstrumentDetailsTable(self, timestamp: datetime, expiry_date: date) -> pd.DataFrame:
        '''
        For a timestamp and underlying returns all of the available options in a dataframe
        '''
        self.__checkAndReinitialiseDF(timestamp, expiry_date)
        return self.lowest_level_options_df

    # TODO: implement this to make code faster
    def getInstrumentDetailsList(self, insList: List[Instrument], timestamp: datetime, expiry_date: date) -> List[Instrument]:
        self.__checkAndInvalidateCache(timestamp, expiry_date)
        pass

# Not used
    def __getSpotFromDF(self) -> float:
        '''
        Fetches the spot price for a timestamp and underlying
        '''
        spot = None
        spot = round(float(self.lowest_level_options_df['Spot'].values[0]),2)
        return spot

    def __checkAndReinitialiseSpotDF(self, timestamp) -> None:
        curr_date = timestamp.date()

        if curr_date != self.spot_date:
            del self.intraday_spot_df

            filepath = os.path.join(self.option_data_dir, "Spot", get_spot_intraday_filename(self.underlying, curr_date))
            self.intraday_spot_df = pd.read_csv(filepath)

            self.intraday_spot_df['Date Time'] = pd.to_datetime(self.intraday_spot_df['Date Time'])
            
            self.intraday_spot_df.set_index('Date Time', inplace=True)
            # print("[DEBUG] Now using datetime index:")
            # print("[DEBUG] Min timestamp:", self.intraday_spot_df.index.min())
            # print("[DEBUG] Max timestamp:", self.intraday_spot_df.index.max())
            # print("[DEBUG] Queried timestamp:", timestamp)
            # print("[DEBUG] Does timestamp exist in index:", timestamp in self.intraday_spot_df.index)

            self.spot_date = curr_date

    def __checkAndReinitialiseRVDF(self, timestamp) -> None:
        curr_date = timestamp.date()

        if curr_date != self.rv_date:
            self.__checkAndReinitialiseSpotDF(timestamp)

            returns = self.intraday_spot_df['Spot'].pct_change().fillna(0)
            self.intraday_rv_df = returns.rolling(window=rv_window).std() * np.sqrt(annualizing_parameter)

            self.rv_date = curr_date

    def getRV(self, timestamp: datetime) -> float:
        '''
        Fetches rv for a timestamp
        '''
        try:
            self.__checkAndReinitialiseRVDF(timestamp)

            if timestamp != self.rv_datetime:
                self.rv = self.intraday_rv_df.loc[timestamp] if not pd.isna(self.intraday_rv_df.loc[timestamp]) else None

                self.rv_datetime = timestamp
        except Exception as e:
            logger.critical(f"Error :: TradingPlatform :: getRV :: {get_exception_line_no()} {e}")
        
        return self.rv
            
    def getInstrumentDetails(self, ins: Instrument, timestamp: datetime) -> Instrument:
        '''
        Fetches details of an instrument for a timestamp and instrument
        '''
        # try:
        self.__checkAndInvalidateCache(timestamp, expiry_date=ins.expiry)

        if ins.idKey() not in self.cache.keys():
            self.cache[ins.idKey()] = self.__getInstrumentDetailsFromDF(ins, timestamp)
        
        return self.cache[ins.idKey()]
        # except Exception as e:
        #     print(f"{timestamp} :: {ins.expiry} :: {ins.instrument_type} :: {e}")

    def getSpot(self, timestamp: datetime) -> float:
        '''
        Fetches spot for a timestamp
        '''
        try:
            self.__checkAndReinitialiseSpotDF(timestamp)

            # print("debug", timestamp)
            # print("debug2",self.spot_datetime)

            if timestamp != self.spot_datetime:
                self.is_spot_problem = self.is_future_price_problem(timestamp)

                if self.is_spot_problem:
                    self.spot = None
                else:
                    self.spot = round(self.intraday_spot_df.loc[timestamp]['Spot'], 2)
                    
                self.spot_datetime = timestamp
            # print("bugg",self.spot)
        except Exception as e:
            self.spot = None
            self.is_spot_problem = True
            self.spot_datetime = timestamp
            logger.critical(f"Error :: TradingPlatform :: getSpot :: {get_exception_line_no()} {e}")
        
        return self.spot

    def submitOrder(self, tradeList: List[Trade]):
        return tradeList

    def __checkAndInvalidateCache(self, timestamp:datetime, expiry_date: date, forceful: bool = False):
        '''
        invalidates caches after checking timestamp
        '''
        if forceful or timestamp != self.timestamp:# or expiry_date != self.expiry_date:
            self.cache.clear()
            self.timestamp = timestamp

        self.__checkAndReinitialiseDF(timestamp, expiry_date)
        
            # self.expiry_date = expiry_date

# Not used in any other module
    def getNearestExpiries(self, timestamp: datetime) -> List[date]:
        if (len(self.expiry_list) == 0):
            return []
        while timestamp.date() > self.expiry_list[0]:
            if (len(self.expiry_list) == 0):
                return []
            self.expiry_list.pop(0)
        return copy.copy(self.expiry_list)


    def get_expiry_list(self):
        return self.expiry_list


    def is_future_price_problem(self, timestamp: datetime) -> bool:
        try:
            if self.check_future_price: 
                spot_spike = self.__future_spot_spike(timestamp=timestamp, spot_move_threshold=self.spot_move_threshold)
                spot_missing = self.__future_spot_missing(timestamp=timestamp)

                if spot_spike or spot_missing:
                    return True
                else:
                    return False

            else:
                return False

        except Exception as e:
            print(f'Error in is_future_price_problem :: error line :: {get_exception_line_no()} :: msg :: {e}')

    def __future_spot_missing(self, timestamp: datetime) -> bool:
        try:
            self.intraday_spot_df.loc[timestamp]['Spot_Missing']

        except Exception as e:
            # print(f'Error in future_spot_missing :: error line :: {get_exception_line_no()} :: msg :: {e}')
            return True

    def __future_spot_spike(self, timestamp: datetime, spot_move_threshold:float) -> bool:
        try:
            prev_spot = self.intraday_spot_df.loc[timestamp]['Prev_Spot']
            curr_spot = self.intraday_spot_df.loc[timestamp]['Spot']
            spot_move = abs(((curr_spot - prev_spot)/prev_spot)*100)

            if spot_move > spot_move_threshold:
                return True
            else:
                return False

        except Exception as e:
            # print(f'Error in future_spot_spike :: error line :: {get_exception_line_no()} :: msg :: {e}')
            return True

    def is_option_price_problem(self, instrument: Instrument, timestamp: datetime) -> bool:
        """
        Return:
            - True : if the option has price problem
            - Falase : if the option has not price problem (Default)
        """
        try:
            # _logger.info(f"In price problem module")
            is_price_problem_list = []
            if self.check_option_prices and self.check_price_problem_start_time < timestamp.time(): # CHECK_PRICE_PROBLEM_START_TIME

                self.__checkAndReinitialiseDF(timestamp, instrument.expiry)
                ins_df = self.lowest_level_options_df[(self.lowest_level_options_df['Strike']==instrument.strike) & (self.lowest_level_options_df['Type']==instrument.opt_type)]

                if len(ins_df) != 0:
                    bid_ask_move, intrinsic_value, mid_price = ins_df[['bid_ask_move', 'Intrinsic_value', 'mid_price']].values[0]

                    if self.check_bid_ask: #CHECK_BID_ASK_SPREAD
                        is_price_problem_list.append(bid_ask_move > self.bid_ask_move_threshold)

                    if self.check_intrinsic_value: #CHECK_INTRINSIC_VALUE
                        is_price_problem_list.append(round(intrinsic_value, 2) >= round(mid_price, 2))

                    if sum(is_price_problem_list):
                        logger.warning(f"At time {timestamp} instrument {instrument.idKey()} :: bid_ask_problem {bid_ask_move > self.bid_ask_move_threshold} :: intrinsic_value_problem {round(intrinsic_value, 2) >= round(mid_price, 2)}")
                        return True
                    else:
                        return False

                # When Option is not present into the data
                else:
                    _logger.warning(f"At time {timestamp} instrument {instrument.idKey()} is missing")
                    return True

            else:
                return False

        except Exception as e:
            _logger.critical(f'Error in is_option_price_problem at time {timestamp}:: error line :: {get_exception_line_no()} :: msg :: {e}')
