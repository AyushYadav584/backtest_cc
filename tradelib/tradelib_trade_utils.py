from trading_platform import TradingPlatform
from datetime import date, datetime, time, timedelta
from typing import List, Tuple, Optional
from models.Option import Option
from models.Future import Future
from models.OptionDetailed import OptionDetailed
from models.FutureDetailed import FutureDetailed
from logging import Logger
from tradelib_utils import moneyness_percentage, round_to_step
from tradelib_global_constants import HARD_LIMIT, unwind_time, expiry_info
import pandas as pd
from tradelib_utils import get_theoretical_date, get_unwind_date_for_an_expiry, get_exception_line_no

import warnings

# Ignore the SettingWithCopyWarning
warnings.filterwarnings("ignore")


def get_nearest_strike_option(trading_platform: TradingPlatform, price: float, _logger: Logger, opt_type:str, nearest_expiry_date: date, underlying: str, timestamp: datetime) -> OptionDetailed:
    opt: OptionDetailed = None
    i = 0
    steps = trading_platform.steps
    rounded_price = round_to_step(price, steps)
    while opt == None and i <= HARD_LIMIT:
        i += 1
        try:
            if (i == 1):
                try:
                    opt = trading_platform.getInstrumentDetails(Option(strike=rounded_price, expiry=nearest_expiry_date, underlying=underlying, opt_type=opt_type), timestamp)
                except:
                    opt = None
                
                if opt == None:
                    _logger.debug(f"{opt_type} Options with strike {rounded_price} not found")
            else:
                upper_price = rounded_price+steps*(i-1)
                lower_price = rounded_price-steps*(i-1)
                try:
                    opt1: OptionDetailed = trading_platform.getInstrumentDetails(Option(upper_price, nearest_expiry_date, underlying, opt_type), timestamp)
                except:
                    opt1 = None

                try:
                    opt2: OptionDetailed = trading_platform.getInstrumentDetails(Option(lower_price, nearest_expiry_date, underlying, opt_type), timestamp)
                except:
                    opt2 = None

                if (opt1 == None) ^ (opt2 == None):
                    opt = opt1 if opt1 != None else opt2
                    not_found_strike = upper_price + lower_price - opt.strike
                    _logger.debug(f"{opt_type} Option with strike {opt.strike} found, but with strike {not_found_strike} not found")
                elif opt1 == None and opt2 == None:
                    _logger.debug(f"{opt_type} Options with strikes {upper_price}, {lower_price} not found")
                    continue
                else:
                    _logger.debug(f"{opt_type} Options with strikes {opt1.strike}, {opt2.strike} found")
                    if abs(opt1.strike - price) < abs(opt2.strike - price):
                        opt = opt1
                    else:
                        opt = opt2
                _logger.info(f"{opt_type} Option with strike {opt.strike} chosen as closest to price {price}")
        except Exception as e:
            _logger.critical("something went wrong with function: get_nearest_strike_option (tradelib/tradelib_trade_utils)")
            raise e
    if opt != None:
        return opt
    else:
        _logger.warning(f"No {opt_type} Option near {price} found with price variation: {steps*(i-1)}")
        raise Exception((f"No {opt_type} Option near {price} found with price variation: {steps*(i-1)}"))


def get_atm_option(trading_platform: TradingPlatform, underlying: str, spot:float, opt_type: str, nearest_expiry_date: date, steps:float, timestamp: datetime, _logger: Logger) -> OptionDetailed:
    try:
        atm = get_nearest_strike_option(trading_platform, spot, _logger, opt_type, nearest_expiry_date, underlying, timestamp)
        _logger.debug(f"ATM {opt_type} Found, Moneyness Percentage: {atm.moneyness}, strike: {atm.strike}")
        return atm
    except Exception as e:
        _logger.critical(f"No ATM {opt_type} found")
        return None

def get_static_otm_option(trading_platform: TradingPlatform, underlying: str, atm_strike:int, outstrike: float, steps:float, tolerance: bool, strict_tolerance: bool, opt_type: str, nearest_expiry_date: date,timestamp: datetime, _logger: Logger) -> Tuple[OptionDetailed, OptionDetailed]:
    cal_sign = 1 if opt_type == "PE" else -1
    otm_strike = round_to_step(atm_strike - (cal_sign)*atm_strike*(outstrike/100), steps)

    otm = None
    step_to_look = 0
    while otm == None and cal_sign*(otm_strike + (cal_sign)*step_to_look) < cal_sign*atm_strike: #TODO
        if strict_tolerance and (step_to_look/otm_strike) * 100 > tolerance:
            _logger.debug(f"otm {opt_type} not found within tolerance({tolerance}%), and strict tolerance is on")
            break

        try:
            otm: OptionDetailed = trading_platform.getInstrumentDetails(Option(strike=otm_strike+(cal_sign)*step_to_look, expiry=nearest_expiry_date, underlying=underlying, opt_type=opt_type), timestamp)
        except:
            try:
                if (step_to_look == 0):
                    raise Exception
                _logger.debug(f"OTM {opt_type} not found, with strike: {otm_strike+(cal_sign)*step_to_look}")
                otm: OptionDetailed = trading_platform.getInstrumentDetails(Option(strike=otm_strike-(cal_sign)*step_to_look, expiry=nearest_expiry_date, underlying=underlying, opt_type=opt_type), timestamp)
            except:
                _logger.debug(f"OTM {opt_type} not found, with strike: {otm_strike-(cal_sign)*step_to_look}")
                _logger.debug(f"OTM {opt_type} not found, with step_to_look: {step_to_look}")
                step_to_look += steps
                continue

    if otm != None:
        _logger.info(f"OTM {opt_type} Found, Strike: {otm.strike} Moneyness Percentage: {otm.moneyness}, tolerance: {round(abs(otm_strike-otm.strike)/otm_strike, 2)}")
    else:
        _logger.debug(f"OTM {opt_type} not found")

    return otm


def get_static_otm_option_by_price(trading_platform: TradingPlatform,
                                underlying: str,
                                target_price: float,
                                tolerance: float,
                                strict_tolerance: bool,
                                opt_type: str,
                                nearest_expiry_date: date,
                                timestamp: datetime,
                                _logger: Logger) -> OptionDetailed:
    """
    Finds the OTM option whose market price (mid) is closest to the target price.
    Uses the BacktestTradingPlatform's option table directly instead of looping strikes.
    """

    try:
        # Get full intraday option table for timestamp and expiry
        df = trading_platform.getAllInstrumentDetailsTable(timestamp, nearest_expiry_date)
        if df.empty:
            _logger.warning(f"No option data found for {underlying} {nearest_expiry_date} at {timestamp}")
            return None

        # Filter for the given option type
        df = df[df["Type"] == opt_type]

        # Compute mid price if not present
        # if "mid_price" in df.columns:
        #     df["mid"] = df["mid_price"]
        # else:
        df["mid"] = (df["BidPrice"] + df["AskPrice"]) / 2

        # Drop invalid prices
        df = df[df["mid"] > 0]


        if df.empty:
            _logger.warning(f"No valid prices for {opt_type} options at {timestamp}")
            return None

        # Compute absolute difference from target price
        df["price_diff"] = (df["mid"] - target_price).abs()

        # _logger.debug(df[["Strike", "mid", "price_diff"]].sort_values("price_diff").head(10))
        # Get best match
        try:
            best_row = df.sort_values("price_diff", ascending=True).iloc[0]
            diff = float(best_row["price_diff"])
        except Exception as e:
            print("Error selecting best row:", e)
            return None

        # print(type(best_row), type(diff))

        # Enforce tolerance if required
        if strict_tolerance and diff > tolerance:
            _logger.warning(f"No {opt_type} option found within strict tolerance {tolerance}. Closest diff={round(diff,2)}")
            return None

        # Create an OptionDetailed object for the found option
        opt = Option(strike=float(best_row["Strike"]),
                    expiry=nearest_expiry_date,
                    underlying=underlying,
                    opt_type=opt_type)

        best_opt = trading_platform.getInstrumentDetails(opt, timestamp)

        _logger.info(f"{opt_type} Option Found: Strike={best_opt.strike}, "
                    f"Price={best_opt.mid}, Target={target_price}, Diff={round(diff,2)}")

        return best_opt

    except Exception as e:
        _logger.error(f"Error in get_static_otm_option_by_price: {e}")
        return None

def find_options_with_target_premium(trading_platform: TradingPlatform, underlying: str, target_price: float, expiry_date: date, timestamp: datetime, logger) -> Optional[Tuple[OptionDetailed, OptionDetailed]]:
    """
    Finds a call and put option such that the sum of their premiums equals the target price
    and their absolute deltas are the same.

    Args:
        trading_platform: The trading platform object to fetch option details.
        underlying (str): The underlying asset.
        target_price (float): The target sum of premiums for the call and put options.
        expiry_date (date): The expiry date of the options.
        timestamp (datetime): The current timestamp.
        logger: Logger object for logging.

    Returns:
        Tuple[OptionDetailed, OptionDetailed]: A tuple containing the call and put options.
        None: If no such options are found.
    """
    try:
        # Fetch all available options for the given expiry and timestamp
        options_df = trading_platform.getAllInstrumentDetailsTable(timestamp=timestamp, expiry_date=expiry_date)

        if options_df.empty:
            logger.warning(f"No options data available for expiry {expiry_date} at {timestamp}")
            return None

        # Filter call and put options
        # print(options_df.columns)

        options_df['MidPrice'] = (options_df['BidPrice'] + options_df['AskPrice']) / 2

        call_options = options_df[options_df['Type'] == 'CE']
        put_options = options_df[options_df['Type'] == 'PE']

        # Iterate through call and put options to find a matching pair
        for _, call_row in call_options.iterrows():
            for _, put_row in put_options.iterrows():
                # Check if the absolute deltas are the same
                if abs(abs(call_row['Delta']) - abs(put_row['Delta'])) <= 0.01:
                    # Check if the sum of premiums matches the target price
                    # print('exec 224')
                    premium_sum = call_row['MidPrice'] + put_row['MidPrice']
                    # print('exec 226')
                    if abs(premium_sum - target_price) <= target_price/10 :  # Allow small tolerance
                        # Create OptionDetailed objects for the matching options
                        # print('exec 233')
                        call_option: OptionDetailed = trading_platform.getInstrumentDetails(Option(strike=call_row['Strike'], expiry=pd.to_datetime(call_row['ExpiryDateTime']).date(), underlying=underlying, opt_type="CE"), timestamp)

                        put_option: OptionDetailed = trading_platform.getInstrumentDetails(Option(strike=put_row['Strike'], expiry=pd.to_datetime(put_row['ExpiryDateTime']).date(), underlying=underlying, opt_type="PE"), timestamp)
                        logger.info(f"Found options: Call={call_option.strike}, Put={put_option.strike}, Premium Sum={premium_sum}")
                        # print('exec270')
                        return call_option, put_option

        logger.warning(f"No options found with target premium sum {target_price}")
        return None

    except Exception as e:
        logger.critical(f"Error in find_options_with_target_premium: {e}")
        return None


# TODO: check tolerance should be added or not
def get_nearest_strike_option_towards_atm(trading_platform: TradingPlatform, strike: float, _logger: Logger, opt_type:str, nearest_expiry_date: date, underlying: str, timestamp: datetime, atm_strike: float) -> OptionDetailed:
    steps = trading_platform.steps
    cal_sign = 1 if opt_type == "PE" else -1
    opt = None
    step_to_look = steps
    while opt == None and cal_sign*(strike + (cal_sign)*step_to_look) < cal_sign*atm_strike: #TODO
        try:
            opt: OptionDetailed = trading_platform.getInstrumentDetails(Option(strike=strike+(cal_sign)*step_to_look, expiry=nearest_expiry_date, underlying=underlying, opt_type=opt_type), timestamp)
        except:
            try:
                _logger.debug(f"Option {opt_type} not found, with strike: {strike+(cal_sign)*step_to_look}")
                opt: OptionDetailed = trading_platform.getInstrumentDetails(Option(strike=strike-(cal_sign)*step_to_look, expiry=nearest_expiry_date, underlying=underlying, opt_type=opt_type), timestamp)
            except:
                _logger.debug(f"Option {opt_type} not found, with strike: {strike-(cal_sign)*step_to_look}")
                _logger.debug(f"Option {opt_type} not found, with step_to_look: {step_to_look}")
                step_to_look += steps
                continue

    if opt != None:
        _logger.info(f"Nearset Option {opt_type} Found, Strike: {opt.strike} Moneyness Percentage: {opt.moneyness}, tolerance: {round(abs(strike-opt.strike)/strike, 2)}")
    else:
        _logger.debug(f"No nearest Option {opt_type} found near {strike}, have crossed ATM, thus skipping.")

    return opt

def get_delta_based_otm_option(trading_platform: TradingPlatform, underlying: str, delta_outstrike: float, tolerance: int, strict_tolerance: bool, opt_type: str, nearest_expiry_date: date,timestamp: datetime, _logger: Logger) -> OptionDetailed:

    cal_sign = 1 if opt_type == "CE" else -1

    data = trading_platform.getAllInstrumentDetailsTable(timestamp=timestamp, expiry_date=nearest_expiry_date)

    data = data.loc[(data['Type']==opt_type)]
    # if we want to use tolerance
    if strict_tolerance:
        delta_upper_limit = cal_sign * (delta_outstrike/100) + (tolerance/100)
        delta_lower_limit = cal_sign * (delta_outstrike/100) - (tolerance/100)

        data = data.loc[(data['Delta']>=delta_lower_limit) & (data['Delta']<=delta_upper_limit)]

    data.loc[:, "Delta Difference"] = abs(abs(data['Delta']) - (delta_outstrike/100)).values

    try:
        searched_data = data.sort_values(by="Delta Difference").iloc[0]

        otm: OptionDetailed = OptionDetailed(timestamp=timestamp, 
                                                id=searched_data['ExchToken'], 
                                                strike=searched_data['Strike'], 
                                                expiry=nearest_expiry_date, 
                                                underlying=underlying, 
                                                opt_type=opt_type, 
                                                bid=searched_data['BidPrice'], 
                                                ask=searched_data['AskPrice'], 
                                                delta=searched_data['Delta'], 
                                                theta=searched_data['Theta'], 
                                                gamma=searched_data['Gamma'], 
                                                vega=searched_data['Vega'], 
                                                sigma=searched_data['Sigma'], 
                                                spot=searched_data['Spot']
                                                )

    except:
        otm = None


    if otm != None:
        _logger.info(f"OTM {otm.opt_type} Found, Strike: {otm.strike} Moneyness Percentage: {otm.moneyness} Delta: {otm.delta}")
    else:
        _logger.debug(f"OTM {opt_type} not found")

    return otm


def get_actual_expiry_dates(theoretical_dates_dict: dict, trading_platform: TradingPlatform):
    # get explist
    expiry_date_list = trading_platform.get_expiry_list()

    actual_expiry_date_dict = {}

    for theo_day in theoretical_dates_dict.keys():
        collected_list = []

        for date in theoretical_dates_dict[theo_day]:
            if date in expiry_date_list:
                collected_list.append(date)

            else:
                collected_list.append(None)

        actual_expiry_date_dict[theo_day] = collected_list

    return actual_expiry_date_dict

def get_early_expiry_date(theoretical_expiry_date: date, current_date: date, trading_platform: TradingPlatform, _logger: Logger):
    
    # get explist
    expiry_date_list = trading_platform.get_expiry_list()
    # expiry_date_list = expiry_date_set

    if theoretical_expiry_date in expiry_date_list:
        return theoretical_expiry_date
    
    else:
        # print(f"{date} is not a expiry dates. Searching for a nearest expiry.")
        counter = 0
        date1 = theoretical_expiry_date
        while counter < 7:
            date1 = date1 - timedelta(days=1)

            if date1 < current_date:
                _logger.info(f"Found no expiry date For {theoretical_expiry_date}")
                # collected_list.append(None)
                return None

            if date1 in expiry_date_list:
                _logger.info(f"Found nearest expiry date For {theoretical_expiry_date} as {date1}")
                # is_run = False

                return date1

            counter += 1
            
        _logger.critical(f"Found no expiry date For {theoretical_expiry_date}")
        return None


def get_late_expiry_date(theoretical_expiry_date, trading_platform: TradingPlatform, _logger: Logger):

    # get explist
    expiry_date_list = trading_platform.get_expiry_list()
    # expiry_date_list = expiry_date_set

    if theoretical_expiry_date in expiry_date_list:
        return theoretical_expiry_date
    
    else:
        # print(f"{date} is not a expiry dates. Searching for a nearest expiry.")
        counter = 0
        date1 = theoretical_expiry_date
        while counter < 7:
            date1 = date1 + timedelta(days=1)

            if date1 in expiry_date_list:
                _logger.info(f"Found nearest expiry date For {theoretical_expiry_date} as {date1}")

                return date1

            counter += 1

        _logger.critical(f"Found no expiry date For {theoretical_expiry_date}")
        return None


def is_trading_date(date: date, trading_platform: TradingPlatform) -> bool:
    return date in trading_platform.trading_date_list

def get_expiry_date(timestamp: datetime, expiry_info, trading_platform, _logger):

    theoretical_dates = get_theoretical_date(info_list=expiry_info, current_date=timestamp.date())
    actual_expiry_dates = get_actual_expiry_dates(theoretical_dates_dict=theoretical_dates, trading_platform = trading_platform)

    exp_list = []
    for day in actual_expiry_dates.keys():
        # print(i)
        for j, date in enumerate(actual_expiry_dates[day]):
            if date == None:
                
                theory_date = theoretical_dates[day][j]
                _logger.info(f"{theory_date} ({day}) is not an expiry going for early expiry.")

                exp_date = get_early_expiry_date(theory_date, timestamp.date(), trading_platform=trading_platform, _logger = _logger)

                # HOT FIX for Banknifty 2023. Need to change the code.
                if (exp_date == None) & (theory_date == timestamp.date()):
                    _logger.info(f"{theory_date} ({day}) is not an expiry going for late expiry.")

                    exp_date = get_late_expiry_date(theory_date, trading_platform=trading_platform, _logger=_logger)

                if exp_date != None:
                    _logger.info(f"Found early expiry for {theory_date} ({day}) is {exp_date} ({exp_date.strftime('%A')})")

                exp_list.append(exp_date)
                
            else:
                exp_list.append(date)

    if len(exp_list) <= 1:
        return exp_list[0]

    unwind_date = get_unwind_date_for_an_expiry(expiry_date=exp_list[0])
    if timestamp >= datetime.combine(unwind_date, unwind_time):
        return exp_list[1]

    return exp_list[0]

def get_future(trading_platform: TradingPlatform, timestamp: datetime, underlying, expiry, _logger: Logger):
    future_opt = None
    try: 
        future_opt = trading_platform.getInstrumentDetails(ins=Future(strike=0, expiry=expiry, underlying=underlying, opt_type='ES'), timestamp=timestamp)

    except Exception as e:
        _logger.critical(f'Error in get_future :: line {get_exception_line_no()} :: {e}')

    return future_opt

def get_atm_iv(trading_platform: TradingPlatform, timestamp: datetime, _logger):
    curr_atm = None
    curr_atm_ce: OptionDetailed = None
    spot = trading_platform.getSpot(timestamp=timestamp)
    nearest_expiry = get_expiry_date(timestamp, expiry_info, trading_platform, _logger)

    try:
        curr_atm_ce = get_atm_option(trading_platform, trading_platform.underlying, spot, "CE", nearest_expiry, trading_platform.steps, timestamp, _logger)
    except:
        curr_atm_ce = None

    curr_atm_pe: OptionDetailed = None
    try:
        curr_atm_pe = get_atm_option(trading_platform, trading_platform.underlying, spot, "PE", nearest_expiry, trading_platform.steps, timestamp, _logger)
    except:
        curr_atm_pe = None

    if curr_atm_ce == None and curr_atm_pe == None:
        _logger.critical("No ATM found")
        return None
    elif (curr_atm_pe == None) ^ (curr_atm_ce == None):
        curr_atm = curr_atm_pe if curr_atm_pe != None else curr_atm_ce
    else:
        if abs(curr_atm_ce.strike - spot) < abs(curr_atm_pe.strike - spot):
            curr_atm = curr_atm_ce
        else:
            curr_atm = curr_atm_pe

    return curr_atm.sigma