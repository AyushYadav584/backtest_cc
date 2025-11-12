import numpy as np
from datetime import datetime, date, time, timedelta
from py_vollib_vectorized import implied_volatility, greeks
from trading_platform import TradingPlatform
from tradelib_trade_utils import round_to_step, get_nearest_strike_option, get_atm_iv
from models.Instrument import Instrument
from models.OptionDetailed import OptionDetailed
from models.Option import Option
from models.Greeks import Greeks
from logging import Logger
from tradelib_global_constants import avg_trade_days_in_year, number_of_holidays

from scipy.stats import norm

def black_scholes_iv(price:float, S:float, K:int, t:float, r:float, q:float, option_type="CE") -> float:
    """
    Calculates the implied volatility (IV) of an options contract.

    Parameters
    ----------
    price: (float)
        option price/premium for the contract
    K: array (float)
        Strike price of the option contract
    S: float
        The spot price of the underlying asset
    r: float
        risk-free rate
    t: float
        annualised time to maturity
    q: float
        Dividend rate of the underlying
    option_type: array
        Indicating the type of the option - (call/put)

    Returns
    -------
    array: Implied Volatility of the Option

    """
    if option_type == "CE":
        flag = "c"
    elif option_type == "PE":
        flag = "p"

    volatility: np.ndarray = implied_volatility.vectorized_implied_volatility(price=price, S=S, K=K, t=t, r=r, flag=flag, q=q, model='black_scholes_merton', return_as='numpy')

    return np.nan_to_num(volatility)[0]

def black_scholes_price(S:float, K:int, T:float, r:float, q:float, sigma:float, option_type:str) -> float:
    """
    Calculates the option premium using the Black-Scholes model .

    Parameters
    ----------
    K: array (float)
        Strike price of the option contract
    S: float
        The spot price of the underlying asset
    r: float
        risk-free rate
    t: float
        annualised time to maturity
    q: float
        Dividend rate of the underlying
    option_type: str
        Indicating the type of the option - (call/put)
    sigma: float
        Implied volatility of the underlying security

    Returns
    -------
    float: Underlying's call/put premium
    """
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'CE':
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == 'PE':
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    else:
        raise ValueError('Option type must be either "CE" or "PE".')

    return price

def calculate_time_to_expiry(ins: Instrument, timestamp: datetime, avg_trade_days_in_year: int, number_of_holidays: int, trade_start_time:time, trade_end_time:time) -> float:
    '''
    Parameters
    ----------
    at_time_t: current time
    total_trading_holidays: Total number of trading holidays in a year

    Returns
    -------
    Annualised time (in minutes)
    '''
    # calculates the time difference between expiry and present time
    # send in minutes
    try:
        trade_delta_in_day: timedelta = (timedelta(hours=trade_end_time.hour, minutes=trade_end_time.minute, seconds=trade_end_time.second)-timedelta(hours=trade_start_time.hour, minutes=trade_start_time.minute, seconds=trade_start_time.second))
        trade_mins_in_day = trade_delta_in_day.seconds//60
        yearly_trade_mins = (avg_trade_days_in_year-number_of_holidays) * trade_mins_in_day

        if ins.instrument_type == "option":
            ins: Option = ins

            expiry_date_time = datetime.combine(ins.expiry, trade_end_time)

            time_delta: timedelta = expiry_date_time - timestamp 
            
            mins_to_expire = time_delta.days*trade_mins_in_day + (time_delta.seconds//60)
            
            return mins_to_expire/yearly_trade_mins
        else:
            raise Exception(f"[tradelib_blackscholes_utils.py] calculate_time_to_expiry not configured for instrument type: {ins.instrument_type}")
    except Exception as e:
        raise e




def blackschole_option_detailed(timestamp:datetime, ins: Instrument, trading_platform: TradingPlatform, _logger: Logger) -> OptionDetailed:
        '''
        Parameters
        ----------
        t: current time when the strategy is being executed
        rf: risk-free rate
        q_type: bid or ask
        mkt_data: HistoricalData object

        Returns
        -------
        Option details
        '''

        # TODO : Check with DDG if rf should be moved to param file as a global
        
        time_to_expire = calculate_time_to_expiry(ins, timestamp, avg_trade_days_in_year, number_of_holidays, trading_platform.exchange_start_time, trading_platform.exchange_end_time)
        if abs(time_to_expire) < 0.0000001:
            raise Exception("time to expire close to 0, blackscholes will raise division by zero")
        spot = trading_platform.getSpot(timestamp) # make get_spot in HistData()
        if ins.instrument_type == "option":
            ins: Option = ins
            nearestInsDetailed: OptionDetailed = get_nearest_strike_option(trading_platform, ins.strike, _logger,ins.opt_type, ins.expiry, trading_platform.underlying, timestamp)
            nearestPremium = nearestInsDetailed.mid



            # calculating implied volatility
            # insSigma = black_scholes_iv(price=nearestPremium, S=spot, K=ins.strike, t=time_to_expire, q=trading_platform.dividend, option_type=ins.opt_type, r=trading_platform.risk_free_rate)
            insSigma = nearestInsDetailed.sigma
            # insSigma = get_atm_iv(trading_platform=trading_platform, timestamp=timestamp, _logger =_logger)

            _logger.info(f"SUMEGH_2 For {ins.idKey()} nearest strike {nearestInsDetailed.idKey()}  {spot=} {insSigma=}")

            price = black_scholes_price(spot, ins.strike, time_to_expire, trading_platform.risk_free_rate, trading_platform.dividend, insSigma, ins.opt_type)

            # now it returns a positive delta for calls and negative for puts
            opt_type_flag = 'c' if ins.opt_type == "CE" else 'p'

            delta = np.nan_to_num(greeks.delta(
                flag=opt_type_flag,
                S=spot,
                K=ins.strike,
                t=time_to_expire,
                r=trading_platform.risk_free_rate,
                sigma=insSigma,
                q=trading_platform.dividend,
                model='black_scholes',
                return_as='numpy'
            ))[0]

            theta = np.nan_to_num(greeks.theta(
                        flag=opt_type_flag,
                        S=spot,
                        K=ins.strike,
                        t=time_to_expire,
                        r=trading_platform.risk_free_rate,
                        sigma=insSigma,
                        q=trading_platform.dividend,
                        model='black_scholes',
                        return_as='numpy'
            ))[0]
            
            gamma = np.nan_to_num(greeks.gamma(
                        flag=opt_type_flag,
                        S=spot,
                        K=ins.strike,
                        t=time_to_expire,
                        r=trading_platform.risk_free_rate,
                        sigma=insSigma,
                        q=trading_platform.dividend,
                        model='black_scholes',
                        return_as='numpy'
                    ))[0]

            vega = np.nan_to_num(greeks.vega(
                        flag=opt_type_flag,
                        S=spot,
                        K=ins.strike,
                        t=time_to_expire,
                        r=trading_platform.risk_free_rate,
                        sigma=insSigma,
                        q=trading_platform.dividend,
                        model='black_scholes',
                        return_as='numpy'
                    ))[0]

            
            _greeks = Greeks(delta=delta, theta=theta, gamma=gamma, vega=vega, sigma=insSigma)
            insDetailed: OptionDetailed = OptionDetailed(timestamp, None if 'id' not in ins.__dict__ else ins.id, ins.strike, ins.expiry, trading_platform.underlying, ins.opt_type, price, price, _greeks.delta, _greeks.theta, _greeks.gamma, _greeks.vega, _greeks.sigma, spot, price)
            return insDetailed
        else:
            raise Exception("Instrument not defined")
        
def getInstrumentDetailsWithBlackscholes(ins: Option, timestamp: datetime, trading_platform: TradingPlatform, _logger: Logger) -> OptionDetailed:
        insDetailed = None
        try:
            insDetailed: OptionDetailed  = trading_platform.getInstrumentDetails(ins, timestamp)
        except Exception as e:
            _logger.debug(e)
            _logger.debug("trying blackscholes")
            try:
                _logger.info(f"SUMEGH_1 bs input {timestamp} {ins}")
                insDetailed: OptionDetailed = blackschole_option_detailed(timestamp, ins, trading_platform, _logger)
                _logger.info("blackscholes usage sucessful")
                _logger.info(f"Blackscholes Option price: {insDetailed.mid}, delta: {insDetailed.delta}, gamma: {insDetailed.gamma}, theta: {insDetailed.theta}, sigma: {insDetailed.sigma}, strike: {insDetailed.strike}")
            except Exception as e:
                _logger.critical(e)
                raise Exception(f"Blackscholes didn't give any price for the option {ins.idKey()}")
        return insDetailed
