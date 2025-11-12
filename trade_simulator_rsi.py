import re
import subprocess

def update_variables_in_file(file_path, variables):
    """
    Update specific variables in a Python file.

    :param file_path: Path to the Python file to modify.
    :param variables: Dictionary where keys are variable names and values are their new values as strings.
    """
    try:
        # Read the content of the params.py file
        with open(file_path, 'r') as file:
            content = file.read()

        # Loop through each variable and apply the replacement
        for variable_name, new_value in variables.items():
            # Use regex to find and replace the specific variable's value
            updated_content = re.sub(
                rf'^{variable_name}\s*=\s*.*',
                f"{variable_name} = {new_value}",
                content,
                flags=re.MULTILINE
            )
            # Update content for each replacement
            content = updated_content

        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.write(content)

        print(f"Variables {', '.join(variables.keys())} successfully updated in {file_path}")

    except FileNotFoundError:
        print(f"The file '{file_path}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Specify the file path and the variables to change
# file_path = 'params.py'
# variables_to_update = {
#     'd': 'time(10, 5, 30)'  # Set the new value as a string to keep the function syntax
# }

def run_script():
    subprocess.run(["python", "tradelib/main_backtest_single_process.py"], check=True)
    subprocess.run(["python", "tradelib/backtest_combiner.py"], check=True)
    subprocess.run(["python", "tradelib/chartbook.py"], check=True)

if __name__ == '__main__':
    file_path = "tradelib/tradelib_global_constants.py"

    year_list = ['2024'] #, '2023', '2022', '2021', '2020']

    # rsi_upper_list = [70, 75, 80, 85, 90]
    # rsi_lower_list = [15, 20, 25, 30]
    # rsi_window_list = [5, 15, 30, 45, 60]

    slow = [40, 45, 50, 55, 60, 65, 70]
    fast = [25, 30, 35]

    thresold = [0]
    sl_list = [0] #[-50000, -70000, -100000]
    max_trade_list = [1000] #[5, 7, 10, 1000]
    is_stop_lossl = False

    cool_off_list = [10, 15]

    strategy_to_execute = "SMA_STRADDLE_STRATEGY"

    for year in year_list:
        for slow_th in slow:
            for fast_th in fast:
                for tol in thresold:
                    for sl in sl_list:
                        for max_trade in max_trade_list:
                            for cool in cool_off_list:
                                exp_day = "Thursday"

                            
                                variables_to_update = {
                                    'start_date': f'date({year}, 1, 1)',

                                    'end_date': f'date({year}, 12, 31)',

                                    'strategy_to_execute': f'"{strategy_to_execute}"',

                                    'output_dir_folder': f'os.path.join(OUTPUT_DIR, "NF_SMA_CROSS_OVER_COOLOFF", str(start_date.year) + "_" + underlying + "_" + strategy_to_execute + f"_entry_{cool}_exit_{cool}_fast_{fast_th}_slow_{slow_th}_tol_{tol}_mt_{max_trade}")',

                                    'data_dir': f'"/home/cloudcraftz/Music/NIFTY_WK/NIFTY_WK_EIS_SPOT_{year}"',

                                    'expiry_info': f'[("{exp_day}", 1)]',

                                    'strategy_trade_side' : "'customer'",
                                    'hedge_trade_side' : "'customer'",
                                    'unwind_trade_side' : "'customer'",
                                    'm2m_side' : "'customer'",

                                    'lot_size' : "25",
                                    'unit_size' : "5000",

                                    'intraday_trade' : "True",
                                    'hedge_interval_time' : "1",

                                    # 'rsi_window' : f"{rsi_wind}",
                                    # 'rsi_upper' : f"{rsi_upper}",
                                    # 'rsi_lower' : f"{rsi_lower}",

                                    'fast_lookback_period': f"{fast_th}",
                                    'slow_lookback_period': f"{slow_th}",
                                    'signal_tolerance': f"{tol}",

                                    'chart_title': f"'NIFTY {year}'",

                                    'is_stop_loss': f"{is_stop_lossl}",
                                    'stop_loss_threshold': f"{sl}",

                                    'sma_daily_entry_limit': f"{max_trade}",

                                    'entry_cool_off_time': f"{cool}",
                                    'exit_cool_off_time': f"{cool}"
                                }

                                update_variables_in_file(file_path, variables_to_update)
                                try:
                                    run_script()
                                except:
                                    pass