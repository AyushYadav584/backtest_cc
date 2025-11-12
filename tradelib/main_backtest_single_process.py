from tradelib.backtest_driver import BacktestDriver
from datetime import datetime, timedelta
import os

from tradelib.tradelib_global_constants import trade_start_time, trade_end_time, data_dir, OUTPUT_DIR, date_time_format_no_dash, start_date, end_date, strategy_to_execute, underlying, output_dir_folder

# start_date = start_date
# end_date = end_date
# strategy_to_execute = strategy_to_execute

# output_dir = os.path.join(OUTPUT_DIR, str(start_date.year) + "_" + underlying + "_" + strategy_to_execute + "_" + str(datetime.now().strftime('%Y%m%d%H%M%S')))

output_dir = output_dir_folder

with open('output_dir.txt', 'w') as file:
    file.write(output_dir)



# try DI or resource manager
print(start_date, end_date, trade_start_time, trade_end_time, data_dir, output_dir, strategy_to_execute)
start = datetime.now()
backtest_driver = BacktestDriver(start_date, end_date, trade_start_time, trade_end_time, data_dir, output_dir, strategy_to_execute)
# while start_date <= end_date:
#     backtest_driver.single_process_driver(start_date=start_date)
#     start_date = start_date + timedelta(days=1)
backtest_driver.run_backtest_multiprocess(12)
end = datetime.now()
print('='*20, "Total time taken ", end - start, '='*20)