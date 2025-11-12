from datetime import datetime
from trading_platform import TradingPlatform
from models.Portfolio import Portfolio
from tradelib_logger import logger
from tradelib_utils import round_to_step
from models.Option import Option
from models.OptionDetailed import OptionDetailed
from tradelib_trade_utils import get_atm_option, get_expiry_date, get_atm_iv
from tradelib_global_constants import date_time_format, expiry_info

_logger = logger.getLogger("backtest_entry")

class BacktestEntry:
    def __init__(self, timestamp: datetime, trade_done: bool, portfolio: Portfolio, trading_platform: TradingPlatform, m2m_side:str) -> None:
        self.timestamp = timestamp
        self.trade_done = trade_done
        self.spot = trading_platform.getSpot(timestamp)
        # nearest_expiry = get_expiry_date(timestamp, expiry_info, trading_platform, logger)
        self.m2m_side = m2m_side

        self.atmIv = get_atm_iv(trading_platform=trading_platform, timestamp=timestamp, _logger =_logger)

        if not self.trade_done:
            portfolio.updatePortfolioWithCorrectPrices(timestamp=timestamp)

        portfolio_greeks = portfolio.getPortfolioGreeks(timestamp)
        self.delta = portfolio_greeks.delta
        self.gamma = portfolio_greeks.gamma
        self.vega = portfolio_greeks.vega
        self.theta = portfolio_greeks.theta
        self.sigma = portfolio_greeks.sigma
        self.total_contracts = portfolio.getContractSize()
        self.cash = portfolio.cash.value
        self.instrumentsM2m = portfolio.getMarkToMarket(timestamp, m2m_side=self.m2m_side)
        self.pval = self.cash + self.instrumentsM2m
        self.transaction_fees = portfolio.transaction_fees.get_cost(timestamp=timestamp)
        self.RV = trading_platform.getRV(timestamp=timestamp)

        _logger.info(f"Inside BacktestEntry - timestamp : {timestamp}, ATM-IV: {self.atmIv}, Spot: {self.spot}")