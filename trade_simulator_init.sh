#!/bin/bash

# script to start the trade simulator


# python main.py  --data_source "eis_data" \
#                 --data_name "EIS DATA" \
#                 --start_date_time "2022-01-03 09:20:00" \
#                 --end_date_time "2022-01-04 15:30:00" 
                # --interval_type "minutes" \
                # --interval_value 1 \
                # --initial_cash 0 \
                # --strategy_type "condor" \
                # --otm_percentage 10 \
                # --trade_interval 5 \
                # --hedge_interval 2 \
                # --unwind_time 45 \
                # --unit_size 10 \
                # --is_mkt_maker 1 \
                # --expiry_type 'nearest_weekly'


# python main_v02.py

# ret_val=$?

# if [ $ret_val -eq 0 ]; then
#     echo "main finished"

#     echo "going to generate backtest summary"
#     python backtest_summary.py
#     # python chartbook_main.py
#     # python extra_info.py
#     # python margin_report.py
# fi


python tradelib/main_backtest_single_process.py 

ret_val=$?

if [ $ret_val -eq 0 ]; then
    echo "main finished"

    echo "going to generate backtest summary"
    python tradelib/backtest_combiner.py 

    echo "chartbook"
    python tradelib/chartbook.py 
    rm output_dir.txt
    # python chartbook_main.py
    # python extra_info.py
    # python margin_report.py
fi