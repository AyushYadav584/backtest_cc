import os, json
import numpy as np
from datetime import timedelta, date, time, datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'outputs')
DISABLE_DEBUG = False

### BASIC CONFIGURATION OF BACKTEST ENGINE
allowed_fields_in_portfolio_dump = ['instrument_type', 'strike', 'expiry', 'opt_type']

# ================ transaction fees =================
transaction_fee = 0
gst_value = 0 #0.09
nfa_fee = 0 #0.02
exchange_fee_rate_option = 0.001 #0.39 + gst_value + nfa_fee #0.001
exchange_fee_rate_future = 0 #1.38 + gst_value + nfa_fee
exchange_commission = 0 #0.327
future_multiplier = 50
# ===================================================

initial_cash = 0.0
year = 2023
start_date = date(year, 1, 1)
end_date = date(year, 12, 31)
trade_start_time = time(9, 20, 0)
trade_end_time = time(15, 30, 0)
unwind_time= time(15, 15, 0)
underlying = "NIFTY"
interval = timedelta(minutes=1)
strategy_to_execute = "VSSMA_THREEFOLD_STRATEGY"
expiry_type = 'weekly'  # 'weekly'
delta_otm = False # true if using delta otm else false - mainly for chartpacks
date_time_format = "%Y-%m-%d %H:%M:%S"
date_format = "%Y-%m-%d"
date_format_no_dash = "%Y%m%d"
date_time_format_no_dash = "%Y%m%d%H%M%S"
tolerance = 10
strict_condor = False
strict_tolerance = True
take_later_expiry_hedge = False
delta_threshold = 75
RISK_FREE_RATE = 0.02 # 0.0369
exchange_start_time = time(9, 15, 0)
exchange_end_time = time(15, 30, 0)
avg_trade_days_in_year = 252
number_of_holidays = 16
HARD_LIMIT = 20

rv_window = 30
annualizing_parameter = 252*375

#Gamma Hedge
gamma_hedge = False
gamma_threshold = 0.04
gamma_hedge_time = time(15, 30, 0)
percent_hedge = 1.0
trade_with_received_money = True
custom_pct_to_hedge = False
pct_to_spend = 0.0
take_money_from_long_otm = False
allow_frac_gamma_hedge = True
gamma_hege_otm_outstrike = 3
straddle_component_stop_time = time(9,31)
trade_interval_time = 5 # in minutes
hedge_interval_time = 1
unwind_time_before = 15 # in minutes

OTM_outstrike = 3

expiry_info = [("Thursday", 1)]

# underlying map need
steps = 50
unit_size = 10050
lot_size = 75

### Client configuration
client_name = "EIS"

### Folder configuration
data_dir = f"/home/cloudcraftz/DATA_STORE/NIFTY_WK_EIS_SPOT_{year}_2/"
meta_data_file_name = 'meta_data.json'

## delta
delta_otm_tolerance = 50
delta_outstrike = 1

### UnderlyingConfiuration (include in underlying map)
DIVIDEND_MAP = {
    "BANKNIFTY": 0.0078,
    "NIFTY": 0.0138,
    "SPXW": 0.0150
}

STEPS_MAP = {
    "BANKNIFTY": 100,
    "NIFTY": 50,
    "SPXW": 5
}


# ========== Day of week signal ===========
day_of_week_signal_strength = {0:2, 1:1, 2:0, 3:0, 4:2}
# =========================================

# ========== Day of month signal ===========
# Implement a function to create this dict
day_of_month_signal_strength = {0:2, 1:2, 2:2, 3:2, 4:2, 5:2, 6:2, 7:2, 8:2, 9:2, 10:0, 11:0, 12:0, 13:0, 14:0, 15:0, 16:0, 17:0, 18:0, 19:0, 20:0, 21:0, 22:0, 23:0, 24:0}
                                
# =========================================

# ========== Cooloff/Frequency signal ===========
# Implement a function to create this dict
day_of_month_signal_frequency = {0:5, 1:5, 2:5, 3:5, 4:5, 5:5, 6:5, 7:5, 8:5, 9:5, 10:5, 11:5, 12:5, 13:5, 14:5, 15:5, 16:5, 17:5, 18:5, 19:5, 20:5, 21:5, 22:5, 23:5, 24:5}
                              
# =========================================

# =========== Market Trade Side ===========
# +--------+--------+---------------+
# |  Buy   |  Sell  |   Category    |
# +--------+--------+---------------+
# |  bid   |  ask   | market_maker  |
# |  bid+  |  ask-  | market_maker- |
# |  mid   |  mid   | mid           |
# |  ask-  |  bid+  | customer+     |
# |  ask   |  bid   | customer      |
# +--------+--------+---------------+
strategy_trade_side = 'customer'
hedge_trade_side = 'customer'
unwind_trade_side = 'customer'
m2m_side = 'customer'
# =========================================

# ======== Constant Risk Parameters =======
rampup_period = 375 * 3 
rampup_days = 3
rollover_days = 2
non_rollover_days = 3
total_trade_time_in_day = 375
rollover_period = 375 * 2
non_rollover_period = 375 * 3
expiry_weight_vector = np.array([0.5, 0.5])
option_legs = 4 # 4 for condor
# =========================================

# =============== vs sma ==================
signal_strat_time =  time(9, 20, 0)
signal_end_time = time(15, 0, 0)
entry_cool_off_time = 7
exit_cool_off_time = 10
fast_lookback_period = 1
slow_lookback_period = 5
signal_tolerance = 0.07
vssma_iv_exit_threshold = 0
vssma_vs_entry_threshold = 0.2
vssma_vs_or_entry_threshold = 0.45
vssma_exit_long_minutes = 5
iv_rv_fast_lookback_period = 1
iv_rv_slow_lookback_period = 5
iv_rv_signal_tolerance = 0.02
vssma_takeprofit_value = 0.06
vssma_threefold_signal_flag = False
vssma_ignore_rvsma_flag = False
vssma_exit_long_flag = False
vssma_vs_or_entry_threshold_flag = False
vssma_iv_threshold_flag = True
vssma_vs_entry_threshold_flag = False
vssma_take_profit_flag = True

# =============== RSI signal straddle ==================
# Below params are same for vssam and RSI

# signal_strat_time =  time(9, 20, 0)
# signal_end_time = time(15, 15, 0)
# entry_cool_off_time = 5
# exit_cool_off_time = 5
# fast_lookback_period = 5 # not used
# slow_lookback_period = 60 # used

rsi_variable = "iv"
rsi_window = 5
rsi_upper = 80
rsi_lower = 20
rsi_daily_entry_limit = 1
rsi_contract_quota = 1
# ==========================================


# =============== MACD signal straddle ==================
# same for macd and vssma

# signal_strat_time =  time(9, 20, 0)
# signal_end_time = time(15, 15, 0)
# entry_cool_off_time = 5
# exit_cool_off_time = 5
macd_fast_lookback_period = 10
macd_slow_lookback_period = 30
macd_signal_period = 3
macd_variable = "vr"
macd_daily_entry_limit = 15
macd_contract_quota = 1
macd_signal_tolerance = 0
macd_take_profit_level = None
macd_straddle_first_trade = False
macd_condor_flag = False
# ==========================================

# ============ gamma_cleanup ===============
gamma_cleanup = False #For chartpack
gamma_threshold = 25
gamma_condor = True
otm_strike_tolerance = 2
gamma_cleanup_trade_interval_time = 2
# ==========================================

# ============== price check ===============
check_future_price = False
check_option_prices = False

check_intrinsic_value = False
check_bid_ask = False

check_price_problem_start_time = time(0, 2, 0)
spot_move_threshold = 0.40
bid_ask_move_threshold = 1
# ==========================================


# =============================================================================== Chartpack =================================================================================

# BANKNIFTY Exception EXP Dates
BNF_EXP_DICT = {
    "2023-09-07":"2023-09-06",
    "2023-09-14":"2023-09-13",
    "2023-09-21":"2023-09-20",

    "2023-10-06":"2023-10-05",
    "2023-10-13":"2023-10-12",
    "2023-10-20":"2023-10-19",

    "2023-11-02":"2023-11-01",
    "2023-11-09":"2023-11-08",
    "2023-11-16":"2023-11-15",
    "2023-11-23":"2023-11-22",

    "2023-12-07":"2023-12-06",
    "2023-12-14":"2023-12-13",
    "2023-12-21":"2023-12-20",
    "2023-12-28":"2023-12-27"
}

expiry_day_of_week = 2 # 3 => Thursday
holiday_list_store = "holiday_lists/india/"
currency = "INR"

# load holiday list
HOLIDAY_LIST = []
years = np.arange(start_date.year, end_date.year)
for year in years:
    try:
        with open(f"{holiday_list_store}holidays_{year}.json", 'r') as f:
            HOLIDAY_LIST.extend(json.load(f))
    except Exception as ex:
        print(f"error while loading holiday list for year {year}")
        raise ex
    
# Name of the strategy
custom_strategy_name = f"{strategy_to_execute} WEEKLY EXPIRY"
asset_class = "Options"
chart_title = f"{underlying} {year}"
contract_type = "WEEKLY"
strategy = "STRADDLE"
expiry_types = "Nearest Weekly"
margin_calculation = False

# month mapper
month_mapper = {1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"}


# baseline files
baseline_blotters = ""
baseline_backtests = ""


#intraday strategy
intraday_trade = True


hedge_by_option = True

## Constant Params for SPXW
MAINTENANCE_START = time(17, 0, 0)
MAINTENANCE_END = time(17, 59, 0)

TRADING_HALT_START = time(16, 15, 0) 
TRADING_HALT_END = time(16, 29, 0)
TRADING_HALT_END_DATETIME = datetime(2021, 6, 26, 0, 0, 0)

experiment_name = "NIFTY VSSMA STRADDLE 2023"

chart_logo_path=f'/home/cloudcraftz/Backtest/HFT-Options-EIS-Global'

# ============ output folder ============
output_dir_folder = os.path.join(OUTPUT_DIR, f"VSSMA_STOPLOSSNOTIONALIV_2023", f"2023_NIFTYVSSMA_THREEFOLD_STRATEGY_7_10_1_5_0.07_0.06_delta_threshold_75_75_10050")
# output_dir_folder = os.path.join(OUTPUT_DIR, str(start_date.year) + "_" + underlying +strategy_to_execute + "_" + "20240207055834")
# =========================================