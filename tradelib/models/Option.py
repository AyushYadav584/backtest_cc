from datetime import date
from tradelib.models.Instrument import Instrument
from tradelib_global_constants import DIVIDEND_MAP, date_format_no_dash

class Option(Instrument):
    def __init__(self, strike: int, expiry: date, underlying: str, opt_type: str, instrument_type: str="option") -> None:
        super().__init__(instrument_type, underlying)
        self.strike = int(strike)
        self.expiry = expiry
        self.dividend_rate = DIVIDEND_MAP[self.underlying]
        self.opt_type = opt_type

    def idKey(self):
        exp_str = self.expiry.strftime(date_format_no_dash)
        return f"{self.underlying.upper()}_{str(self.strike)}_{self.opt_type.upper()}_{exp_str}"

