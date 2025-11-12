import os
import glob
import datetime
import numpy as np
import pandas as pd

from tradelib_global_constants import *
from tradelib_logger import logger, get_exception_line_no
from visualizer.cc_financial_statistics import financial_summary
from visualizer.cc_financial_plots import return_plots, max_drawdown_plots, rolling_volatility_plots, general_plots, plot_returns_heatmap, rv_distribution_scatter_plots

logger = logger.getLogger("backtest")

class Backtest:
    # init - constructor
    def __init__(self, rows=375, name="Condor", mode="algo", currency=currency, asset_class="Derivates") -> None:
        self._name = name # sets name of the strategy
        self._mode = mode.lower() # analyse or algo
        self._pointer = -1 # pointer
        self._currency = currency # currency
        self._asset_class = asset_class # asset class

        if self._mode == "algo": # check if algo initialize dict or else initialize dataframe
            self._backtest_dict =  {"Timestamp":[], 
                                    "Values":[], 
                                    "Spot":[], 
                                    "Implied Vol ATM":[],
                                    "Portfolio Delta":[],
                                    "Portfolio Gamma":[],
                                    "Portfolio Vega":[],
                                    "Portfolio Theta":[],
                                    "Portfolio Cash":[]} # array initialized
            
            if margin_calculation:
                # self._backtest_dict['Margin'] = []
                # self._backtest_dict['Span_Margin'] = []
                self._backtest_dict['total_long_CE_position'] = []
                self._backtest_dict['total_short_CE_position'] = []
                self._backtest_dict['CE_moneyness'] = []
                self._backtest_dict['trade_count'] = []
                self._backtest_dict['Exposure_Margin'] = []
                self._backtest_dict['Total_Contract'] = []

        elif self._mode.lower() == "analyse":
            self._backtest_df = pd.DataFrame() # df initialized


    def read(self, path="", start_time="", end_time="", use_date_slicing=False) -> None: # read the files of backtest and generate a dataframe.
        try:
            if self._mode == "analyse":

                if use_date_slicing:
                    # if using date slicing load default storage path
                    file_names = np.array(glob.glob(pathname=os.path.join(output_dir_folder, "backtest", "*.csv"))) # load all files in location
                    file_names.sort(kind="stable")    # using insertion sort on array (fastest sorting method on almost sorted array)
                    file_names = pd.Series(file_names).apply(lambda x: x.split("/")[-1].split(".")[-2]).values # taking only the date part and removing Backtest/ and .csv 
                    
                    start, end = "".join(start_time.split("-")), "".join(end_time.split("-")) # pre-process dates to format 20200101 -> receive dates in format "2020-01-01"
                    file_names = file_names[(file_names >= start) & (file_names < end)] # take all files in the included date
                    
                    # create df
                    self._backtest_df = pd.concat([pd.read_csv(os.path.join(output_dir_folder,file_path,".csv")) for file_path in file_names], axis=0) # loading and concatenating all files into a single dataframe
                else:
                    file_names = np.array(glob.glob(pathname=os.path.join(path,"*.csv"))) # sorting all files at a particular location
                    file_names.sort(kind="stable")    # using insertion sort on array (fastest sorting method on almost sorted array)
                    self._backtest_df = pd.concat([pd.read_csv(file_path) for file_path in file_names], axis=0) # loading and concatenating all files into a single dataframe

                try:
                    self._backtest_df = self._backtest_df.rename(columns={
                                    'timestamp':'Timestamp',
                                    'spot':'Spot',
                                    'atm_iv':'Implied Vol ATM',
                                    'portfolio_delta':'Portfolio Delta',
                                    'portfolio_gamma':'Portfolio Gamma',
                                    'portfolio_vega':'Portfolio Vega',
                                    'portfolio_theta':'Portfolio Theta',
                                    'portfolio_sigma':'Portfolio Sigma',
                                    'portfolio_cash':'Portfolio Cash',
                                    'portfolio_value':'Values',
                                    'total_contracts':'Total_Contract'
                                    })
                
                    self._backtest_df = self._backtest_df[self._backtest_df['trade_done']==True]
                except:
                    pass

                # timestamp as datetime
                self._backtest_df["Timestamp"] = pd.to_datetime(self._backtest_df["Timestamp"])
                self._backtest_df.sort_values(by="Timestamp", inplace=True)
            else:
                print("Not compatible with this mode of backtest")
        except Exception as e:
            logger.info(f"f'Error in read() in line : {get_exception_line_no()}, error : {e}'")


    # Plots All Charts
    def plotCharts(self, freq="D", agg="last", chart_width=900, chart_height=450, window=10) -> None:
        """
        frequency: Frequency of Resampling df.
        agg: Aggregation Method.
        chart_width: Width of Charts
        chart_height: Height of Charts
        window: rolling window for charts
        """
        try:
            if self._mode == "analyse":
                # plot-df
                plot_df = self.__resample_df(frequency=freq, agg=agg)

                # cumulative returns plot
                return_plots(df=plot_df, frequency=freq, strategy=self.getName(), graph_width=chart_width, graph_height=chart_height, yaxis="Cumulative Return (%)",
                                                                                                                xaxis="Timestamp", title="Cumulative Returns", x_shift=25).show()


                # Plots the max drawdown
                max_drawdown_plots(df=plot_df, frequency=freq, strategy=self.getName(), graph_width=chart_width, graph_height=chart_height, yaxis=" Maximum Drawdown (%)",
                                                                                                                xaxis="Timestamp", title="Max Drawdown").show()


                # volatility charts
                rolling_volatility_plots(df=plot_df, frequency=freq, windows=window, strategy=self.getName(), graph_width=chart_width, graph_height=chart_height, yaxis="Volatility (%)",
                                                                                                                xaxis="Timestamp", title="Rolling Volatility", x_shift=25).show()

                # Cumulative PnL
                plot_df['Cumulative PnL'] = self.__calculate_pnl(plot_df['Value'])
                general_plots(df=plot_df[['Cumulative PnL']].dropna(), frequency=freq, strategy=self.getName(), graph_width=chart_width, graph_height=chart_height, y_title=f"Cumulative PnL ({self._currency})",
                                                                                                                x_title="Timestamp", chart_title=f"Cumulative PnL", x_shift=25).show()

                # monthly returns heatmap
                temp, z_val = self.__heatmap_monthly_return_data(portfolio=self.__resample_df(frequency=freq, agg=agg), date_col="Timestamp", value_col="Value")
                plot_returns_heatmap(temp, z_val, graph_height=chart_height, graph_width=chart_width).show()


                # Distribution of Returns
                # rv_distribution_scatter_plots(data=plot_df[['Value']].reset_index(), date_col="Timestamp", price_col="Value", frequency=freq, annualised=True, only_return_dist=True).show()

                # kill unnecessary dfs
                del plot_df, temp
            else:
                print("Not compatible with this mode of backtest")
        except Exception as e:
            logger.info(f"f'Error in plotCharts() in line : {get_exception_line_no()}, error : {e}'")


    # This is method to be accessed by internal methods only (private)
    def resample_df(self, frequency="D", agg="last") -> None:
        """
        frequency: Frequency of Resampling df.
        agg: Aggregation Method.
        """
        try:
            if agg == "last":
                return self._backtest_df.set_index("Timestamp").resample(frequency).last().dropna()
            elif agg == "first":
                return self._backtest_df.set_index("Timestamp").resample(frequency).first().dropna()
            elif agg == "mean":
                return self._backtest_df.set_index("Timestamp").resample(frequency).mean().dropna()
            elif agg == "median":
                return self._backtest_df.set_index("Timestamp").resample(frequency).median().dropna()

        except Exception as e:
            print(f"Warning: {e}, returns default - daily resampling with aggregation function as last")


    # summary
    def summary(self, frequency="D", agg="last") -> pd.DataFrame:
        try:
            if self._mode == 'analyse':
                return financial_summary(self.__resample_df(frequency=frequency, agg=agg).reset_index(), 
                            frequency=frequency, date_col="Timestamp", col_name_cagr="Value", risk_free_rate=params["RISK_FREE_RATE"], asset_class=self.getAssetclass())
            else:
                print("Not compatible with this mode of backtest")   
        except Exception as e:
            logger.info(f"f'Error in summary() in line : {get_exception_line_no()}, error : {e}'")
        

    # pnl calculation - private method
    def __calculate_pnl(self, port_values) -> np.array:
        return pd.Series(port_values).diff().cumsum().values


    def getData(self): # get data, return a numpy array if phase is "algo" else return "dataframe"
        if self._mode == "algo":
            return self._backtest_dict
        elif self._mode == "analyse":
            return self._backtest_df

    def getName(self): # returns the name of the backtest instance
        return self._name
    
    def getAssetclass(self): # name of asset class
        return self._asset_class