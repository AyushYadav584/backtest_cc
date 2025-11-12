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

    year_list = ['2025']

    dow_configs_mon_exp = '{0:1, 1:0, 2:0, 3:0, 4:0}'

    dow_configs_tue_exp = '{0:1, 1:0, 2:0, 3:0, 4:0}'
    dow_configs_wed_exp = '{0:0, 1:1, 2:0, 3:0, 4:0}'
    dow_configs_thu_exp = '{0:0, 1:0, 2:1, 3:0, 4:0}'
    dow_configs_fri_exp = '{0:0, 1:0, 2:0, 3:1, 4:2}'

    dow_config_dict = {"MON":dow_configs_mon_exp, "TUE":dow_configs_tue_exp, "WED":dow_configs_wed_exp, "THU":dow_configs_thu_exp, "FRI":dow_configs_fri_exp}

    day_of_week = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4}

    expiry_info_list = {"MON":"Monday", "TUE":"Tuesday", "WED":"Wednesday", "THU":"Thursday", "FRI":"Friday"}

    days = ["MON","TUE","WED","THU",'FRI']

    delta_atm_outstrikes = [20]

    strategy_to_execute = "DAY_OF_WEEK_DELTA_CONDOR_STRATEGY"
    
    #prices_threshold = [7,8,3.4,3.8,4.2,4.6]
    price_move_threshold_asia_hours_list = [3]
    
    for year in year_list:
        for day in days:
            for price_move_threshold_asia_hours in price_move_threshold_asia_hours_list:
                for d_a_o in delta_atm_outstrikes:
                    if year in ['2020', '2021']:
                        if day in ['THU', 'TUE']:
                            continue

                    exp_day = expiry_info_list[day]
                    freq_value = dow_config_dict[day]
                    exp_day_code = day_of_week[day]

                    variables_to_update = {
                        'start_date': f'date({year}, 1, 1)',

                        'end_date': f'date({year}, 12, 31)',

                        'strategy_to_execute': f'"{strategy_to_execute}"',

                        'price_move_threshold_asia_hours': f'{price_move_threshold_asia_hours}',

                        # 'output_dir_folder': f'os.path.join(OUTPUT_DIR, "settel_test" , str(start_date.year)+ "_" + underlying + "_" + strategy_to_execute)+"_3"',

                        'output_dir_folder': f'os.path.join(OUTPUT_DIR, "trial" , str(start_date.year),"fm_3_baseline", "{day}_{price_move_threshold_asia_hours}_{d_a_o}_new_17_" + underlying + "_" + strategy_to_execute)',


                        #'data_dir': f'"/media/dell/548d4dc2-4844-4adb-8b24-7b412b8f3455/data/SPX/{year}_{day}"',
                        'data_dir': f'"/media/oem/a4d62143-0d04-43f0-b10c-1ab3bb5c56de/Ayush/CME/cc_backtest_utils-dev/{year}/{day}_NEW"',
                        #'data_dir':'"/home/dell/Desktop/FRI_NEW"',

                        'expiry_info': f'[("{exp_day}", 1)]',

                        'delta_atm_outstrike' : f'{d_a_o}',

                        'strategy_trade_side' : "'customer'",
                        'hedge_trade_side' : "'customer'",
                        'unwind_trade_side' : "'customer'",
                        'm2m_side' : "'customer'",

                        'lot_size' : "50",
                        'unit_size' : "50",

                        'day_of_week_signal_strength': f'{freq_value}',

                        'chart_title': f"'SPXW {year}'",

                        'expiry_day_of_week': f"{exp_day_code}",

                        'unwind_time': 'time(16, 0, 0)'
                    }

                    update_variables_in_file(file_path, variables_to_update)
                    try:
                        run_script()
                    except:
                        print('FAILED!!!')
                        pass

                    # break

        