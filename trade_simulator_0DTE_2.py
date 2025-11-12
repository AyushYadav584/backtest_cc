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
 
 
 
def run_script():
    subprocess.run(["python", "tradelib/main_backtest_single_process.py"], check=True)
    subprocess.run(["python", "tradelib/backtest_combiner.py"], check=True)
    subprocess.run(["python", "tradelib/chartbook.py"], check=True)
 
if __name__ == '__main__':
    counter = 0
    
    file_path = "tradelib/tradelib_global_constants.py"
 
    year_list = ["2025","2024","2023","2022"]#,"2023","2024","2022"]
 
    dow_configs_mon_exp_0 = '{0:1, 1:0, 2:0, 3:0, 4:0}'
    dow_configs_tue_exp_0 = '{0:0, 1:1, 2:0, 3:0, 4:0}'
    dow_configs_wed_exp_0 = '{0:0, 1:0, 2:1, 3:0, 4:0}'
    dow_configs_thu_exp_0 = '{0:0, 1:0, 2:0, 3:1, 4:0}'
    dow_configs_fri_exp_0 = '{0:0, 1:0, 2:0, 3:0, 4:2}'

    dow_config_dict_0 = {"MON":dow_configs_mon_exp_0, "TUE":dow_configs_tue_exp_0, "WED":dow_configs_wed_exp_0, "THU":dow_configs_thu_exp_0, "FRI":dow_configs_fri_exp_0}

    dow_configs_mon_exp_1 = '{0:1, 1:0, 2:0, 3:0, 4:0}'
    dow_configs_tue_exp_1 = '{0:1, 1:0, 2:0, 3:0, 4:0}'
    dow_configs_wed_exp_1 = '{0:0, 1:1, 2:0, 3:0, 4:0}'
    dow_configs_thu_exp_1 = '{0:0, 1:0, 2:1, 3:0, 4:0}'
    dow_configs_fri_exp_1 = '{0:0, 1:0, 2:0, 3:1, 4:0}'

    dow_config_dict_1 = {"MON":dow_configs_mon_exp_1, "TUE":dow_configs_tue_exp_1, "WED":dow_configs_wed_exp_1, "THU":dow_configs_thu_exp_1, "FRI":dow_configs_fri_exp_1}

    dow_configs = {"0DTE":dow_config_dict_0, "1DTE":dow_config_dict_1}
 
    day_of_week = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4}
 
    expiry_info_list = {"MON":"Monday", "TUE":"Tuesday", "WED":"Wednesday", "THU":"Thursday", "FRI":"Friday"}
 
    days_0dte = ["MON","FRI"]#"MON",
    days_1dte = ["THU","FRI"]

    days = {'0DTE':days_0dte,'1DTE':days_1dte}

    prices_0dte = {'2022':7, '2023':5, '2024':5, '2025':7}
    prices_1dte = {'2022':15, '2023':10, '2024':10, '2025':15}

    prices = {'0DTE':prices_0dte,'1DTE':prices_1dte}
 
    # start_times = [["00","00"]]#[['09', '30']]# + [[f"{h:02}", f"{m:02}"] for h in range(10, 16) for m in range(0, 60, 30)]
    
    # wings_levels = [2.5]
    
    # for wings_level in wings_levels:
    for dte in ['0DTE']:
        for year in ['2022']:
            for day in days[dte]:
                
                if year == "2025":
                    start_time = ['08','30']
                    end_time = ['15','00']
                    unwind_time = ['15','00']

                else:
                    start_time = ['09','30']
                    end_time = ['16','00']
                    unwind_time = ['16','00']                   

                exp_day = expiry_info_list[day]
                freq_value = dow_configs[dte][day]
                exp_day_code = day_of_week[day]

                variables_to_update = {

                    'delta_condor_trade_start_time' : f'time({int(start_time[0])}, {int(start_time[1])}, 0)',
                    'delta_condor_trade_stop_time' : f'time({int(end_time[0])}, {int(end_time[1])}, 0)',

                    # 'output_dir_folder': f'os.path.join(OUTPUT_DIR, "settel_test" , str(start_date.year)+ "_" + underlying + "_" + strategy_to_execute)+"_3"',

                    # 'output_dir_folder': f'os.path.join(OUTPUT_DIR, "trial" , str(start_date.year),"fm_3_baseline", "{day}_{price_move_threshold_asia_hours}" + underlying + "_" + strategy_to_execute)',

                    'start_date': f'date({year}, 1, 1)',

                    'end_date': f'date({year}, 12, 31)',

                    'output_dir_folder': f'os.path.join(OUTPUT_DIR, "balanced_strangles_premium_{dte}", strategy_to_execute + "_{year}","{day}")',

                    'data_dir': f'"/media/oem/a4d62143-0d04-43f0-b10c-1ab3bb5c56de/Ayush/CME/cc_backtest_utils-dev/{year}/{day}_NEW"',

                    'expiry_info': f'[("{exp_day}", 1)]',

                    'strategy_trade_side' : "'customer'",
                    'hedge_trade_side' : "'customer'",
                    'unwind_trade_side' : "'customer'",
                    'm2m_side' : "'customer'",

                    'lot_size' : "50",
                    
                    # 'unit_size': f'{50}',

                    'day_of_week_signal_strength': f'{freq_value}',

                    'expiry_day_of_week': f"{exp_day_code}",

                    'unwind_time': f'time({int(unwind_time[0])}, {int(unwind_time[1])}, 0)',
                    
                    'target_option_premium_sum':f"{prices[dte][year]}"
                    
                }

                update_variables_in_file(file_path, variables_to_update)
                try:
                    run_script()
                    counter+=1
                    
                except:
                    pass
            
    #         break
    #     break
    # break

    print(counter)
