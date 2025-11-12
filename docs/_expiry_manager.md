# expiry_manager module

## Class
    class ExpiryManager()

It’s a helper class to manage dates 

## Methods

    def findDay(self, timestamp:datetime)->str:

Find Day for a given timestmap

Args:

- **timestamp (datetime):** date for which we need the day

Returns:

- **str:** Day of that date (Eg: Monday, Tuesday, ...)

<br>

    def get_next_trading_date(self, t:datetime)->datetime:

this function is responsible to return the next trading date. If `t` is a holiday then , move to next trading day.

Args:

- **t (datetime):** Date for which we need the next trading date.

Returns:

- **datetime:** Get the next trading date of the given date

<br>

    def day_data_exists(self, day:datetime) -> bool:

Check whather data exist for the given date

Args:

- **day (datetime):** Date for which we want to check data exist or not

Returns:

- **bool:** It's return True when data exist, otherwise it's return False

<br>

    def get_early_unwind_day(self, qtime:datetime, actual_expiry:datetime, expiry_type:str)->datetime:

This function return the early unwind day. If actual_expiry is holiday or data not available 

Args:

- **qtime (datetime):** Start date
- **actual_expiry (datetime):** Date of actual expiry
- **expiry_type (str):** Expiry type (weekly, monthly, nearest_weekly, nearest_monthly)

Returns:

- **datetime:** Expiry date

<br>

    def first_trading_day(self, time_stamp:datetime)->tuple:

This function check whather the given date is the first trading day or not

Args:

- **time_stamp (datetime):** Input date

Returns:

- **tuple:** It return (True, time_stamp) if the date is first trading day, otherwise it's return (False, time_stamp)

<br>

    def expiry_data_exists(self, data:pd.DataFrame, time_stamp: datetime, freq:str="nearest_weekly") -> bool:

This function is responsible to check the expiry data exist or not base on the expiry type 

Args:

- **data (pd.DataFrame):** Historical data based of expiry type
- **time_stamp (datetime):** First trading day  
- **freq (str, optional):** Expiry type. Defaults to "nearest_weekly".

Returns:

- **bool:** True if the expiry date exist. Otherwise False