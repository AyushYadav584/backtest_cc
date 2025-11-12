from models.BacktestEntry import BacktestEntry
from typing import List
from models.Portfolio import Portfolio
from trading_platform import TradingPlatform
from datetime import datetime
from tradelib_utils import get_backtest_filename
import os
import csv

class Backtest:
    def __init__(self, portfolio: Portfolio, trading_platform: TradingPlatform, output_dir: str) -> None:
        self.portfolio = portfolio
        self.backtest_dir = os.path.join(output_dir, 'backtest')
        os.makedirs(self.backtest_dir, exist_ok=True)
        self.trading_platform = trading_platform
        self.backtest_list: List[BacktestEntry] = []

    def addBacktestEntry(self, timestamp:datetime, trade_done: bool, m2m_side:str):
        self.backtest_list.append(BacktestEntry(timestamp, trade_done, self.portfolio, self.trading_platform, m2m_side))

    def saveToCsvAndClear(self, date):
        filename = get_backtest_filename(date)
        file_path = os.path.join(self.backtest_dir, filename)
        with open(file_path, "w") as fp:
            writer = csv.writer(fp)
            writer.writerow(['timestamp', 'trade_done', 'spot', 'atm_iv', 'portfolio_delta', 'portfolio_gamma', 'portfolio_vega', 'portfolio_theta', 'portfolio_sigma', 'portfolio_cash', 'instruments_mtm', 'portfolio_value', 'total_contracts','transaction_fees'])

            for backtestEntry in self.backtest_list:
                writer.writerow([backtestEntry.timestamp, backtestEntry.trade_done, backtestEntry.spot, backtestEntry.atmIv, backtestEntry.delta, backtestEntry.gamma, backtestEntry.vega, backtestEntry.theta, backtestEntry.sigma, backtestEntry.cash, backtestEntry.instrumentsM2m, backtestEntry.pval, backtestEntry.total_contracts, backtestEntry.transaction_fees])

        self.backtest_list.clear()

    # def saveToCsvAndClear(self, date):
    #         filename = get_backtest_filename(date)
    #         file_path = os.path.join(self.backtest_dir, filename)
    #         with open(file_path, "w") as fp:
    #             writer = csv.writer(fp)
    #             writer.writerow(['timestamp', 'trade_done', 'spot', 'atm_iv', 'RV','portfolio_delta', 'portfolio_gamma', 'portfolio_vega', 'portfolio_theta', 'portfolio_sigma', 'portfolio_cash', 'instruments_mtm', 'portfolio_value', 'total_contracts'])
    
    #             for backtestEntry in self.backtest_list:
    #                 writer.writerow([backtestEntry.timestamp, backtestEntry.trade_done, backtestEntry.spot, backtestEntry.atmIv,backtestEntry.RV, backtestEntry.delta, backtestEntry.gamma, backtestEntry.vega, backtestEntry.theta, backtestEntry.sigma, backtestEntry.cash, backtestEntry.instrumentsM2m, backtestEntry.pval, backtestEntry.total_contracts])
    
    #         self.backtest_list.clear()
 
