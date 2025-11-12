import re
import glob, os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

from datetime import timedelta
from plotly.subplots import make_subplots
from _backtest import Backtest
from tradelib_global_constants import *
from models.chartpack_utils import get_expiry_list_from_date_range

# with open('/home/cloudcraftz/Desktop/leatest-backtest-multi/HFT-Options-EIS-Global/output_dir.txt', 'r') as file:
#     output_dir_folder = file.read()

output_dir_folder = output_dir_folder

class Chartpack(Backtest):

    # constructor
    def __init__(self, filepath:str, name:str, asset_class:str, underlying:str, startMonth="", startYear="", endMonth="", endYear="", currency:str=currency, graph_font_size:int=16, graph_width:int=1600, graph_height:int=600) -> None:
        """
        Constructor:

        parameters
        =============================
        filepath: str
            Path of the backtest files
        name: str
            Name of the strategy
        asset_class: str
            Class of the asset eg: Options, Futures etc.
        underlying: str
            Name of the underlying security
        startMonth: str
            Start month of the backtest year 
        startYear: str
            Start year of the backtest
        endMonth: str
            End month of the backtest year
        endYear: str
            End year of the backtest
        currency: str, Optional, default: INR
            Currency in which the backtest is being dealt with
        graph_font_size: int, Optional, default: 16
            Size of the fonts used in the charts
        graph_width: int, Optional, default: 1600
            Width of the charts
        graph_height: int, Optional, default: 600
            Height of the charts

        return
        =============================
        None
        
        """
        super().__init__(name=name, mode="analyse", asset_class=asset_class, currency=currency)
        self.path = filepath
        self.underlying = underlying
        self.startMonth = str(startMonth)
        self.startYear = str(startYear)
        self.endMonth = str(endMonth)
        self.endYear = str(endYear)
        self.graph_font_size = graph_font_size
        self.graph_width = graph_width
        self.graph_height = graph_height

        self.read(path=self.path)


    def max_drawdown(self, value_col:str="Values", freq:str="D") -> go.Figure:
        """
        Description: Plots the daily drawdown of the strategy

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the column that contains the portfolio M2M values.
        freq: str, Optional, default: D
            Frequency of the data eg: D for Daily, M for Monthly
        
        return
        =============================
        plotly graph object

        """
        # Calculate Max Drawdown
        df = self.resample_df(frequency=freq)

        # add starting value as cash
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        # time mapper
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # Drawdown
        inv = pd.Series(df[value_col].values)
        z = pd.Series(index=range(len(inv)))
        z.iloc[0] = inv.iloc[0]

        for i in range(1, len(inv)):
            z.iloc[i] = max(inv[i], z[i-1])

        # Maximum Drawdown
        drawdowns = (inv - z)
        max_drawdown = drawdowns.min()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = df.index,
            y = (inv - z),
            fill="tozeroy"
            )
        )
        # max drawdown point
        index = np.where(drawdowns.values==max_drawdown)[0][0]

        fig.add_annotation(
                    y=drawdowns[index],
                    x=df.index[index],
                    text=str(f"{round(drawdowns[index]/1000)}K"),
                    showarrow=False,
                    xshift=30,
                    bgcolor='rgb(255,0,0)',
                    font_color='rgb(255,255,255)',
                    font_size=25
                )

        fig.update_layout(yaxis_title=f"Value in ({self._currency})", xaxis_title=f"Date", title=f"Drawdown ({mapper[freq]})| {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)
        return fig


    def monthly_pnl_plot(self) -> go.Figure:
        """
        Plots a monthly level P/L chart for the strategy

        Returns:
            plotly graph objects
        """
        # portfolio dataframe
        df = self.resample_df("D")
        
        # monthly expiry dates
        exp_dates = [exp_date.strftime('%Y-%m-%d') for exp_date in get_expiry_list_from_date_range(start_date=df.index[0], 
                                                                                                   end_date=df.index[len(df)-1], expiry_type='nearest_monthly')]

        # a fix the start date
        start = df.index[0].strftime('%Y-%m-%d')
        monthlyPL = []
        prev_val = 0

        for date in exp_dates:
            first_end = date
            tmpDf = df.loc[start:first_end]
            pnl = (tmpDf.iloc[0]['Values'] - prev_val)

            monthlyPL.append(tmpDf['Values'].diff().sum() + pnl)

            prev_val = tmpDf.iloc[-1]['Values']
            start = (pd.to_datetime(date) + timedelta(days=1)).strftime("%Y-%m-%d")


        monthlyPL_ = pd.Series(monthlyPL).apply(lambda x: str(round(x/1000))+"K")

        def convert_to_month_year(date_str):
            date_object = datetime.strptime(date_str, '%Y-%m-%d')
            return date_object.strftime('%b %Y')

        output_months = list(set(map(convert_to_month_year, exp_dates)))
        output_months.sort(key=lambda x: datetime.strptime(x, '%b %Y'))

        # plot
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x = output_months,
            y = monthlyPL,
            text = monthlyPL_, 
            textposition = "outside",
        ))


        fig.update_layout(plot_bgcolor="white", title=f"Monthly P/L {output_months[0].split(' ')[1]} {underlying} {contract_type.capitalize()} |{output_months[0]} - {output_months[len(output_months)-1]}", xaxis_title="Months", yaxis_title=f"P/L ({self._currency})", font=dict(
                                                                                                                    size=self.graph_font_size,
                                                                                                                    family="Courier New, monospace",
                                                                                                                    color="RebeccaPurple",

                                                                                            ), width=self.graph_width, height=self.graph_height)

        fig.update_xaxes(
                    mirror=True,
                    ticks='outside',
                    showline=True,
                    linecolor='black',
                    gridcolor='white')


        fig.update_yaxes(
                    mirror=True,
                    ticks='outside',
                    showline=True,
                    linecolor='black',
                    gridcolor='white')
        
        return fig


    def winnning_losing_(self, value_col:str="Values", freq:str="W") -> go.Figure:
        """
        Description: Plots the winning vs losing weeks (Number of Weeks)

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the column that contains the portfolio M2M values.
        freq: str, Optional, default: W
            Frequency of the data eg: D for Daily, M for Monthly, W for Weekly
        
        return
        =============================
        plotly graph object
        
        """
        # resampling
        df = self.resample_df(frequency=freq)

        # starting amount
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        df["pnl"] = df[value_col].diff()
        df.dropna(inplace=True)

        # winning losing periods
        win = df[df['pnl'] > 0].count()
        loss = df[df['pnl'] < 0].count()

        mapper = {"D":"Days", "M":"Months", "Q":"Quarters", "W":"Weeks"}
        dt = pd.DataFrame(data=[win.values[0], loss.values[0]], index=["Wins", "Losses"], columns=["Count"])

        x = ['Wins', 'Losses']
        y = [win.values[0], loss.values[0]]

        # Create the trace object
        trace = go.Bar(x=x, y=y, text=y, textposition="outside", marker_color=["darkgreen", "crimson"])

        # Create the layout object
        layout = go.Layout(title=f'Winning vs Losing in ({mapper[freq]}) | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})', yaxis_title=f"Number of {mapper[freq]}", xaxis_title="Win / Loss", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        # Create the figure object
        fig = go.Figure(data=[trace], layout=layout)

        return fig



    def plot_rolling_std(self, value_col:str="Values", freq:str="D", windows:int=15) -> go.Figure:
        """
        Description: Plots the rolling standard deviation of the P/L

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the column that contains the portfolio M2M values.
        freq: str, Optional, default: D
            Frequency of the data eg: D for Daily, M for Monthly, W for Weekly
        windows: int, Optional, default: 15
            Size of the rolling window (lookback).
        
        return
        =============================
        plotly graph object
        """
        # Resample
        df = self.resample_df(frequency=freq)

        # starting cash
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        # maps time
        mapper = {"D":"Day", "M":"Month", "Q":"Quarter", "W":"Week"}

        # pnl calculation
        df['pnl'] = df[value_col].diff()
        df.dropna(inplace=True)

        # vol calc
        vols = df['pnl'].rolling(window=windows).std().values

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = df.index,
            y = vols,
            marker=dict(color='darkblue')
        ))

        fig.update_layout(yaxis_title=f"Value ({self._currency})", xaxis_title=f"Date", title=f"Rolling Standard Deviation of daily PnL({windows} {mapper[freq]})| {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)
        return fig



    def plot_port_value(self, value_col:str="Values", freq:str="D") -> go.Figure:
        """
        Description: Plots the portfolio values

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the column that contains the portfolio M2M values.
        freq: str, Optional, default: D
            Frequency of the data eg: D for Daily, M for Monthly, W for Weekly
        
        return
        =============================
        plotly graph object
        """
        # Resample
        df = self.resample_df(frequency=freq)


        # add starting value as cash
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        # loading underlying data
        if self.underlying == "BANKNIFTY":
            # underlying_data = pd.read_csv("/home/cloudcraftz/Desktop/latest-backtest-2/HFT-Options-EIS-Global/tradelib/underlying/BANKNIFTY_2010_2023_EOD.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            underlying_data = yf.download("^NSEBANK", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "NIFTY":
            underlying_data = yf.download("^NSEI", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            # underlying_data = pd.read_csv("/home/cloudcraftz/Desktop/latest-backtest-2/HFT-Options-EIS-Global/tradelib/underlying/^NSEI.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()
        elif self.underlying == "SPXW":
            # underlying_data = yf.download("^SPX", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            underlying_data = pd.read_csv("tradelib/underlying/SPX_2020_2024_EOD.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "SBIN":
            # underlying_data = yf.download("^SPX", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/SBI_RAW_DATA_20219-2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "ASIANPAINT":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/ASIANPAINT_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "AXISBANK":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/AXISBANK_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BHARTIARTL":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BHARTIARTL_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BAJAJAUTO":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BAJAJAUTO_RAW_DATA_2019-2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BAJFINANCE":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BAJFINANCE_2023_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        else:
            underlying_data = yf.download(self.underlying, progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # df.to_csv("port.csv")

        # portfolio values
        values = df[value_col].values

        # underlying values
        underlying_data = underlying_data.loc[df.index[0]:df.index[-1]]

        # create figure object
        fig = go.Figure()
        fig = make_subplots(specs = [[{"secondary_y": True}]])


        fig.add_trace(go.Scatter(
            x = df.index,
            y = values,
            marker=dict(color='darkblue'),
            name = "Portfolio Value"
        ), secondary_y = False)
        

        fig.add_trace(go.Scatter(
            x = underlying_data['Close'].index,
            y = underlying_data['Close'],
            marker=dict(color='lightgreen'),
            name = f"{self.underlying}"
        ), secondary_y = True)



        # annotations
        fig.add_annotation(
                    y=values[-1],
                    x=df.index[-1],
                    text=f"{round(values[-1]/1000)}K",
                    showarrow=False,
                    xshift=30,
                    yshift=10,
                    bgcolor='darkblue',
                    font_color='rgb(255,255,255)',
                    font_size=25
                )

        # print(underlying_data['Close'].values[-1][-1])
        # print(type(underlying_data['Close'].values[-1]))

        fig.add_annotation(
                    y=values[-1],
                    x=underlying_data.index[-1],
                    text=f"{round(underlying_data['Close'].values[-1]/1000)}K",
                    showarrow=False,
                    xshift=27,
                    yshift=85,
                    bgcolor='lightgreen',
                    font_color='rgb(255,255,255)',
                    font_size=25
                )

        fig.update_layout(yaxis_title=f"Portfolio Value ({self._currency})", xaxis_title=f"Date", title=f"Portfolio Value vs Underlying ({mapper[freq]})| {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)
        fig.update_yaxes(title_text = f"{self.underlying}", secondary_y = True)

        return fig


    def winlossratio(self, value_col:str="Values", freq="D", rolling="W") -> go.Figure:
        """
        Description: Plots the rolling win ratio and the distribution of winning days

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the column that contains the portfolio M2M values.
        freq: str, Optional, default: D
            Frequency of the data eg: D for Daily, M for Monthly, W for Weekly
        rolling: str, Optional, default: W
            Frequency of the rolling win ratio
        
        return
        =============================
        plotly graph object
        """
        # resample daily
        df = self.resample_df(frequency=freq)

        # first timestep
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # maps days in rolling
        mapper_time = {"M":22, "W":5}

        # On a rolling daily basis calculate the win/loss ratio
        temp = pd.DataFrame(columns=["Win Ratio"])

        if rolling == "W":
            for date in df.index[6:]:
                x = df.loc[:date].iloc[-7:-1][value_col].diff().dropna()
                pct_win = x[x > 0].count() / len(x)
                temp.loc[date, "Win Ratio"] = pct_win
        elif rolling == "M":
            for date in df.index[23:]:
                x = df.loc[:date].iloc[-24:-1][value_col].diff().dropna()
                pct_win = x[x > 0].count() / len(x)
                temp.loc[date, "Win Ratio"] = pct_win

        temp.index.name = "Date"
        temp.reset_index(inplace=True)

        # plot bar
        fig1 = go.Figure()

        fig1.add_trace(go.Bar(
            x = temp['Date'],
            y = temp['Win Ratio']

        ))

        fig1.update_layout(yaxis_title="Win Ratio", xaxis_title=f"Date", title=f"{mapper['D']} Win Ratio (Rolling {mapper[rolling]}) | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        # percentage text for annotation
        new_df = temp.copy()
        new_df['Win Ratio'] = new_df['Win Ratio'].apply(lambda x: x * mapper_time[rolling])
        counts = new_df.groupby("Win Ratio").count()
        pct = pd.Series((counts.values / sum(counts.values)).flatten()).apply(lambda x: f'{round(x*100, 2)}%').to_list()

        # plot histogram
        fig2 = go.Figure()

        fig2.add_trace(go.Histogram(
            x = (temp['Win Ratio'] * mapper_time[rolling]),
            marker_color='#330C73',
            opacity=0.75,
            histnorm="percent",
            text = pct,
            textposition="outside"
        ))

        fig2.update_layout(yaxis_title="Percentage (%)", xaxis_title=f"Win Days", title=f"Winning Days per Week | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)


        return fig1, fig2



    def gainloss_from_mean(self, freq:str="W", value_col:str="Values") -> go.Figure:
        """
        Description: Plots the deviation of P/L from mean P/L

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the column that contains the portfolio M2M values.
        freq: str, Optional, default: W
            Frequency of the data eg: D for Daily, M for Monthly, W for Weekly
        
        return
        =============================
        plotly graph object
        """
        # helper function
        def custom_legend_name(new_names):
            for i, new_name in enumerate(new_names):
                fig.data[i].name = new_name

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # resample the year by week, take mean and calculate the deviation from mean.
        df = self.resample_df(frequency=freq)

        # staring value
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        df['pnl'] = df[value_col].diff()
        df.dropna(inplace=True)
        df['Deviation']= df["pnl"].mean() - df["pnl"]

        # colors - red if less than 0 else green
        df['PnL'] = df['Deviation'].apply(lambda x: "#66a3ff" if x < 0 else "#0047b3")
        df['Type of Gain'] = df['Deviation'].apply(lambda x: "Negative" if x < 0 else "Positive")

        fig = px.bar(df, y="Deviation", color='PnL', color_discrete_sequence=df["PnL"].unique(), labels={'col1':'postive', 'col2': 'negative'})
        fig.update_layout(yaxis_title=f"Deviation in ({self._currency})", xaxis_title=f"Date", title=f"Deviation of PnL (from {mapper[freq]} Mean PnL, Mean = {round(df['pnl'].mean() / 1000)}K {self._currency}) | Condor Strategy {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)


        if len(df[df['Deviation'] > 0]) > 1 and len(df[df['Deviation'] < 0]) > 1:
            if df['Deviation'].iloc[0] > 0:
                custom_legend_name(["Positive", "Negative"])
            elif df['Deviation'].iloc[0] < 0:
                custom_legend_name(["Negative", "Positive"])
        elif len(df[df['Deviation'] < 0]) > 1 and len(df[df['Deviation'] > 0]) == 0:
            custom_legend_name(["Negative"])
        else:
            custom_legend_name(["Positive"])


        return fig


    def meta_data_table(self, title:str="Meta Data") -> pd.DataFrame:
        """
        Description: Displays a table summarising the deatils of the strategy

        parameters
        =============================
        value_col: str, Optional, default: Meta Data
            Details of the strategy eg: Trade interval, Hedge interval etc.
        
        return
        =============================
        pandas DataFrame
        """
        # Data Arrangement
        meta_data = pd.DataFrame(
            data = [
                f"{int(interval.seconds / 60)} Minute",
                f"{int(trade_interval_time)} Minute",
                f"{int(hedge_interval_time)} Minute",
                f"{int(unwind_time_before)} Minute"
            ],

            index = ['Time Interval', 'Trade Interval', f'Hedge Interval', 'Unwind Time'], columns=['Time Intervals']
        )

        if not delta_otm:
            summary_data = pd.DataFrame(
                data = [
                    f'{np.around(initial_cash, 2)}',
                    f'{OTM_outstrike}%',
                    f'{np.around(unit_size, 2)}',
                    f'{strategy}'
                ],

                index = ['Initial Cash', 'OTM Percentage', f'N Contracts', 'Strategy'], columns=['Summary']
            )
        else:
            summary_data = pd.DataFrame(
                data = [
                    f'{np.around(initial_cash, 2)}',
                    f'{round(delta_outstrike)}%',
                    f'{np.around(unit_size, 2)}',
                    f'{strategy}'
                ],

                index = ['Initial Cash', 'Delta Percentage', f'N Contracts', 'Strategy'], columns=['Summary']
            )

        other_stats = pd.DataFrame(
            data = [
                f'{self.underlying}',
                f'{expiry_types}',
                f'{asset_class}',
                f'{month_mapper[start_date.month] + " " + str(start_date.year) + "-" + month_mapper[end_date.month] + " " + str(end_date.year)}'
            ],

            index = ['Underlying Instrument', 'Expiry Type', f'Asset Class', 'Period'], columns=['Basic Information']
        )

        meta_data = meta_data.reset_index()
        summary_data = summary_data.reset_index()
        other_stats = other_stats.reset_index()

        meta_data.columns = ['', '']
        other_stats.columns = ['', '']
        summary_data.columns = ['', '']

        df = pd.concat([other_stats, summary_data, meta_data], axis=1)
        df = df.style.set_caption(f'<b>{title}</b>').hide_index()

        return df



    def rolling_ratio(self, window=15, value_col="Values", freq="D") -> go.Figure:
        # resample the df on daily basis
        df = self.resample_df(frequency=freq)

        # starting value as cash
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        # maps time
        mapper = {"D":"Day", "M":"Month", "Q":"Quarter", "W":"Week"}

        # pnl calculations
        df['pnl'] = df[value_col].diff()
        df.dropna(inplace=True)

        # vol calc
        vols = df["pnl"].rolling(window=window).std().values

        # rolling pnl
        pnl = df[value_col].diff(window)

        # ratio
        ratio = pnl / vols

        # Plotting the rolling ratio
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = df.index,
            y = ratio,
            marker=dict(color='darkblue')
        ))

        fig.update_layout(yaxis_title=f"Ratio (PnL / Std.Dev)", xaxis_title=f"Date", title=f"{window} {mapper[freq]} Rolling - (PnL/SD)| {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)
        return fig


    # Ratio - Total Gamma Condors/Total Condors
    def gamma_cleanup_ratio(self, path_blotter:str=os.path.join(output_dir_folder, "blotter", ""), gamma_flag:bool=gamma_cleanup) -> float:
        """
        Description: Calculates the Gamma Ratio
                Gamma Ratio = (Gamma Trades / Strategy Trades)

        parameters
        =============================
        path_blotter: str
            Path of the blotter files for backtest
        gamma_flag: bool
            If gamma cleanup is switched on, we calculate this ratio.
        
        return
        =============================
        float: Gamma Ratio
        """
        if gamma_flag:
            # Year of Run
            start = str(start_date.year)
            end = str(end_date.year)

            # Blotter Analysis daywise
            sdate, edate = pd.to_datetime(f"{start}-01-01"), pd.to_datetime(f"{end}-12-31")
            df = pd.DataFrame(columns=["Gamma Strategy Contracts", "Gamma Unwind Contracts", "Hedge Contracts", "Strategy Contracts", "Unwind Contracts"])
            dates = pd.date_range(sdate, edate - timedelta(days=1), freq='d')

            # Iterate through each day of week 
            for date in dates:
                try:
                    dayOfweek = date.day_name() # day name
                    indexDate = date.strftime("%Y-%m-%d") # index date format
                    date = date.strftime("%Y%m%d") # date used to pickup file
                    blotterFilename = path_blotter + f"blotter_{date}092000_{date}153000.csv" # blotter file for a day
                    Df = pd.read_csv(blotterFilename, index_col=0)
                    Df['abs_pos'] = abs(Df['position'])

                    # normal strategy
                    normal_strategy = Df[Df['trade_object'].str.contains("strategy")]['abs_pos'].sum()

                    # normal unwind
                    normal_unwind = Df[Df['trade_object'].str.contains("unwind")]['abs_pos'].sum()

                    # strategy trades 
                    gamma_strategy = Df[Df['trade_object'].str.contains("gamma_trade")]['abs_pos'].sum()

                    # unwind trades
                    gamma_unwind = Df[Df['trade_object'].str.contains("gamma_unwind")]['abs_pos'].sum()

                    # hedge trades
                    hedge = Df[Df['trade_object'].str.contains("hedge")]['abs_pos'].sum() 

                    # Record daywise strategy, unwind and hedge trades.
                    df.loc[indexDate, 'Day Name'] = dayOfweek
                    df.loc[indexDate, 'Gamma Strategy Contracts'] = gamma_strategy
                    df.loc[indexDate, 'Gamma Unwind Contracts'] = gamma_unwind
                    df.loc[indexDate, 'Strategy Contracts'] = normal_strategy
                    df.loc[indexDate, 'Unwind Contracts'] = normal_unwind
                    df.loc[indexDate, 'Hedge Contracts'] = hedge

                except:
                    pass
            
            # Percent calculation
            gamma_strategy_condors = (df['Gamma Strategy Contracts'].sum() / 4)
            strategy_condors = (df['Strategy Contracts'].sum() / 4)

            return (round(gamma_strategy_condors/strategy_condors, 2) * 100) 
        else:
            return 0



    def premium_ratios(self, value_col="Values", PATH:str=os.path.join(output_dir_folder, "blotter", "*.csv")) -> tuple:
        """
        Calculates OTM/ATM Premium Ratio and Net Premium Earned to P/L ratio.
        """
        data = pd.concat([pd.read_csv(files, index_col=0, parse_dates=True) for files in glob.glob(PATH)])
        data = data[['position', 'instrument_id', 'instrument_object', 'trade_sub_type', 'price']]
        data.sort_index(inplace=True)
        # data['price'] = np.nan
        
        for eles in range(len(data)):
            try:
                bid, ask = float(eval(data['instrument_object'].iloc[eles])['bid']), float(eval(data['instrument_object'].iloc[eles])['ask'])
                data.iloc[eles, -1] = (bid + ask) / 2
            except:
                pass
        
        # data of strategy trades
        if gamma_hedge:
            data_strategy = data[(data['trade_sub_type'] == "trade") | (data['trade_sub_type'] == "gamma_hedge")]
        else:
            data_strategy = data[(data['trade_sub_type'] == "trade")]
        
        # weighted price 
        data_strategy['weighted_price'] = (data_strategy['price'] * abs(data_strategy['position']))
        # print(data_strategy[data_strategy.position > 0]['weighted_price'].sum(), " ", data_strategy[data_strategy.position < 0]['weighted_price'].sum())
        ratio_otm_atm = (data_strategy[data_strategy.position > 0]['weighted_price'].sum() / data_strategy[data_strategy.position < 0]['weighted_price'].sum()) # ratio of premium of otm / premium of atms

        # total premium / total pnl
        net_premium = (data_strategy[data_strategy.position < 0]['weighted_price'].sum() - data_strategy[data_strategy.position > 0]['weighted_price'].sum())
        ratio_premium_pnl = self.resample_df(frequency="D").iloc[-1][value_col] / net_premium

        return ratio_otm_atm, ratio_premium_pnl
    
    
    
    def enhanced_ratio(self, path:str=os.path.join(output_dir_folder,"blotter",""), freq:str="D", baseline_path:str=baseline_blotters+"") -> tuple:
        """
        Description: Calculates some custom ratios such as Enhanced Delta Ratio and Contract Ratio
                Enhanced Delta Ratio = (Delta at Hedge Time in Enhanced Strategy / Delta at Hedge Time in Basline) - 1
                Enhanced Contract Ratio = (Total contracts in Enhanced Strategy / Total contracts in Basline) - 1

        parameters
        =============================
        path: str
            Path of the blotter files for backtest
        freq: str, Optional, default: D
            Frequency of the data
        baseline_path: str
            Path of the baseline blotter files
        
        return
        =============================
        tuple: (float, float, float)
        """
        # delta hedge ratio
        def delta_hedge_ratio():
            # Enhanced Delta Ratio
            enhanced_data = self.getData().copy()
            enhanced_data['Portfolio Delta'] = abs(enhanced_data['Portfolio Delta'])
            enhanced_delta_hedge = enhanced_data.groupby("Trade")["Portfolio Delta"].sum()["Hedge"]

            # combine all baseline files
            baseline_backtest = np.array(glob.glob(pathname=baseline_backtest+"*.csv"))
            baseline_backtest.sort(kind="stable")

            backtest_baseline_df = pd.concat([pd.read_csv(files) for files in baseline_backtest], axis=0)
            baseline_data = backtest_baseline_df.copy()
            baseline_data['Portfolio Delta'] = abs(baseline_data['Portfolio Delta'])
            baseline_delta_hedge = baseline_data.groupby("Trade")["Portfolio Delta"].sum()["Hedge"]

            return ((enhanced_delta_hedge) / (baseline_delta_hedge)) - 1

        enhanDf = pd.DataFrame()
        baseDf = pd.DataFrame()

        # Combining all blotter files for Baseline
        for files in glob.glob(baseline_path+"*.csv"):
            data = pd.read_csv(files, index_col=0)[['time', 'instrument_id', 'price', 'trade_object', 'position']].set_index("time")
            data = data[data['trade_object'].str.contains("strategy")]
            baseDf = pd.concat([baseDf, data])

        # Combining all files of Enhanced Strategy
        for files in glob.glob(path+"*.csv"):
            data = pd.read_csv(files, index_col=0)[['time', 'instrument_id', 'price', 'trade_object', 'position']].set_index("time")
            data = data[data['trade_object'].str.contains("strategy")]
            enhanDf = pd.concat([enhanDf, data])

        # Baseline and Enhanced Total Df's
        baseDf.sort_index(inplace=True)
        enhanDf.sort_index(inplace=True)

        baseDf.index = pd.to_datetime(baseDf.index)
        enhanDf.index = pd.to_datetime(enhanDf.index)

        # Absolute Contracts
        baseDf['position ABS (Baseline)'] = abs(baseDf['position'])
        enhanDf['position ABS (Enhanced)'] = abs(enhanDf['position'])

        enhanced_contract_ratio = (enhanDf['position ABS (Enhanced)'].sum() / baseDf['position ABS (Baseline)'].sum() - 1)

        return enhanced_contract_ratio, 0, delta_hedge_ratio()


    def technical_summary(self, title:str="Summary Stats", freq:str="D", secondary_freq:str="M", value_col:str="Values") -> pd.DataFrame:
        """
        Description: Displays the technical summary of the strategy, statistics.

        parameters
        =============================
        title: str, Optional, default: Summary Stats
            Title of the table
        freq: str, Optional, default: D
            Frequency of the data
        secondary_freq: str, default: W
            Frequency of the data to be used for some secondary processing eg: Weekly Loss, Weekly Gain if secondary_freq = W
        value_col: str, Optional, default: Values
            Name of the column which contains the portfolio values
        
        return
        =============================
        pandas DataFrame
        """
        def comma(num):
            '''Add comma to every 3rd digit. Takes int or float and
            returns string.'''
            if type(num) == int:
                return '{:,}'.format(num)
            elif type(num) == float:
                return '{:,.2f}'.format(num) # Rounds to 2 decimal places
            else:
                print("Need int or float as input to function comma()!")

        # Resampling df and calculating pnl
        df = self.resample_df(frequency=freq)

        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        df['pnl'] = df[value_col].diff()
        df.dropna(inplace=True)

        # mapper
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # ===================== Gain Information ==================================

        # total pnl
        total_pnl = df['pnl'].sum()

        # max daily gain
        max_gain = max(df['pnl'].max(), 0)

        # max weekly gain
        df_weekly = self.resample_df(frequency=secondary_freq)

        t = df_weekly.index[0] - timedelta(weeks=1)
        df_weekly.loc[t, value_col] = initial_cash
        df_weekly.sort_index(inplace=True)

        df_weekly['pnl'] = df_weekly[value_col].diff()
        df_weekly.dropna(inplace=True)

        max_weekly_gain = max(df_weekly['pnl'].max(), 0)

        # daily win percentage
        winloss = len(df[df['pnl'] > 0]) / len(df['pnl'])

        # ======================== Risk Metrics =====================================


        # standard deviation daily gain
        ovr_std = df["pnl"].std() # std deviation over raw value or pnl ?

        # standard deviation weekly
        weekly_sd = df_weekly['pnl'].std()

        # max daily loss
        max_loss = min(0, df['pnl'].min())

        # max weekly loss
        max_weekly_loss = min(0, df_weekly['pnl'].min())

        # peak drawdown
        peak_drawdown_daily = 0

        # Drawdown
        inv = pd.Series(df[value_col].values)
        z = pd.Series(index=range(len(inv)))
        z.iloc[0] = inv.iloc[0]

        for i in range(1, len(inv)):
            z.iloc[i] = max(inv[i], z[i-1])

        # Maximum Drawdown
        drawdowns = (inv - z)
        peak_drawdown_daily = drawdowns.min()


        # ======================== Descriptive Stats ================================

        # daily gain / SD Ratio
        ratio = df['pnl'].mean() / df['pnl'].std()

        # weekly gain / SD ratio
        ratio_weekly = df_weekly['pnl'].mean() / weekly_sd

        # peak contracts
        try:
            enhancement_contract_ratio, enhancement_delta_ratio, delta_hedge_ratio = self.enhanced_ratio()
        except:
            print("Error Encountered !!!")
            enhancement_contract_ratio, enhancement_delta_ratio, delta_hedge_ratio = 0, 0, 0

        # average daily gain
        avg_daily_gain = df['pnl'].mean()

        # average weekly gain
        avg_weekly_gain = df_weekly['pnl'].mean()


        # ======================== Margin Stats ================================
        if margin_calculation:
            margin_path = os.path.join(output_dir_folder, "backtest", f"_{contract_type.lower()}", "")
            margin_frequency = "D"

            margin_file_names = np.array(glob.glob(pathname=margin_path+"*.csv")) # sorting all files at a particular location
            margin_file_names.sort(kind="stable")    # using insertion sort on array (fastest sorting method on almost sorted array)
            margin_backtest_df = pd.concat([pd.read_csv(file_path) for file_path in margin_file_names], axis=0) # loading and concatenating all files into a single dataframe

            margin_backtest_df["Timestamp"] = pd.to_datetime(margin_backtest_df["Timestamp"])
            margin_backtest_df.sort_values(by="Timestamp", inplace=True)

            # min_daily_margin = margin_backtest_df[margin_backtest_df['Total_Margin'] != 0].set_index("Timestamp").resample(margin_frequency).min().dropna()['Total_Margin'].min()

            max_daily_margin = margin_backtest_df.set_index("Timestamp").resample(margin_frequency).max().dropna()['Total_Margin'].max()
            avg_daily_margin = margin_backtest_df.set_index("Timestamp").resample(margin_frequency).max().dropna()['Total_Margin'].mean()
        else:
            max_daily_margin, avg_daily_margin = 0, 0

        # ============================================================================

        # start and end date
        start, end = (self.startMonth + "-" + self.startYear), (self.endMonth + "-" + self.endYear)
        
        # premium ratios
        ratio_otm_atm, ratio_net_premium_pnl = self.premium_ratios()

        # Data Arrangement
        meta_data = pd.DataFrame(
            data = [
                f'{comma(round(total_pnl))} ({self._currency})',
                f'{comma(round(max_gain))} ({self._currency})',
                f'{comma(round(max_weekly_gain))} ({self._currency})',
                f'{round((winloss)*100, 2)}%'
            ],

            index = ['Total P/L', 'Max Daily Gain', f'Max Monthly Gain', 'Daily Win %'], columns=['Meta Data']
        )

        summary_data = pd.DataFrame(
            data = [
                f'{comma(round(ovr_std))} ({self._currency})',
                f'{comma(round(max_loss))} ({self._currency})',
                f'{comma(round(max_weekly_loss))} ({self._currency})',
                f'{comma(round(peak_drawdown_daily))} ({self._currency})'
            ],

            index = ['SD Daily PnL', 'Max Daily Loss', 'Max Monthly Loss', f'Peak Drawdown'], columns=['Summary']
        )

        other_stats = pd.DataFrame(
            data = [
                f'{round(ratio, 2)}',
                f'{round(enhancement_contract_ratio, 2)}',
                f'{comma(round(avg_daily_gain))} ({self._currency})',
                f'{comma(round(avg_weekly_gain))} ({self._currency})'
            ],

            index = ['Daily Avg. PnL / SD', 'Enhanced Contract Ratio', 'Avg. Daily PnL', 'Avg. Monthly PnL'], columns=['Risk Metrics']
        )

        extra_stats = pd.DataFrame(
            data = [
                f'{round(ratio_weekly, 2)}',
                f'{comma(round(weekly_sd))} ({self._currency})',
                f'{self.gamma_cleanup_ratio()} %',
                f'{round(delta_hedge_ratio, 2)}'
            ],

            index = ['Monthly Avg. PnL / SD', 'SD Monthly PnL', 'G.C. Ratio', 'Enhanced Delta Ratio'], columns=['Extra Info']
        )

        margin_stats = pd.DataFrame(
            data = [
                f'{comma(round(max_daily_margin))} ({self._currency})',
                f'{comma(round(avg_daily_margin))} ({self._currency})',
                f'{round(ratio_otm_atm*100, 2)}%',
                f'{round(ratio_net_premium_pnl*100, 2)}%'
            ],

            index = ['Daily Peak Margin', 'Avg. Daily Peak Margin', 'Ratio (OTM/ATM) Premium', 'Ratio (Total P/L / Net Premium)'], columns=['Margin Info']
        )


        meta_data = meta_data.reset_index()
        summary_data = summary_data.reset_index()
        other_stats = other_stats.reset_index()
        extra_stats = extra_stats.reset_index()
        margin_stats = margin_stats.reset_index()

        meta_data.columns = ['', 'Summary']
        other_stats.columns = [' ', 'Descriptive Stats']
        summary_data.columns = ['  ', 'Risk Metrics']
        extra_stats.columns = ['   ', 'Extra Info']
        margin_stats.columns = ['    ', 'Margin Info']

        # Set Colors
        def _color_negative_red(val):
            try:
                if 0 > float("".join(val.split(f"({self._currency})")[0].split(","))):
                    return 'color: %s' % "red"
            except:
                pass

        df = pd.concat([meta_data, summary_data, other_stats, extra_stats, margin_stats], axis=1)
        df = df.style.applymap(_color_negative_red).set_caption(f'<b>{title}</b>').hide_index()       
        df.to_excel(os.path.join(output_dir_folder,f'Technical_Summary_{self.underlying}_{self.startYear}.xlsx'), index=False)

        return df


    def distribution_plots(self, freq:str="D", value_col:str="Values") -> go.Figure:
        """
        Description: Plots the P/L distribution

        parameters
        =============================
        freq: str, Optional, default: D
            Frequency of the data required for distribution
        value_col: str, Optional, default: Values
            Name of the column which contains the portfolio values
        
        return
        =============================
        plotly graph objects
        """
        # resample by given frequency
        df = self.resample_df(frequency=freq)

        # starting amount as cash
        if freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        elif freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # time mapper
        mapper_ = {"D":"Days", "M":"Months", "Q":"Quarters", "W":"Weeks"}

        # day on day or week on week gain loss
        df['pnl'] = df[value_col].diff()
        df.dropna(inplace=True)

        # mean and median
        mean = df['pnl'].mean()
        median = df['pnl'].median()

        # std
        posi_2_std = mean + (2*df['pnl'].std())
        neg_2_std = mean - (2*df['pnl'].std())

        maxi, mini = round(df['pnl'].max()), round(df['pnl'].min())
        bin_size = round((1 + 3.322*np.log(len(df))))
        steps = (maxi - mini) / bin_size

        # Define the bin edges and bin centers
        bin_edges = np.arange(df['pnl'].min(), df['pnl'].max() + steps, steps)
        bin_centers = bin_edges[:]

        counts_percent = []
        for j in range(len(bin_centers)-1):
            upper = bin_centers[j+1]
            lower = bin_centers[j]
            counts_percent.append(len(df[(df['pnl'] >= lower) & (df['pnl'] <= upper)]))

        # last interval
        lower = bin_centers[j]
        upper = bin_centers[j+1]
        counts_percent.append(len(df[(df['pnl'] >= lower) & (df['pnl'] <= upper)]))

        total_sum = sum(counts_percent)
        counts_percent = pd.Series(counts_percent).apply(lambda x: round((x/total_sum)*100, 2))

        # Compute the histogram values
        hist, _ = np.histogram(df['pnl'], bins=bin_edges)

        # Create the histogram trace with bin ticks
        histogram_trace = go.Histogram(x=df['pnl'], xbins=dict(start=df['pnl'].min(), end=df['pnl'].max(), size=steps), text=[f'{round((percent*total_sum)/100)}' for percent in counts_percent], marker=dict(color="#99ebff")) #histnorm="percent")

        # change by TR
        arrow_position=[round((percent*total_sum)/100) for percent in counts_percent]

        # Create the layout object with explicit tickvals
        layout = go.Layout(title=f"{mapper[freq]} PnL Distribution | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", xaxis=dict(title=f'Gain ({self._currency})', tickvals=bin_centers, ticktext=[f'{round((tick/1000))}K' for tick in bin_centers]), yaxis=dict(title=f'No. of {mapper_[freq]}'), font=dict(family = "Courier New, monospace",
                                    size = self.graph_font_size,
                                    color = "RebeccaPurple"
                                ), width = self.graph_width, height = self.graph_height)

        # Calculate the position of the arrow
        arrow_x = mean
        arrow_y = max(counts_percent)


        # Create the figure object and add the trace and layout
        fig = go.Figure(data=[histogram_trace], layout=layout)

        fig.add_vline(x=mean, line_width=3, line_dash="dash", line_color="red")
        fig.add_vline(x=median, line_width=3, line_dash="dash", line_color="black")

        #vertical line to 2std(+ve) and 2std(-ve)
        fig.add_vline(x=posi_2_std, line_width=3, line_dash="dash", line_color="blue")
        fig.add_vline(x=neg_2_std, line_width=3, line_dash="dash", line_color="orange")

        fig.add_annotation(x=mean, y = max(arrow_position)+2,
            text=f"Mean(μ)={round(mean/1000)}K",
            ax=80,
            ay=-40,
            showarrow=True,
            font=dict(size=self.graph_font_size),
            arrowhead=1,
        )

        fig.add_annotation(x=median, y = max(arrow_position),
            text=f"Median(x̃)={round(median/1000)}K",
            ax=-80,
            ay=-60,
            showarrow=True,
            font=dict(size=self.graph_font_size),
            arrowhead=1,
        )
        # (+ve ) 2std
        fig.add_annotation(x=posi_2_std, y = max(arrow_position)+2,
            text=f"μ+2σ={round(posi_2_std/1000)}K",
            ax=100,
            ay=40,
            showarrow=True,
            font=dict(size=self.graph_font_size),
            arrowhead=1,
        )
        # (-ve) 2std
        fig.add_annotation(x=neg_2_std, y = max(arrow_position),
            text=f"μ-2σ={round(neg_2_std/1000)}K",
            ax=-80,
            ay=40,
            showarrow=True,
            font=dict(size=self.graph_font_size),
            arrowhead=1,
        )

        return fig



    def plot_realized_vol(self, freq:str="D", window:int=15) -> go.Figure:
        """
        Description: Plots the Realized Volatility

        parameters
        =============================
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        window: int, Optional, default: 15
            Size of the rolling window (lookback).
        
        return
        =============================
        plotly graph objects
        """
        # start year
        start_datetime = (pd.to_datetime(self.startYear) - timedelta(days=(window+1))).strftime("%Y-%m-%d")
        end_datetime = (pd.to_datetime(self.endYear+'-12-31')).strftime("%Y-%m-%d")
        
        if self.underlying == "BANKNIFTY":
            # underlying_data = pd.read_csv("/home/cloudcraftz/Desktop/latest-backtest-2/HFT-Options-EIS-Global/tradelib/underlying/BANKNIFTY_2010_2023_EOD.csv", index_col=0, parse_dates=True).loc[start_datetime:end_datetime].resample(freq).last().dropna()
            underlying_data = yf.download("^NSEBANK", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()
        elif self.underlying == "NIFTY":
            underlying_data = yf.download("^NSEI", progress=False).loc[start_datetime:end_datetime].resample(freq).last().dropna()
            # underlying_data = pd.read_csv("/home/cloudcraftz/Desktop/latest-backtest-2/HFT-Options-EIS-Global/tradelib/underlying/^NSEI.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()
        elif self.underlying == "SPXW":
            underlying_data = pd.read_csv("tradelib/underlying/SPX_2020_2024_EOD.csv", index_col=0, parse_dates=True).loc[start_datetime:end_datetime].resample(freq).last().dropna()
            # underlying_data = yf.download("^SPX", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "SBIN":
            # underlying_data = yf.download("^SPX", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/SBI_RAW_DATA_20219-2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "ASIANPAINT":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/ASIANPAINT_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "AXISBANK":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/AXISBANK_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BHARTIARTL":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BHARTIARTL_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BAJAJAUTO":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BAJAJAUTO_RAW_DATA_2019-2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BAJFINANCE":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BAJFINANCE_2023_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        else:
            underlying_data = yf.download(self.underlying, progress=False).loc[start_datetime:end_datetime].resample(freq).last().dropna()

        mapper = {"D":"Daily", "M":"Monthly", "W":"Weekly"}
        mapper_time = {"D":252, "M": 12, "W": 52}

        underlying_data["returns"] = underlying_data['Close'].pct_change().fillna(0)
        rolling_window_vol = (underlying_data['returns'].rolling(window=window).std() * np.sqrt(mapper_time[freq])).dropna()
        
        # plotting the realized volatility
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = rolling_window_vol.index,
            y = rolling_window_vol * 100,
            line=dict(color='#00b3b3', width=2)
        ))

        # update title, font etc.
        fig.update_layout(yaxis_title=f"Realized Volatility (%)", xaxis_title=f"Date", title=f"Rolling Realized Annual Volatility ({window} day, Mean = {round(rolling_window_vol.mean()*100, 2)}%)| {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        return fig


    def plot_port_delta(self, value_col:str="Portfolio Delta", freq:str="D") -> go.Figure:
        """
        Description: Plots the Portfolio Delta

        parameters
        =============================
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        value_col: str, Optional, default: Portfolio Delta
            Name of the Portfolio Delta column
        
        return
        =============================
        plotly graph objects
        """
        # Resample
        df = self.resample_df(frequency=freq, agg="mean")

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # portfolio values
        values = df[value_col].values
        # fig = general_plots(df=values)
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = df.index,
            y = values,
            line=dict(color='darkblue', width=2)
        ))

        fig.update_layout(yaxis_title="Portfolio Delta", xaxis_title=f"Date", title=f"{mapper[freq]} Portfolio Delta | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        return fig


    def get_underlying_returns_data(self, freq:str="D", window:int=20) -> pd.DataFrame:
        """
        Description: Gives the underlying security data with returns

        parameters
        =============================
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        
        return
        =============================
        pandas DataFrame
        """
        # start year
        start_datetime = (pd.to_datetime(self.startYear) - timedelta(days=(window+1))).strftime("%Y-%m-%d")
        end_datetime = (pd.to_datetime(self.endYear+'-12-31')).strftime("%Y-%m-%d")
        
        if self.underlying == "BANKNIFTY":
            underlying_data = yf.download("^NSEBANK", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            # underlying_data = pd.read_csv("/home/cloudcraftz/Desktop/latest-backtest-2/HFT-Options-EIS-Global/tradelib/underlying/BANKNIFTY_2010_2023_EOD.csv", index_col=0, parse_dates=True).loc[start_datetime:end_datetime].resample(freq).last().dropna()
        elif self.underlying == "NIFTY":
            underlying_data = yf.download("^NSEI", progress=False).loc[start_datetime:end_datetime].resample(freq).last().dropna()
            # underlying_data = pd.read_csv("/home/cloudcraftz/Desktop/latest-backtest-2/HFT-Options-EIS-Global/tradelib/underlying/^NSEI.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()
        elif self.underlying == "SPXW":
            underlying_data = pd.read_csv("tradelib/underlying/SPX_2020_2024_EOD.csv", index_col=0, parse_dates=True).loc[start_datetime:end_datetime].resample(freq).last().dropna()
            # underlying_data = yf.download("^SPX", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "SBIN":
            # underlying_data = yf.download("^SPX", progress=False).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/SBI_RAW_DATA_20219-2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "ASIANPAINT":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/ASIANPAINT_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "AXISBANK":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/AXISBANK_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BHARTIARTL":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BHARTIARTL_2019_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BAJAJAUTO":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BAJAJAUTO_RAW_DATA_2019-2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()

        elif self.underlying == "BAJFINANCE":
            underlying_data = pd.read_csv("/home/cloudcraftz/Downloads/BAJFINANCE_2023_2025.csv", index_col=0, parse_dates=True).loc[self.startYear:self.endYear].resample(freq).last().dropna()
            
        else:
            underlying_data = yf.download(self.underlying, progress=False).loc[start_datetime:end_datetime].resample(freq).last().dropna()

        underlying_data["returns"] = underlying_data['Close'].pct_change().fillna(0)

        return underlying_data



    def plot_realized_implied_vol(self, value_col:str="Implied Vol ATM", freq:str="D", window:int=15) -> go.Figure:
        """
        Description: Plot the implied volatility and realized volatility in a single plot

        parameters
        =============================
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        value_col: str, Optional, default: Implied Vol ATM
            Name of the ATM Implied Volatility column
        window: int, Optional, default: 15
            Size of the rolling window (lookback).
        
        return
        =============================
        plotly graph objects
        """
        # Resample
        df = self.resample_df(frequency=freq, agg="mean")

        underlying_data = self.get_underlying_returns_data()

        # mapper time
        mapper_time = {"D":252, "M":12, "W": 52}

        # Calculate Realized Volatility
        underlying_data['Realized_Vol'] = underlying_data['returns'].rolling(window=window).std() * np.sqrt(mapper_time[freq])

        underlying_data.reset_index(inplace = True)
        underlying_data = underlying_data.dropna()

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # implied volatility values
        values = df[[value_col]]
        values.reset_index(inplace = True)

        fig = go.Figure()

        trace1 = go.Scatter(
            x=values['Timestamp'],
            y=(values[value_col]*100),
            mode='lines',
            line=dict(color='#ff4d4d', width=2),
            name='Implied Volatility'
        )
        
        trace2 = go.Scatter(
            x=underlying_data['Date'],
            y=(underlying_data['Realized_Vol']*100),
            mode='lines',
            line=dict(color='#00b3b3', width=2),
            name='Realized Volatility',
        )

        fig.add_trace(trace1)
        fig.add_trace(trace2)

        fig.update_layout(yaxis_title="Volatility (%)", xaxis_title=f"Date", title=f"Implied Volatility Vs Realized Volatility (Mean IV = {round(values[value_col].mean()*100, 2)}%, Mean RV = {round(underlying_data['Realized_Vol'].mean()*100, 2)}%) | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                            size = self.graph_font_size,
                                                                                                            color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width+400, height = self.graph_height)

        return fig


    def generate_descriptive_stats(self, path:str=os.path.join(output_dir_folder,"blotter"), freq:str="D", value_col:str="Values") -> pd.DataFrame:
        """
        Description: Display the descriptive statistics of the strategy

        parameters
        =============================
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        value_col: str, Optional, default: Values
            Name of the portfolio values column
        path: str
            Path of the blotter summary files of the backtest
        
        return
        =============================
        pandas DataFrame
        """

        # Accumulating all trades daily
        file_names = np.array(glob.glob(pathname=os.path.join(path,"*.csv")))
        file_names = pd.concat([pd.read_csv(file_path, index_col=0, parse_dates=True) for file_path in file_names], axis=0)
        file_names = file_names.reset_index()
        file_names['Date'] = file_names['timestamp'].apply(lambda x: x.strftime("%Y-%m-%d"))
        file_names_grouped = file_names.groupby(['Date', 'trade_sub_type'])['position'].count().reset_index().set_index("Date")

        file_names = pd.DataFrame(columns=["ntrades", "nhedges", "nunwinds"])
        for dates in file_names_grouped.index.unique():
            tmp = file_names_grouped.loc[dates].values
            hedges, trades, unwind = 0, 0, 0
            for i in range(0, len(tmp)):
                try:
                    if tmp[i][0] == "hedge":
                        hedges = tmp[i][1]
                    elif tmp[i][0] == "trade":
                        trades = tmp[i][1]
                    elif tmp[i][0] == "unwind":
                        unwind = tmp[i][1]
                except:
                    pass

            file_names.loc[dates, "ntrades"] = trades
            file_names.loc[dates, "nhedges"] = hedges
            file_names.loc[dates, "nunwinds"] = unwind

        file_names['totaltrades'] = file_names['ntrades'] + file_names['nhedges'] + file_names['nunwinds']


        df = self.resample_df(frequency=freq)
        # stats
        tf = self.resample_df(frequency=freq, agg="mean")[['Portfolio Delta', 'Portfolio Gamma', 'Portfolio Vega', 'Implied Vol ATM']]
        if freq == "W":
            t = tf.index[0] - timedelta(weeks=1)
            tf.loc[t, value_col] = initial_cash
            tf.sort_index(inplace=True)
        elif freq == "D":
            t = tf.index[0] - timedelta(days=1)
            tf.loc[t, value_col] = initial_cash
            tf.sort_index(inplace=True)

        # Average PnL / (Strategy Trade)
        starting_val = (df[value_col].iloc[0] - initial_cash)
        total_trades = file_names['ntrades'].sum()

        if total_trades != 0:
            avg_pnl_per_ntrade = ((df[value_col].diff().dropna().sum() + starting_val) / total_trades)
            temp = round(avg_pnl_per_ntrade)
        else:
            avg_pnl_per_ntrade = np.nan
            temp = "N/A"

        
        # print("n trades",(file_names['ntrades']))

        # Data Arrangement
        
        meta_data = pd.DataFrame(
            data = [
                f'{round(file_names["nhedges"].max())}',
                f'{round(file_names["nunwinds"].max())}',
                f'{round(tf["Portfolio Delta"].max(), 2)}',
                f'{temp} ({self._currency})'
                
            ],

            index = ['Max Daily Hedge Trades', f'Max Daily Unwind Trades', "Max Daily Portfolio Delta", 'Avg. PnL (per Strategy Trade)'], columns=['Meta Data']
        )

        summary_data = pd.DataFrame(
            data = [
                f'{round(file_names["nhedges"].mean())}',
                f'{round(file_names["nunwinds"].mean())}',
                f'{round(tf["Portfolio Delta"].mean(), 2)}',
                f'{round(file_names["ntrades"].mean())}'
            ],

            index = ['Avg. Daily Hedge Trades', f'Avg. Daily Unwind Trades', 'Avg. Daily Portfolio Delta', 'Avg. Daily Strategy Trades'], columns=['Summary']
        )

        other_stats = pd.DataFrame(
            data = [
                f'{round(tf["Implied Vol ATM"].mean()*100, 2)}%',
                f'{round(tf["Implied Vol ATM"].max()*100, 2)}%',
                f'{round(tf["Portfolio Gamma"].max(), 2)}',
                f'{round(tf["Portfolio Gamma"].mean(), 2)}'
            ],

            index = ['Avg Daily Implied Volatility', 'Max Daily Implied Volatility', f'Max Daily Portfolio Gamma', 'Avg. Daily Portfolio Gamma'], columns=['Summary']
        )

        extra_stats = pd.DataFrame(
            data = [
                f'{round(file_names["totaltrades"].max())}',
                f'{round(file_names["totaltrades"].mean())}',
                f'{round(tf["Portfolio Vega"].min(), 2)}',
                f'{round(tf["Portfolio Vega"].mean(), 2)}'
            ],

            index = [f'Max Daily Total Trade', 'Avg. Daily Total Trade', 'Max Daily Portfolio Vega', 'Avg Daily Portfolio Vega'], columns=['Summary']
        )

        meta_data = meta_data.reset_index()
        summary_data = summary_data.reset_index()
        other_stats = other_stats.reset_index()
        extra_stats = extra_stats.reset_index()

        meta_data.columns = ['', '']
        other_stats.columns = ['', '']
        summary_data.columns = ['', '']
        extra_stats.columns = ['', '']

        tf = pd.concat([meta_data, summary_data, other_stats, extra_stats], axis=1)
        tf = tf.style.set_caption(f'<b>{"Descriptive Statistics"}</b>').hide_index()

        return tf


    def imp_real_vol_diff(self, window:int=15) -> go.Figure:
        """
        Description: Plots the Implied Realized Volatility Spread

        parameters
        =============================
        window: int, Optional, default: 15
            Size of the rolling window (lookback in days).
        
        return
        =============================
        plotly graph objects
        """
        # get EOD underlying data
        df = self.get_underlying_returns_data()
        df['vol'] = df['returns'].rolling(window).std() * np.sqrt(252)

        # implied vol
        imp_df = self.resample_df("D")[["Implied Vol ATM"]]

        diff = df['vol'].reset_index()['vol'].values[:len(imp_df)] - imp_df.reset_index()['Implied Vol ATM'].values
        mean_line = np.mean(pd.Series(diff).dropna().values)

        # plot
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = imp_df.index,
            y = (diff * 100),
            name = "Difference Line"
        ))

        fig.add_trace(go.Scatter(
            x = imp_df.index,
            y = [mean_line]*len(imp_df),
            name = "Mean Line"
        ))

        fig.update_layout(yaxis_title="Volatility Difference (%)", xaxis_title=f"Date", title=f"Difference (of IV and RV) | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                            size = self.graph_font_size,
                                                                                                            color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        return fig



    def plot_weekly_pnl(self, value_col:str="Values") -> go.Figure:
        """
        Description: Plots the Weekly P/L

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the portfolio value column
        
        return
        =============================
        plotly graph objects
        """
        # resample the dataframe
        df = self.resample_df("W")

        # starting cash
        t = df.index[0] - timedelta(weeks=1)
        df.loc[t, value_col] = initial_cash
        df.sort_index(inplace=True)

        # helper function
        def custom_legend_name(new_names):
            for i, new_name in enumerate(new_names):
                fig.data[i].name = new_name

        # calculate the pnl
        df['pnl'] = df[value_col].diff()
        df.dropna(inplace=True)

        # colors - red if less than 0 else green
        df['PnL'] = df['pnl'].apply(lambda x: "#66a3ff" if x < 0 else "#0047b3")
        df['Type of Gain'] = df['pnl'].apply(lambda x: "Negative" if x < 0 else "Positive")

        fig = px.bar(df, y="pnl", color='PnL', color_discrete_sequence=df["PnL"].unique(), labels={'col1':'postive', 'col2': 'negative'})

        fig.add_trace(go.Scatter(mode="lines", x=df.index, y=[df['pnl'].mean()] * len(df), name="Mean Line", line=dict(color="crimson", dash="dash")))
        fig.add_annotation(
                    y=df['pnl'].mean(),
                    x=df.index[-1],
                    text=str(f"{round(df['pnl'].mean()/1000)}K"),
                    showarrow=False,
                    xshift=30,
                    bgcolor='black',
                    font_color='rgb(255,255,255)',
                    font_size=25
                )
        fig.update_layout(yaxis_title=f"PnL ({self._currency})", xaxis_title=f"Date", title=f"Weekly PnL (Mean = {round(df['pnl'].mean() / 1000)}K {self._currency}) | Condor Strategy {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        if len(df[df['pnl'] > 0]) > 1 and len(df[df['pnl'] < 0]) > 1:
            if df['pnl'].iloc[0] > 0:
                custom_legend_name(["Positive", "Negative"])
            elif df['pnl'].iloc[0] < 0:
                custom_legend_name(["Negative", "Positive"])
        elif len(df[df['pnl'] < 0]) > 1 and len(df[df['pnl'] > 0]) == 0:
            custom_legend_name(["Negative"])
        else:
            custom_legend_name(["Positive"])


        return fig


    def portfolio_value(self, freq:str="D", value_col:str="Values") -> go.Figure:
        """
        Description: Plots the Portfolio Value

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the portfolio value column
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        
        return
        =============================
        plotly graph objects
        """
        # Resample
        df = self.resample_df(frequency=freq)

        # add starting value as cash
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # portfolio values
        values = df[value_col].values

        # create figure object
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = df.index,
            y = values,
            marker = dict(color='darkblue'),
            name = "Portfolio Value"
        ))

        fig.add_annotation(
                    y=values[-1],
                    x=df.index[-1],
                    text=str(f"{round(values[-1]/1000)}K"),
                    showarrow=False,
                    xshift=30,
                    bgcolor='darkblue',
                    font_color='rgb(255,255,255)',
                    font_size=25
                )

        fig.update_layout(yaxis_title=f"Portfolio Value ({self._currency})", xaxis_title=f"Date", title=f"Portfolio Value ({mapper[freq]})| {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                size = self.graph_font_size,
                                                                                                                color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        return fig



    def average_pnl_per_trading_day(self, freq="D", value_col="Values") -> go.Figure:
        """
        Description: Plots the Average P/L per trading day.

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the portfolio value column
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        
        return
        =============================
        plotly graph objects
        """
        # resampling by frequency
        df = self.resample_df(frequency=freq)

        # add starting value as cash
        if freq == "W":
            t = df.index[0] - timedelta(weeks=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)
        elif freq == "D":
            t = df.index[0] - timedelta(days=1)
            df.loc[t, value_col] = initial_cash
            df.sort_index(inplace=True)

        df = df.reset_index()

        # calculate pnl
        df['pnl'] = df[value_col].diff()
        df.dropna(inplace=True)

        # Mark week days
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        df['dayofWeek'] = pd.Series(df["Timestamp"]).apply(lambda x: weekdays[x.weekday()])
        df.set_index("Timestamp", inplace=True)

        # get the average pnl by weekdays
        avg_pnl_perday = df.groupby("dayofWeek")["pnl"].mean()
        # vals = pd.Series(avg_pnl_perday.values).apply(lambda x: str(round(x/1000))+"K")

        # data arrangement
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

        x, y = [], []
        for day in days:
            try:
                y.append(avg_pnl_perday.to_dict()[day])
                x.append(day)
            except:
                y.append(0)
                x.append(day)

        vals = pd.Series(y).apply(lambda x: str(round(x/1000))+"K")
        color = pd.Series(y).apply(lambda x: "#66a3ff" if x < 0 else "#0047b3")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x = x,
            y = y,
            marker=dict(color=color),
            text=vals,
            textposition="inside")
        )

        fig.update_layout(yaxis_title=f"PnL ({self._currency})", xaxis_title=f"Days", title=f"Average PnL Per Trading Day | {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                        size = self.graph_font_size,
                                                                                                                        color = "RebeccaPurple"
                                                                                                                    ), width = self.graph_width, height = self.graph_height, bargap=0.4)

        return fig
    

   # Spread vs P/L 
    def plot_realized_implied_vol_port(self, value_col:str="Implied Vol ATM", freq:str="D", window:int=15) -> go.Figure:
        """
        Description: Plots the Implied and Realized Vol Spread vs the P/L

        parameters
        =============================
        value_col: str, Optional, default: Values
            Name of the portfolio value column
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        window: int, Optional, default: 15
            Size of the lookback window in days.
        
        return
        =============================
        plotly graph objects
        """
        # Resample
        df = self.resample_df(frequency=freq, agg="mean")
        df_portfolio = self.resample_df(frequency=freq)[['Values']]

        underlying_data = self.get_underlying_returns_data()

        # mapper time
        mapper_time = {"D":252, "M":12, "W": 52}

        # Calculate Realized Volatility
        underlying_data['Realized_Vol'] = underlying_data['returns'].rolling(window=window).std() * np.sqrt(mapper_time[freq])

        underlying_data.reset_index(inplace = True)

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # implied volatility values
        values = df[[value_col]]
        values.reset_index(inplace = True)
        values.rename(columns={"Timestamp":"Date"}, inplace=True)

        # get portfolio values
        df_portfolio.reset_index(inplace=True)
        df_portfolio.rename(columns={"Timestamp":"Date"}, inplace=True)

        # merge all information
        underlying_data = underlying_data.merge(values, on="Date")
        underlying_data = underlying_data.merge(df_portfolio, on="Date")
        underlying_data['Spread'] = (underlying_data['Implied Vol ATM'] - underlying_data['Realized_Vol'])
        underlying_data['P/L'] = underlying_data['Values'].diff()
        
        fig = go.Figure()
        fig = make_subplots(specs = [[{"secondary_y": True}]])

        fig.add_trace(go.Scatter(
            x=underlying_data['Date'],
            y=(underlying_data['Spread']*100),
            mode='lines',
            line=dict(color='lightslategrey', width=2),
            name='Spread Volatility'
        ), secondary_y=False)

        fig.add_trace(go.Bar(
            x=underlying_data['Date'],
            y=(underlying_data['P/L']),
            marker_color='crimson',
            name=f'P/L Value ({self._currency})'
        ), secondary_y=True)
        

        fig.update_layout(yaxis_title="Spread (%)", xaxis_title=f"Date", title=f"Daily Volatility Spread (IV - RV) Vs P/L | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                            size = self.graph_font_size,
                                                                                                            color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        fig.update_yaxes(title_text=f'P/L Value ({self._currency})', secondary_y=True)


        return fig


    def pnl_by_trades_taken_on_day(self, pathBlotter:str=os.path.join(output_dir_folder,"blotter")) -> pd.DataFrame:
            """
            Description: Table with P/L's given by all trades taken on those particular days

            parameters
            =============================
            pathBlotter: str
                Path of the blotter files of the backtest
            
            return
            =============================
            pandas DataFrame
            """
            # Expiry List
            def expiry_list(startDate:str, endDate:str, contract_freq:str="nearest_weekly") -> list:
                startDate, endDate = pd.to_datetime(startDate), pd.to_datetime(endDate)
                list = get_expiry_list_from_date_range(startDate, endDate, contract_freq)
                expiry_list = pd.Series(list).apply(lambda x: x.strftime("%Y%m%d")).to_list()

                return expiry_list

            # parameters
            expiry_dates = expiry_list(startDate=f"{str(start_date.year)}-01-01", endDate=f"{str(end_date.year)}-12-31")

            start = f"{str(start_date.year)}-01-01" # starting date of the backtest year

            # Daily P/L calculation
            daily_pnl = pd.DataFrame()

            # Pattern File of Blotter
            blotter_file = "blotter_"

            for dates in expiry_dates:
                try:
                    # take expiry date and take all dates in that month upto expiry
                    date = pd.to_datetime(dates[:4] + "-" + dates[4:6] + "-" + dates[6:]) + timedelta(days=1)
                    start = pd.to_datetime(start)
                    date_range = pd.Series(pd.date_range(start, date - timedelta(days=1), freq='d')).apply(lambda x: x.strftime("%Y%m%d")) # get_dates(start=ranges, end=date)
                    # blotter store for a week
                    blotterStore = pd.DataFrame()

                    # load all blotter files in that month/ week
                    for sdates in date_range:
                        try:
                            blotterFile = blotter_file + sdates + exchange_start_time.strftime("%H:%M:%S").replace(':', '') + "_" + sdates + exchange_end_time.strftime("%H:%M:%S").replace(':', '') + ".csv"
                            blotter = pd.read_csv(os.path.join(pathBlotter,blotterFile))[['time', 'trade_object', 'price', 'position', 'instrument_id']]
                            blotterStore = blotterStore.append(blotter)
                        except Exception as e:
                            print(e)
                    # Week/Month by calculation
                    blotterStore['time'] = pd.to_datetime(blotterStore['time'])
                    blotterStore['Weekday'] = blotterStore['time'].dt.day_name()
                    blotterStore.set_index("time", inplace=True)

                    # pickup strategy, hedge trades & unwind trades
                    strategy = blotterStore[(blotterStore['trade_object'].str.contains("strategy")) | (blotterStore['trade_object'].str.contains("hedge"))]
                    unwind = blotterStore[blotterStore['trade_object'].str.contains("unwind")]

                    # Assigning Days
                    strategy['Day'] = strategy.index.strftime("%Y-%m-%d")
                    unwind['Day'] = unwind.index.strftime("%Y-%m-%d")

                    # P/L Calculation 
                    unwind_data = unwind.reset_index()[['instrument_id', 'position', 'price']]
                    strategy_data = strategy.reset_index()[['instrument_id', 'position', 'price', 'Day']]
                    
                    # Day by day P/L calculation
                    dataMain = strategy_data.merge(unwind_data.drop_duplicates(subset=['instrument_id'])[['price', 'instrument_id']], on='instrument_id', how='left', suffixes=["_strategy_hedge", "_unwind"])
                    dataMain['pnl'] = (dataMain['price_unwind'] - dataMain['price_strategy_hedge']) * (dataMain['position'])
                    
                    # Append all data
                    daily_pnl = daily_pnl.append(dataMain.groupby("Day")['pnl'].sum().reset_index())

                    # update start date
                    start = date
                    
                except Exception as e:
                    pass
            
            # Index Name Set and drop duplicate dates if any
            daily_pnl = daily_pnl.set_index("Day")
            daily_pnl.index.name = "Timestamp"

            daily_pnl = daily_pnl.reset_index()
            daily_pnl = daily_pnl.drop_duplicates(subset=['Timestamp'])
            daily_pnl.set_index("Timestamp", inplace=True)

            return daily_pnl
    

    def plot_by_trade_taken_day(self) -> go.Figure:
        """
        Description: Plots the charts by trade taken on those days
        
        return
        =============================
        plotly graph objects
        """
        # resample and get pnl daywise
        df = self.pnl_by_trades_taken_on_day()
        df.index = pd.to_datetime(df.index)

        # extract the days
        df['Day Name'] = df.index.day_name()
        # Expiry wise booked p/l
        expiry_dates = get_expiry_list_from_date_range(pd.to_datetime(str(start_date.year)+'-01-01'), pd.to_datetime(str(end_date.year)+'-12-31'), "nearest_weekly")
        sdate = pd.to_datetime(str(start_date.year)+'-01-01')

        # expiry dates -> 
        totalDf = pd.DataFrame()

        for exp_date in expiry_dates:
            exp_date = exp_date + timedelta(days=1)
            date_ranges = pd.date_range(sdate, exp_date - timedelta(days=1), freq='d')
            day_count = 1

            newDf = pd.DataFrame()

            for date in date_ranges:
                try:
                    tmpData = pd.DataFrame(df.loc[date, ['pnl', 'Day Name']]).T
                    tmpData['Day No.'] = day_count
                    newDf = pd.concat([newDf, tmpData])
                    day_count += 1
                except Exception as e:
                    pass
            
            week_no, counter = 1, 0
            try:
                for day, date in zip(newDf['Day Name'].to_list(), newDf.index):
                    if day == "Friday" and counter != 0:
                        week_no += 1

                    newDf.loc[date, "Week No."] = "Week "+str(week_no)
                    counter += 1

                totalDf = pd.concat([totalDf, newDf])
                sdate = exp_date
            except Exception as e:
                pass

        totalDf.index.name = "Date"

        # get the average pnl by week
        avg_pnl_perday = totalDf.groupby("Day No.")["pnl"].mean()
        avg_pnl_perweek = totalDf.groupby("Week No.")["pnl"].mean()
        
        # data arrangement
        weeks = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]

        # Week wise P/L
        x, y = [], []
        for week in weeks:
            try:
                y.append(avg_pnl_perweek.to_dict()[week])
                x.append(week)
            except:
                pass

        vals = pd.Series(y).apply(lambda x: str(round(x/1000))+"K")
        color = pd.Series(y).apply(lambda x: "#66a3ff" if x < 0 else "#0047b3")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x = x,
            y = y,
            marker=dict(color=color),
            text=vals,
            textposition="outside")
        )

        fig.update_layout(yaxis_title=f"P/L ({self._currency})", xaxis_title=f"Week", title=f"Average P/L Per Trading Week (by Trading Day) | {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                        size = self.graph_font_size,
                                                                                                                        color = "RebeccaPurple"
                                                                                                                    ), width = self.graph_width, height = self.graph_height, bargap=0.4)
        

        # Day wise P/L
        daysInmonth = [i for i in range(30)]

        x1, y1 = [], []
        for day in daysInmonth:
            try:
                y1.append(avg_pnl_perday.to_dict()[day])
                x1.append("D"+str(day))
            except:
                pass

        vals = pd.Series(y1).apply(lambda x: str(round(x/1000))+"K")
        color = pd.Series(y1).apply(lambda x: "#66a3ff" if x < 0 else "#0047b3")

        fig1 = go.Figure()

        fig1.add_trace(go.Bar(
            x = x1,
            y = y1,
            marker=dict(color=color),
            text=vals,
            textposition="outside")
        )

        fig1.update_layout(yaxis_title=f"P/L ({self._currency})", xaxis_title=f"Days", title=f"Average P/L Per Trading Day (in a Month by Trading Day)| {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                                        size = self.graph_font_size,
                                                                                                                        color = "RebeccaPurple"
                                                                                                                    ), width = self.graph_width, height = self.graph_height, bargap=0.4)


        return fig, fig1
    

    # Spread Change vs P/L 
    def plot_vol_spread_change_pnl(self, value_col:str="Implied Vol ATM", freq:str="D", window:int=15) -> go.Figure:
        """
        Description: Plots the chart of P/L vs Spread Change

        parameters
        =============================
        value_col: str, Optional, default: Implied Vol ATM
            Name of the IV ATM column
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        window: int, default: 15, Optional
            Size of the lookback period
        
        return
        =============================
        plotly graph objects
        """
        # Resample
        df = self.resample_df(frequency=freq, agg="mean")
        df_portfolio = self.resample_df(frequency=freq)[['Values']]

        underlying_data = self.get_underlying_returns_data()

        # mapper time
        mapper_time = {"D":252, "M":12, "W": 52}

        # Calculate Realized Volatility
        underlying_data['Realized_Vol'] = underlying_data['returns'].rolling(window=window).std() * np.sqrt(mapper_time[freq])

        underlying_data.reset_index(inplace = True)

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # implied volatility values
        values = df[[value_col]]
        values.reset_index(inplace = True)
        values.rename(columns={"Timestamp":"Date"}, inplace=True)

        # get portfolio values
        df_portfolio.reset_index(inplace=True)
        df_portfolio.rename(columns={"Timestamp":"Date"}, inplace=True)

        # merge all information
        underlying_data = underlying_data.merge(values, on="Date")
        underlying_data = underlying_data.merge(df_portfolio, on="Date")
        underlying_data['Spread'] = (underlying_data['Implied Vol ATM'] - underlying_data['Realized_Vol'])
        underlying_data['Spread Change'] = underlying_data['Spread'].diff()
        underlying_data['P/L'] = underlying_data['Values'].diff()
        
        fig = go.Figure()
        fig = make_subplots(specs = [[{"secondary_y": True}]])

        fig.add_trace(go.Scatter(
            x=underlying_data['Date'],
            y=(underlying_data['Spread Change'] * 100),
            mode='lines',
            line=dict(color='lightslategrey', width=2),
            name='Volatility Spread Change'
        ), secondary_y=False)

        fig.add_trace(go.Bar(
            x=underlying_data['Date'],
            y=(underlying_data['P/L']),
            marker_color='crimson',
            name=f'P/L Value ({self._currency})'
        ), secondary_y=True)
        

        fig.update_layout(yaxis_title="Change in Spread (%)", xaxis_title=f"Date", title=f"Daily Volatility Spread (IV - RV) Change Vs P/L | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                            size = self.graph_font_size,
                                                                                                            color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width, height = self.graph_height)

        fig.update_yaxes(title_text=f'P/L Value ({self._currency})', secondary_y=True)


        return fig
    

    # Spread vs P/L by trade taken
    def plot_vol_spread_pnl_trades_taken(self, value_col:str="Implied Vol ATM", freq:str="D", window:int=15) -> go.Figure:
        """
        Description: Plots the IV RV Spread and P/L of Days by Trades Taken

        parameters
        =============================
        value_col: str, Optional, default: Implied Vol ATM
            Name of the IV ATM column
        freq: str, Optional, default: D
            Frequency of the data required for plotting
        window: int, default: 15, Optional
            Size of the lookback period
        
        return
        =============================
        plotly graph objects
        """
        # Resample
        df = self.resample_df(frequency=freq, agg="mean")
        df_portfolio = self.pnl_by_trades_taken_on_day()
        df_portfolio.index.name = "Date"
        df_portfolio.index = pd.to_datetime(df_portfolio.index)
        df_portfolio.rename(columns={"pnl":"P/L"}, inplace=True)

        underlying_data = self.get_underlying_returns_data()

        # mapper time
        mapper_time = {"D":252, "M":12, "W": 52}

        # Calculate Realized Volatility
        underlying_data['Realized_Vol'] = underlying_data['returns'].rolling(window=window).std() * np.sqrt(mapper_time[freq])

        underlying_data.reset_index(inplace = True)

        # maps time
        mapper = {"D":"Daily", "M":"Monthly", "Q":"Quarterly", "W":"Weekly"}

        # implied volatility values
        values = df[[value_col]]
        values.reset_index(inplace = True)
        values.rename(columns={"Timestamp":"Date"}, inplace=True)

        # get portfolio values
        df_portfolio.reset_index(inplace=True)
        df_portfolio.rename(columns={"Timestamp":"Date"}, inplace=True)

        # merge all information
        underlying_data = underlying_data.merge(values, on="Date")
        underlying_data = underlying_data.merge(df_portfolio, on="Date")
        underlying_data['Spread'] = (underlying_data['Implied Vol ATM'] - underlying_data['Realized_Vol'])
        underlying_data['Spread Change'] = underlying_data['Spread'].diff()
        
        fig = go.Figure()
        fig = make_subplots(specs = [[{"secondary_y": True}]])

        fig.add_trace(go.Scatter(
            x=underlying_data['Date'],
            y=(underlying_data['Spread'] * 100),
            mode='lines',
            line=dict(color='lightslategrey', width=2),
            name='Volatility Spread'
        ), secondary_y=False)

        fig.add_trace(go.Bar(
            x=underlying_data['Date'],
            y=(underlying_data['P/L']),
            marker_color='crimson',
            name=f'P/L Value ({self._currency})'
        ), secondary_y=True)
        

        fig.update_layout(yaxis_title="Spread (%)", xaxis_title=f"Date", title=f"Daily Volatility Spread (IV - RV) Vs P/L (by Trading Day) | {self._name} {self.underlying} ({self.startMonth} {self.startYear} - {self.endMonth} {self.endYear})", font=dict(family = "Courier New, monospace",
                                                                                                            size = self.graph_font_size,
                                                                                                            color = "RebeccaPurple"
                                                                                                            ), width = self.graph_width + 100, height = self.graph_height)

        fig.update_yaxes(title_text=f'P/L Value ({self._currency})', secondary_y=True)


        return fig
    

    def risk_chart_plots(self, log_file_path:str) -> go.Figure:

        contract_info = pd.DataFrame(columns=["Contracts"])
        log_file_path = glob.glob(os.path.join(output_dir_folder, "*.log"))[0] # log file fetching 

        try:
            with open(log_file_path, 'r') as file:
                for line in file:
                    if "final " in line:
                        try:
                            year, month, day, hour, min, sec, contracts, _ = re.sub("[^0-9]", " ", line.split("INFO")[1]).split()
                            date = pd.to_datetime("-".join([year, month, day]) + " " + ":".join([hour, min, sec]))
                            contracts = int(contracts)

                            contract_info.loc[date, "Contracts"] = contracts
                        except Exception as e:
                            pass

            # plot figure
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x = contract_info.index,
                y = contract_info['Contracts'],
                name="Constant Risk"
            ))

            fig.update_layout(plot_bgcolor="white", xaxis_title="Date", yaxis_title="No. of Contract", title=f"No. of Contracts (Constant Risk)| {underlying} {month_mapper[start_date.month]}-{start_date.year} - {month_mapper[end_date.month]}-{end_date.year} | (C.B - 90K, Avg Contract - {round(contract_info['Contracts'].mean()/1000)}K)", font=dict(
                family = "Courier new, monospace",
                size = self.graph_font_size, 
                color = "RebeccaPurple"
            ), width = self.graph_width + 100, height = self.graph_height)

            fig.update_xaxes(
                            mirror=True,
                            ticks='outside',
                            showline=True,
                            linecolor='black',
                            gridcolor='white')
            
            fig.update_yaxes(
                        mirror=True,
                        ticks='outside',
                        showline=True,
                        linecolor='black',
                        gridcolor='white')

            return fig

        except FileNotFoundError:
            print(f"File not found: {log_file_path}")
        except Exception as e:
            print(f"An error occurred: {e}")