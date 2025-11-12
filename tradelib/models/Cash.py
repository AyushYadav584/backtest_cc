from models.Instrument import Instrument
from datetime import datetime

class Cash(Instrument):
    def __init__(self, initial_cash: float) -> None:
        super().__init__("cash", underlying="cash")
        self.value: float = initial_cash
        
    def idKey(self):
        return "CASH"
    
    def addCash(self, cashChange: float):
        self.value += cashChange