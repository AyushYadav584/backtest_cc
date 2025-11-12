from abc import ABC, abstractmethod
from datetime import datetime

class Instrument(ABC):
    def __init__(self, instrument_type: str, underlying: str, isDetailed: bool=False) -> None:
        super().__init__()
        self.detailed = isDetailed
        self.instrument_type = instrument_type
        self.underlying = underlying

    @abstractmethod
    def idKey(self):
        pass