from abc import ABC, abstractmethod
from typing import List
from datetime import datetime, date
import pandas as pd
import inspect
import os

from tradelib.models.Instrument import Instrument
from tradelib.models.Trade import Trade
from tradelib_utils import get_underlying_from_data_dir
from tradelib_global_constants import DIVIDEND_MAP, STEPS_MAP, RISK_FREE_RATE, exchange_start_time, exchange_end_time, unit_size

class TradingPlatform(ABC):
    def __init__(self, underlying: str, dividend: float, steps: float, risk_free_rate: float) -> None:
        frame = inspect.stack()[1]
        filename = os.path.abspath(frame.filename)
        lineno = frame.lineno
        classname = self.__class__.__name__

        # print(f"[DEBUG] Instantiated class: {classname}")
        # print(f"[DEBUG] Instantiated at: {filename}:{lineno}")




        super().__init__()
        self.underlying = underlying if underlying != None else get_underlying_from_data_dir(self.option_data_dir)
        self.dividend = dividend if underlying != None else DIVIDEND_MAP[self.underlying]
        self.exchange_start_time = exchange_start_time
        self.exchange_end_time = exchange_end_time
        self.risk_free_rate = risk_free_rate if risk_free_rate != None else RISK_FREE_RATE
        self.steps = steps if steps != None else STEPS_MAP[self.underlying]
        self.unit_size = unit_size

    @abstractmethod
    def getSpot(self, timestamp: datetime)->float:
        pass

    @abstractmethod
    def getRV(self, timestamp: datetime)->float:
        pass

    @abstractmethod
    def submitOrder(self, tradeList: List[Trade]) -> None:
        pass

    @abstractmethod
    def getInstrumentDetails(self, ins: Instrument, timestamp: datetime) -> Instrument:
        pass

    @abstractmethod
    def getInstrumentDetailsList(self, insList: List[Instrument], timestamp: datetime) -> List[Instrument]:
        pass

    @abstractmethod
    def getAllInstrumentDetailsTable(self, timestamp: datetime, underlying: str, expiry_date: date) -> pd.DataFrame:
        pass

    @abstractmethod
    def getNearestExpiries(self, timestamp: datetime) -> List[date]:
        pass

    @abstractmethod
    def is_option_price_problem(self, instrument: Instrument, timestamp: datetime) -> bool:
        pass

    @abstractmethod
    def is_future_price_problem(self, timestamp: datetime) -> bool:
        pass