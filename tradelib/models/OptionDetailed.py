from datetime import datetime, date
from tradelib.models.Option import Option
from tradelib_utils import moneyness_percentage

# TODO: for detailed models have name as same
class OptionDetailed(Option):
    def __init__(self, timestamp:datetime, id: str, strike: int, expiry: date, underlying: str, opt_type: str, bid: float, ask: float, delta:float, theta: float, gamma: float, vega: float, sigma: float, spot:float, mid=None) -> None:
        super().__init__(strike, expiry, underlying, opt_type)
        self.timestamp = timestamp
        self.underlying_spot = spot
        self.detailed = True
        self.id = id
        self.bid = bid
        self.ask = ask
        if mid == None:
            if ask != None and bid != None:
                self.mid =round((bid+ask)/2, 2)
            else:
                self.mid = None
        else:
            self.mid = mid
        self.delta = delta
        self.theta = theta
        self.gamma = gamma
        self.vega = vega
        self.sigma = sigma
        self.moneyness = moneyness_percentage(self.strike, self.underlying_spot, self.opt_type)