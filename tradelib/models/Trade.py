from tradelib.models import Instrument

class Trade:
    def __init__(self, ins: Instrument, pos: float, trade_sub_type='None') -> None:
        self.instrument = ins
        self.position = pos
        self.trade_sub_type = trade_sub_type