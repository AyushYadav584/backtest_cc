# main_v02 module


    def set_trading_start_time(input_date:datetime) -> datetime:
    
It's add the start time of the market with the given date

Args:

- **input_date (datetime):** Date without the start time

Returns:

- **datetime:** Date with start time

<br>

    def set_trading_end_time(input_date:datetime) -> datetime:
It's add the end time of the market with the given date

Args:

- **input_date (datetime):** Date without the end time

Returns:

- **datetime:** Date with end time

<br>

    def datetime_has_time(input_date:datetime) -> bool:

It check whater the input_date has time with it

Args:

- **input_date (datetime):** date

Returns:

- **bool:** It returns `True` when the date has time otherwise it return `False`

<br>

    def get_total_trading_units_of_a_day(interval_type:str='minutes') -> int:

It's calculate the total number of trading units for a trading day.

Args:

- **interval_type (str, optional):** Interval type. Defaults to `'minutes'`.

Returns:

- **int:** return total number of trading days when interval_type is known(`'minutes'`), `0` when interval_type is unknown.

<br>

    def process_single_expiry(start_date:datetime, end_date:datetime) -> None:

This function is responsible for conducting backtesting of a monthly or weekly expiry. 

Args:

- **start_date (datetime):** Start date of the trading period for a weekly or monthly expiry. 
- **end_date (datetime):** End date of the trading period for a weekly or monthly expiry. 

Raises:

- **Exception:** If anything goes wrong, raise an exception and store the error in the log file.

<br>

    def process(start_date:datetime, end_date:datetime) -> None:

This is a rapper function of process_single_expiry function to run the backtest in multi-processing.

Args:

- **start_date (datetime):** Start date of the trading period for a weekly or monthly expiry. 
- **end_date (datetime):** End date of the trading period for a weekly or monthly expiry. 
