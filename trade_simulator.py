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
    # subprocess.run(["python", "tradelib/chartbook.py"], check=True)

if __name__ == '__main__':
    file_path = "tradelib/tradelib_global_constants.py"

    year_list = ['2024', '2023', '2022', '2021'] #, '2022', '2021'] # '2024', '2023', '2022', '2021']

    day_of_month_signal_strength_list = [
        # {'week_0': '{0:4, 1:4, 2:4, 3:4, 4:4, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0, 13:0, 14:0, 15:0, 16:0, 17:0, 18:0, 19:0, 20:0, 21:0, 22:0, 23:0, 24:0}'}, 

        # {'week_1': '{0:0, 1:0, 2:0, 3:0, 4:0, 5:4, 6:4, 7:4, 8:4, 9:4, 10:0, 11:0, 12:0, 13:0, 14:0, 15:0, 16:0, 17:0, 18:0, 19:0, 20:0, 21:0, 22:0, 23:0, 24:0}'},

        # {'week_2': '{0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:1, 11:1, 12:1, 13:1, 14:1, 15:0, 16:0, 17:0, 18:0, 19:0, 20:0, 21:0, 22:0, 23:0, 24:0}'},

        # {'week_3': '{0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0, 13:0, 14:0, 15:1, 16:1, 17:1, 18:1, 19:1, 20:1, 21:1, 22:1, 23:1, 24:1}'},

        # {'week_4': '{0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0, 13:0, 14:0, 15:0, 16:0, 17:0, 18:0, 19:0, 20:1, 21:1, 22:1, 23:1, 24:1}'},

        # {'week_0_1': '{0:2, 1:2, 2:2, 3:2, 4:2, 5:2, 6:2, 7:2, 8:2, 9:2, 10:0, 11:0, 12:0, 13:0, 14:0, 15:0, 16:0, 17:0, 18:0, 19:0, 20:0, 21:0, 22:0, 23:0, 24:0}'}, 

        # {'week_2_3': '{0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:2, 11:2, 12:2, 13:2, 14:2, 15:2, 16:2, 17:2, 18:2, 19:2, 20:0, 21:0, 22:0, 23:0, 24:0}'}, 

        # {'week_0': '{0:1, 1:1, 2:1, 3:1, 4:1, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0, 13:0, 14:0, 15:0, 16:0, 17:0, 18:0, 19:0, 20:0, 21:0, 22:0, 23:0, 24:0}'}, 
        
        # {'week_0_1_2_3': '{0:1, 1:1, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1, 9:1, 10:1, 11:1, 12:1, 13:1, 14:1, 15:1, 16:1, 17:1, 18:1, 19:1, 20:1, 21:1, 22:1, 23:1, 24:1}'}

        # {'week_0_1_rev_2_3': '{0:1, 1:1, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1, 9:1, 10:-1, 11:-1, 12:-1, 13:-1, 14:-1, 15:-1, 16:-1, 17:-1, 18:-1, 19:-1, 20:-1, 21:-1, 22:-1, 23:-1, 24:-1}'}

        {'week_2101': '{0:2, 1:2, 2:2, 3:2, 4:2, 5:1, 6:1, 7:1, 8:1, 9:1, 10:0, 11:0, 12:0, 13:0, 14:0, 15:1, 16:1, 17:1, 18:1, 19:1, 20:1, 21:1, 22:1, 23:1, 24:1}'}
    ]

    day_of_month_frequency_strength_list = [
        # {'fast_expiry': '{0:5, 1:5, 2:5, 3:5, 4:5, 5:10, 6:10, 7:10, 8:10, 9:10, 10:15, 11:15, 12:15, 13:15, 14:15, 15:20, 16:20, 17:20, 18:20, 19:20, 20:20, 21:20, 22:20, 23:20, 24:20}'}, 

        # {'slow_expiry': '{0:20, 1:20, 2:20, 3:20, 4:20, 5:15, 6:15, 7:15, 8:15, 9:15, 10:10, 11:10, 12:10, 13:10, 14:10, 15:5, 16:5, 17:5, 18:5, 19:5, 20:5, 21:5, 22:5, 23:5, 24:5}'},

        {'baseline': '{0:5, 1:5, 2:5, 3:5, 4:5, 5:5, 6:5, 7:5, 8:5, 9:5, 10:5, 11:5, 12:5, 13:5, 14:5, 15:5, 16:5, 17:5, 18:5, 19:5, 20:5, 21:5, 22:5, 23:5, 24:5}'}
    ]

    strategy_to_execute = "DAY_OF_MONTH_DUAL_SIGNAL_STATIC_CONDOR_STRATEGY"

    for year in year_list:
        for signal in day_of_month_signal_strength_list:
            key_name, value = next(iter(signal.items()))

            exp_day = "Thursday"
            end_month = 12
            end_day = 31

            if year == '2024':
                exp_day = "Wednesday"
                end_month = 10
                end_day = 30

            for freq in day_of_month_frequency_strength_list:
                freq_key_name, freq_value = next(iter(freq.items()))
        
                variables_to_update = {
                    'start_date': f'date({year}, 1, 1)',

                    'end_date': f'date({year}, {end_month}, {end_day})',

                    'strategy_to_execute': f'"{strategy_to_execute}"',

                    'output_dir_folder': f'os.path.join(OUTPUT_DIR, "BNF_Monthly_revcon_NOV29", "Test","{key_name}", "{freq_key_name}", str(start_date.year) + "_" + underlying + "_" + strategy_to_execute)',

                    'day_of_month_signal_strength': f'{value}',
                    'day_of_month_signal_frequency': f'{freq_value}',

                    'data_dir': f'"/home/hsph/Downloads/DataStore/BNF_M/BNF_MN_NB_Preprossed/{year}"',

                    'expiry_info': f'[("{exp_day}", 1)]',

                    'strategy_trade_side' : "'customer'",
                    'hedge_trade_side' : "'customer'",
                    'unwind_trade_side' : "'customer'",
                    'm2m_side' : "'customer'",

                    'lot_size' : "25",
                    'unit_size' : "25",

                    'intraday_trade' : "False",
                    'hedge_interval_time' : "2",
                }

                update_variables_in_file(file_path, variables_to_update)
                try:
                    run_script()
                except:
                    pass


