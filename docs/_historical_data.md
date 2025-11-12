# historical_data module

## Class

    class HistoricalData

This class helps us to deal with the raw data.

Args:

- **source : str :** source of the data 
- **name : str :** name of historical data 
- **underlying_instrument : str :** name of the underlying instrument 
- **start_date : datetime :** start date 
- **end_date : datetime :** end date 
- **expiry_type : str :** monthly or weekly

## Methods

    def get_total_trading_days(self) -> int:

It's calculate the total number of trading days for which data is available

Returns:

- **int:** The total number of trading days

<br>

    def day_data_availabile(self, cdate:datetime) -> bool:

Check the data availability in the given date 

Args:

- **cdate (datetime):** Date for which we want to check the data availability

Returns:

- **bool:** Return True when data available, otherwise it return False

<br>

    def getSlice(self,t:datetime):
        
It's slice the historical data based on the given date. It also stores current slice data.

Args:

- **t (datetime):** Date for which we need the historical data 

Raises:

- **Exception:** If anything goes wrong. It logs the error into the log file.

Returns:

- **HistoricalData:** Sliced HistoricalData Object

<br>

    def get_greeks_by_id(self, exch_token:int) -> np.array:
        
It calculates the option greeks based on the given instrument id. 

Args:

- **exch_token (int):** Instrument ID

Raises:
    
- **Exception:** If Data not found for the given `exch_token`

Returns:

- **np.array:** Array with the option greeks (Delta, Theta, Gamma, Vega)

<br>

    def get_delta_by_id(self, exch_token:int) -> float:

It calculates the delta based on the given instrument id.

Args:

- **exch_token (int):** Instrument ID

Raises:
    
- **Exception:** If Data not found for the given `exch_token`

Returns:

- **float:** Delta of the given instrument id.

<br>

    def get_nearest_strike_premium(self, strike: float, option_type: str) -> tuple:

It's find the nearest strike instrument details based on `strike` and `option_type`.

Args:

- **strike (float):** Strike price of the option. 
- **option_type (str):** Type of option ("call" or "put") 

Returns:

- **tuple:** Instrument details (ExchToken, BidPrice, BidQty, AskPrice, AskQty, Strike)

<br>

    def get_exercise_list(self, qtime:datetime) -> list: 

This function calculates the list of exercise dates, based on the given `ctime`.

Args:

- **qtime (datetime):** Time for which we need the exercise dates

Returns:

- **list:** list of dates

<br>

    def get_specific_expiry(self, expiry_list : list, expiry_type :str = 'weekly') -> list:
        """
It find list of expiry dates, for the given `expiry_type`. 

Args:

- **expiry_list (list):** List of expiry
- **expiry_type (str, optional):** type of expiry. Defaults to `weekly`. (it can be `weekly`, `monthly`, `nearest_weekly, nearest_monthly`, `second_weekly`, `second_monthly`)

Returns:

- **list:** A list of expiry date, for the given expiry type.

<br>

    def load_processed_data(self, start_time:datetime=None, end_time:datetime=None) -> None:

This function load the processed data file between `start_time` and the `end_time`.

Args:

- **start_time (datetime, optional):** Start time. Defaults to None.
- **end_time (datetime, optional):** End time. Defaults to None.

<br>

    def load_market_data(self):

It helps us to load the market data based on the `self._expiry_type`.

<br>

    def get_quote(self, t: datetime, option_type: str, expiry: list, strike: int)-> tuple:
        
This function create a tuple which contains bid price, bid qty, ask price, ask qty respectively. 

Args:

- **t (datetime):** Date
- **option_type (str):** Type of option (eg: `CE`, `PE`)
- **expiry (list):** Expiry date time
- **strike (int):** Strike price

Raises:

- **NoOptionsFound:** If there is no option at the given time `t`

Returns:

- **tuple:** a tuple which contains `BidPrice`, `BidQty`, `AskPrice`, `AskQty` respectively.

<br>

    def get_quote_by_id(self, t, instrument_id:int)-> tuple:

This function create a tuple which contains bid price, bid qty, ask price, ask qty respectively based on `instrument_id`

Args:

- **instrument_id (int):** Instrument ID

Raises:

- **NoOptionsFound:** If there is no option at the given time `t`

Returns:

- **tuple:** a tuple which contains `BidPrice`, `BidQty`, `AskPrice`, `AskQty` respectively

<br>

    def get_option_detail_from_id(self, id: int) -> tuple:
        
It return the option detail based on instrument id

Args:

- **id (int):** Instrument ID

Raises:

- **NoOptionsFound:** If there is no option available.

Returns:

tuple: a tuple which consists `Strike` , `ExpiryDateTime`, `Option_Type`  respectively.

<br>

    def get_option_dtls_from_id_list(self, id_list: list) -> list:

It return the option details of the given instrument id list.

Args:

- **id_list (list):** List of instrument ID

Raises:

- **NoOptionsFound:** If there is no option available.

Returns:

- **list:** A list of tuple which consists `Strike`, `ExpiryDateTime`, `Option_Type` respectively.

    def get_max_expiry_from_options(self, id_list:list) -> datetime:

It calculate the maximum expiry datetime from the given instrument id list. 

Args:

- **id_list (list):** List of Instrument ID

Returns:

- **datetime:** Date where get the maximum expiry.

<br>

    def get_spot_v2(self, ctime:datetime):
        
Calculates the spot price. first it calculate the average of the maximum spot bid price and the minimum spot ask price and returns this average.

Returns:
    
- **float :** spot price

<br>

    def get_atm_option(self, qtime:datetime, underlying:str, expiry:datetime, option_type:str) -> tuple:
        """
It finds the details of the ATM option

Args:

- **underlying (str):** Name of underlying instrument  
- **expiry (datetime):** Expiry date for which the ATM option is being searched. 
- **option_type (str):** Type of option (`CE` or `PE`)

Raises:

- **NoOptionsFound:** If there is no option available.

Returns:

- **tuple:** tuple which consists `Strike`, `expiry`, `instrument`, `instrument_id` respectively.

<br>

    def get_otm_option(self, qtime:datetime, atm_strike:float, underlying:str, expiry:datetime, option_type:str, pct:float):

It finds the details of the OTM option

Args:

- **qtime (datetime):** Query time for which the OTM option is sought.
- **atm_strike (float):** ATM strike price.
- **expiry (datetime):** Expiry date for which the OTM option is being searched.
- **option_type (str):** Type of option (`CE` or `PE`)
- **pct (float):** OTM percentage

Raises:

- **NoOptionsFound:** If there is no option available.

Returns:

- **tuple:** tuple which consists `Strike`, `expiry`, `instrument`, `instrument_id` respectively.

<br>

    def check_otm_tolerance(self, type:str, atm_strike:int, otm_strike:int, tolerance:int) -> bool:

Checks whether otm_strike found is within tolerance range

Args:

- **type (str):** Option type (`CE` or `PE`)
- **atm_strike (int):** ATM strike price
- **otm_strike (int):** OTM strike price
- **tolerance (int):** Tolerance limit

Returns:

- **bool:** True when otm_strike within tolerance range otherwise it is False

<br>

    def new_preprocessing(self, path: str):

Method to drop atm call and put option price below a threshold compute the spot, delta, gamma, vega , theta and dump into a csv file

Args:

- **path (str):** Path where we have to save the preprocess data

Returns:

- **pd.DataFrame :** Preprocess dataframe