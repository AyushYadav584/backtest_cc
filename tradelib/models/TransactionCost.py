from tradelib.tradelib_global_constants import exchange_fee_rate_option, exchange_fee_rate_future, exchange_commission, transaction_fee, underlying, future_multiplier
from datetime import datetime, time
from models import Trade

class TransactionCost:
    def __init__(self) -> None:
        self.total_cost = 0
        self.exchange_fee_rate_option = exchange_fee_rate_option
        self.exchange_fee_rate_future = exchange_fee_rate_future
        self.exchange_commission = exchange_commission

        self.transaction_cost_rate = transaction_fee
        self.cost_calculation_time = None


    def check_and_reinitialise_cost(self, timestamp:datetime):
        if self.cost_calculation_time != timestamp:
            self.total_cost = 0
            self.cost_calculation_time = timestamp

    def update_cost(self, value:float):
        self.total_cost += value

    def get_cost(self, timestamp:datetime) -> float:
        self.check_and_reinitialise_cost(timestamp=timestamp)
        return self.total_cost

    def calculate_exchange_cost_NSE(self, trade_position, trade_price):
        total_premium = abs(trade_position) * trade_price
        return total_premium * self.exchange_fee_rate_option

    def calculate_exchange_cost_CME(self, trade_position, instrument_type):
        cost = 0

        if instrument_type == 'option':
            # exchange commission
            cost += abs(trade_position)/future_multiplier * self.exchange_commission
            cost += abs(trade_position)/future_multiplier * self.exchange_fee_rate_option

        if instrument_type == 'future':
            # exchange commission
            cost += abs(trade_position) * self.exchange_commission
            cost += abs(trade_position) * self.exchange_fee_rate_future

        return cost


    def calculate_exchange_cost(self, trade_position, trade_price, instrument_type):
        if underlying in ["BANKNIFTY", "NIFTY", 'SBIN', "ASIANPAINT", "AXISBANK", "BHARTIARTL", "BAJFINANCE", "BAJAJAUTO"]:
            return self.calculate_exchange_cost_NSE(trade_position, trade_price)

        if underlying in ['SPXW']:
            return self.calculate_exchange_cost_CME(trade_position, instrument_type)

    def calculate_transaction_cost(self):
        return self.transaction_cost_rate
