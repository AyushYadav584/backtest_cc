import re
import subprocess
import os

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

    year_list = ["2025"]

    dow_configs_mon_exp_0 = '{0:1, 1:0, 2:0, 3:0, 4:0}'
    dow_configs_tue_exp_0 = '{0:0, 1:1, 2:0, 3:0, 4:0}'
    dow_configs_wed_exp_0 = '{0:0, 1:0, 2:1, 3:0, 4:0}'
    dow_configs_thu_exp_0 = '{0:0, 1:0, 2:0, 3:1, 4:0}'
    dow_configs_fri_exp_0 = '{0:0, 1:0, 2:0, 3:0, 4:1}'

    dow_config_dict_0 = {"MON":dow_configs_mon_exp_0, "TUE":dow_configs_tue_exp_0, "WED":dow_configs_wed_exp_0, "THU":dow_configs_thu_exp_0, "FRI":dow_configs_fri_exp_0}

    dow_configs_mon_exp_1 = '{0:1, 1:0, 2:0, 3:0, 4:0}'
    dow_configs_tue_exp_1 = '{0:1, 1:0, 2:0, 3:0, 4:0}'
    dow_configs_wed_exp_1 = '{0:0, 1:1, 2:0, 3:0, 4:0}'
    dow_configs_thu_exp_1 = '{0:0, 1:0, 2:1, 3:0, 4:0}'
    dow_configs_fri_exp_1 = '{0:0, 1:0, 2:0, 3:1, 4:1}'

    dow_config_dict_1 = {"MON":dow_configs_mon_exp_1, "TUE":dow_configs_tue_exp_1, "WED":dow_configs_wed_exp_1, "THU":dow_configs_thu_exp_1, "FRI":dow_configs_fri_exp_1}

    # dow_configs = {"1DTE":dow_config_dict_1, "0DTE":dow_config_dict_0}
    dow_configs = {"1DTE":dow_config_dict_1}

    day_of_week = {"MON":0, "TUE":1, "WED":2, "THU":3, "FRI":4}

    expiry_info_list = {"MON":"Monday", "TUE":"Tuesday", "WED":"Wednesday", "THU":"Thursday", "FRI":"Friday"}

    days = ["MON","TUE","WED","THU","FRI"]
    #+ [[f"{h:02}", f"{m:02}"] for h in range(10, 16) for m in range(0, 60, 30)
    # start_times = [['04', '00'],['05','00'],['06','00']]
    start_times = [['03','00']]
    end_times = [['11','00']]#,['14','00'],['16','00']]
    strangle_levels = [20]
    
    for strangle_level in strangle_levels:
        for time in start_times:
            for end_time in end_times:
                for day in days:
                    
                    for exp_type,dow_config_dict in dow_configs.items():

                        exp_day = expiry_info_list[day]
                        freq_value = dow_config_dict[day]
                        exp_day_code = day_of_week[day]

                        variables_to_update = {

                            'delta_condor_trade_start_time' : f'time({int(time[0])}, {int(time[1])}, 0)',
                            'delta_condor_trade_stop_time' : f'time({int(end_time[0])}, {int(end_time[1])}, 0)',
                            # 'output_dir_folder': f'os.path.join(OUTPUT_DIR, "settel_test" , str(start_date.year)+ "_" + underlying + "_" + strategy_to_execute)+"_3"',

                            # 'output_dir_folder': f'os.path.join(OUTPUT_DIR, "trial" , str(start_date.year),"fm_3_baseline", "{day}_{price_move_threshold_asia_hours}" + underlying + "_" + strategy_to_execute)',

                            'output_dir_folder': f'os.path.join(OUTPUT_DIR,"{"".join(time)}" +"_{exp_type}_NEW_test", "{"".join(end_time)}","{day}")',

                            'data_dir': f'"/media/oem/a4d62143-0d04-43f0-b10c-1ab3bb5c56de/Ayush/CME/cc_backtest_utils-dev/2025/{day}_NEW"',

                            'expiry_info': f'[("{exp_day}", 1)]',

                            'strategy_trade_side' : "'customer'",
                            'hedge_trade_side' : "'customer'",
                            'unwind_trade_side' : "'customer'",
                            'm2m_side' : "'customer'",

                            'lot_size' : "50",
                            
                            'unit_size': f'{50}',

                            'day_of_week_signal_strength': f'{freq_value}',

                            'expiry_day_of_week': f"{exp_day_code}",

                            'unwind_time': 'time(15, 0, 0)',
                            
                            'delta_atm_outstrike':f"{strangle_level}"
                            
                        }

                        update_variables_in_file(file_path, variables_to_update)
                        
                        output_dir_path = os.path.join(
                        os.path.join('tradelib', 'outputs'), "".join(time) + "_0DTENEW" , "".join(end_time), day + "_" + str(strangle_level)
                        )
                        
                        if os.path.exists(output_dir_path):
                            print(f"Skipping {output_dir_path}, already exists.")
                            continue
                        
                        try:
                            run_script()
                            counter+=1
                        except Exception as e:
                            print(e)
                            pass

    # print(counter)

        
