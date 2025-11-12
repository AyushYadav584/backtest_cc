from datetime import datetime, date, time
from typing import List, Dict
from trading_platform._TradingPlatform import TradingPlatform
from tradelib.models.Instrument import Instrument
from tradelib.models.OptionDetailed import OptionDetailed
from tradelib.models.Option import Option
from tradelib.models.Trade import Trade
import os
import pandas as pd
from tradelib_logger import logger
from tradelib_global_constants import date_format, DIVIDEND_MAP, data_dir
from tradelib_utils import get_options_intraday_filename, get_expiry_dates_on_weekday, round_to_step, get_expiry_from_pre_process
import copy

# TODO: partial exceution allow or not
# TODO: allow underlying object pass

_logger = logger.getLogger("trading platform")
class BacktestTradingPlatform(TradingPlatform):
    def __init__(self, option_data_dir: str, risk_free_rate: float=None, steps: float=None,underlying: str=None, dividend: float=None) -> None:
        self.option_data_dir = option_data_dir
        super().__init__(underlying, dividend, steps, risk_free_rate)
        self.intraday_options_df: pd.Dataframe = None
        self.lowest_level_options_df: pd.DataFrame = None
        self.date: date = None
        self.timestamp: datetime = None
        self.cache: Dict[str, Instrument] = {} # this map caches the data from searching dataframe
        self.expiry_list = get_expiry_from_pre_process(data_dir=data_dir)#get_expiry_dates_on_weekday(option_data_dir, 'thursday')

    def __checkAndReinitialiseDF(self, timestamp:datetime) -> None:
        '''
        Reinitialised the intraday DF if the date is changed.
        '''
        date_curr: date = timestamp.date()

        if date_curr != self.date:
                try:
                    # reinitialise Options DF
                    del self.intraday_options_df
                    filepath = os.path.join(self.option_data_dir, get_options_intraday_filename(self.underlying, timestamp))
                    self.intraday_options_df = pd.read_csv(filepath)
                    if len(self.intraday_options_df) == 0:
                        raise Exception
                    self.intraday_options_df['Date Time'] = pd.to_datetime(self.intraday_options_df['Date Time'])
                    self.intraday_options_df.set_index('Date Time', inplace=True)

                    self.date = date_curr

                except Exception as e:
                    raise Exception("File not found for date:" + str(timestamp.date))
        try:
            del self.lowest_level_options_df
            self.lowest_level_options_df = self.intraday_options_df.loc[timestamp]
            if len(self.lowest_level_options_df) == 0:
                raise Exception
        except Exception as e:
            raise Exception("Not data found for timestamp: " + str(timestamp))
                
    def __getOptionDetailedFromDF(self, ins: Option, timestamp: datetime)-> OptionDetailed:
        '''
        Fetches the detailed option values for a timestamp from the intraday dataframe
        '''
        insDetailed = None

        insdf = self.lowest_level_options_df[(self.lowest_level_options_df['Strike'] == int(ins.strike)) & (self.lowest_level_options_df['ExpiryDate'] == ins.expiry.strftime(date_format)) & (self.lowest_level_options_df['Type'] == ins.opt_type) & (self.lowest_level_options_df['Instrument'] == ins.underlying)]
        
        # insdf = self.intraday_options_df.loc[timestamp][(self.intraday_options_df.loc[timestamp]['Strike'] == int(ins.strike)) & (self.intraday_options_df.loc[timestamp]['ExpiryDate'] == ins.expiry.strftime("%Y-%m-%d")) & (self.intraday_options_df.loc[timestamp]['Type'] == ins.opt_type) & (self.intraday_options_df.loc[timestamp]['Instrument'] == ins.underlying)]
        
        if len(insdf) == 0:
            raise Exception(f"No data found in market for instrument {ins.idKey()} for the timestamp.")
        
        insData = insdf.loc[timestamp]
        insDetailed = OptionDetailed(timestamp, insData['ExchToken'], insData['Strike'], pd.to_datetime(insData['ExpiryDateTime']).date(), insData['Instrument'], insData['Type'], insData['BidPrice'], insData['AskPrice'], insData['Delta'], insData['Theta'], insData['Gamma'], insData['Vega'], insData['Sigma'], insData['Spot'])

        return insDetailed

    def __getInstrumentDetailsFromDF(self, ins: Instrument, timestamp: datetime) -> Instrument:
        '''
        Fetches detailed instrument values from intraday dataframe
        '''
        insDetailed = None

        try:
            if ins.instrument_type == "option":
                insDetailed: Instrument = self.__getOptionDetailedFromDF(ins, timestamp)

            if insDetailed == None:
                raise Exception("For instrument type data fetcher not implemented.")
        except Exception as e:
            raise e

        return insDetailed

    def getAllInstrumentDetailsTable(self, timestamp: datetime) -> pd.DataFrame:
        '''
        For a timestamp and underlying returns all of the available options in a dataframe
        '''
        self.__checkAndReinitialiseDF(timestamp)
        return self.lowest_level_options_df

    # TODO: implement this to make code faster
    def getInstrumentDetailsList(self, insList: List[Instrument], timestamp: datetime) -> List[Instrument]:
        self.__checkAndInvalidateCache(timestamp)
        pass

    
    def __getSpotFromDF(self) -> float:
        '''
        Fetches the spot price for a timestamp and underlying
        '''
        spot = None
        spot = round(float(self.lowest_level_options_df['Spot'].values[0]),2)
        return spot


    def getInstrumentDetails(self, ins: Instrument, timestamp: datetime) -> Instrument:
        '''
        Fetches details of an instrument for a timestamp and instrument
        '''
        self.__checkAndInvalidateCache(timestamp)

        if ins.idKey() not in self.cache.keys():
            self.cache[ins.idKey()] = self.__getInstrumentDetailsFromDF(ins, timestamp)
        
        return self.cache[ins.idKey()]

    def getSpot(self, timestamp: datetime) -> float:
        '''
        Fetches spot for a timestamp
        '''
        self.__checkAndInvalidateCache(timestamp)
        if "SPOT" not in self.cache.keys():
            self.cache["SPOT"] = self.__getSpotFromDF()
        return self.cache["SPOT"]

    def submitOrder(self, tradeList: List[Trade]):
        return tradeList

    def __checkAndInvalidateCache(self, timestamp:datetime, forceful: bool = False):
        '''
        invalidates caches after checking timestamp
        '''
        if forceful or timestamp != self.timestamp:
            self.cache.clear()
            self.__checkAndReinitialiseDF(timestamp)
            self.timestamp = timestamp
    
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

