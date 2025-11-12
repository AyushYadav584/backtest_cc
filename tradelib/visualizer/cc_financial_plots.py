import datetime
import os
import numpy as np
import pandas as pd
import empyrical as ep
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff

from scipy.optimize import minimize
from plotly.subplots import make_subplots

import plotly.io as pio
pio.templates.default = "simple_white"


def plot_efficient_frontier(df:pd.DataFrame, frequency:str="D", num_ports:int=10000, risk_free_rate:int=0, colorscale:str="aggrnyl", ef_line:bool=False, custom_weights:list=[], graph_width:int=1600, graph_height:int=600) -> go.Figure:
    '''
    Plots the Markowitz Efficient Frontier given a dataframe that contains the asset prices
    for a given period.

    Parameters
    ----------
    df : Pandas DataFrame object
        DataFrame containing the asset prices
    frequency : str, default 'D'    Frequency of the data
    num_ports : int, default 10000
        The number of portfolios to generate
    risk_free_rate : str, default 0
        Market's risk free rate
    colorscale : Color map of the efficient frontier, default 'aggrnyl'
    ef_line: bool, default False
        Plots only the Efficient Frontier Line
    custom_weights: np.array or list, default []
        custom weights to be plotted on the Efficient Frontier
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object

    Returns
    -------
    plotly.graph_objects : Plots the Efficient Frontier

    Example
    -------
    >>> df.head(2)

                    TCS  NTPC  INFY
    Dates
    2022-01-01      200  300   400
    2022-01-02      202  299   401


    >>> plot_efficient_frontier(df)
    '''
    # Type checking
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (num_ports > 1), "Number of portfolio cannot be less than 1"
    assert (risk_free_rate >= 0), "risk free rate cannot be negative"
    assert (str(type(ef_line))=="<class 'bool'>"), "Not a boolean variable"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"

    try:
        # Mapping the frequencies
        mapper = {'D': 252, 'M': 12, 'W': 52, 'Q': 4, 'Y': 1, '6M': 2}

        # Calculating the annualized returns and volatilities
        rets = df.pct_change().dropna().mean() * mapper[frequency]
        cov = df.pct_change().dropna().cov() * mapper[frequency]

        # Only efficient frontier portfolios
        mean_variance_ef_portfolios = []

        # Generating various portfolios
        np.random.seed(42)
        all_weights = np.zeros((num_ports, len(df.columns)))
        ret_arr = np.zeros(num_ports)
        vol_arr = np.zeros(num_ports)
        sharpe_arr = np.zeros(num_ports)

        # Lists to store various weight combinations and assets.
        all_weights_plot = []
        all_ticker_plot = []


        # Plot all portfolio / Plot only efficient portfolios
        if ef_line:

            for x in range(num_ports):
                # Weights
                weights = np.array(np.random.random(len(df.columns)))
                weights = weights / np.sum(weights)

                # Save weights
                all_weights[x, :] = weights

                # Expected return
                ret_arr[x] = np.sum((rets * weights))

                # Expected volatility
                vol_arr[x] = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))

                # Sharpe Ratio
                sharpe_arr[x] = (ret_arr[x] - risk_free_rate) / vol_arr[x]

                track = False
                # Check for optimal portfolios
                for v, r, _ in mean_variance_ef_portfolios:
                    if (r > ret_arr[x]) and (v < vol_arr[x]):
                        track = True
                        break

                if track != True:
                    # Storing weights and tickers for portfolio plots
                    all_weights_plot.append(all_weights[x])
                    all_ticker_plot.append(list(df.columns))
                    mean_variance_ef_portfolios.append([vol_arr[x], ret_arr[x], sharpe_arr[x]])


            # Max seen return in simulation
            indices_max_r = max(np.array(mean_variance_ef_portfolios)[:, 1])

            # Min seen return in simulation
            indices_min_r = min(np.array(mean_variance_ef_portfolios)[:, 1])


            # Efficient Frontier Line Calculations
            def checkSumToOne(w: np.array):
                return np.sum(w) - 1

            def getReturn(w: np.array):
                w = np.array(w)
                R = np.sum(rets * w)
                return R

            def minimizeMyVolatility(w: np.array):
                w = np.array(w)
                V = np.sqrt(np.dot(w.T, np.dot(cov, w)))
                return V

            def get_efficient_frontier():
                returns = np.linspace((indices_min_r - 0.05), indices_max_r, 20)
                volatility_opt = []

                # Defining starting weights (equal weights)
                w0 = [1/len(rets)] * len(rets)

                # Defining bounds
                if len(rets) == 1:
                    bounds = (0, 1)
                else:
                    bounds = ((0, 1), ) * len(rets)


                for ret in returns:
                    # Find best volatility

                    # Constraints
                    constraints = ({'type':'eq', 'fun':checkSumToOne},
                                   {'type': 'eq', 'fun': lambda w: getReturn(w) - ret})

                    opt = minimize(minimizeMyVolatility, w0, method='SLSQP', bounds=bounds, constraints=constraints)

                    # Save optimal volatility
                    volatility_opt.append(opt['fun'])

                return volatility_opt, returns


            # EF Line Volatilities, Returns
            volas, retus = get_efficient_frontier()


            # Type casting
            mean_variance_ef_portfolios = np.array(mean_variance_ef_portfolios)

            # Max Sharpe Portfolio
            indices_max_sr = mean_variance_ef_portfolios[:, 2].argmax()
            max_sr_ret = mean_variance_ef_portfolios[:, 1][indices_max_sr]
            max_sr_vol = mean_variance_ef_portfolios[:, 0][indices_max_sr]
            max_sr_weights = all_weights_plot[indices_max_sr]


            # Min Vol Portfolio
            indices_min_vol = mean_variance_ef_portfolios[:, 0].argmin()
            min_vol_ret = mean_variance_ef_portfolios[:, 1][indices_min_vol]
            min_vol_vol = mean_variance_ef_portfolios[:, 0][indices_min_vol]
            min_vol_weights = all_weights_plot[indices_min_vol]

            # Plot the efficient frontier
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                y = mean_variance_ef_portfolios[:, 1],
                x = mean_variance_ef_portfolios[:, 0],
                mode = 'markers',
                name = 'Portfolios',
                marker = dict(color=mean_variance_ef_portfolios[:, 2],
                showscale = True,
                size = 5,
                line = dict(width=1),
                colorscale = colorscale,
                colorbar = dict(title="Sharpe<br>Ratio")),
                text = [str(np.array(all_ticker_plot[i])) + "<br>" + str(np.array(all_weights_plot[i]).round(2)) for i in range(len(all_ticker_plot))]
            ))

            # Max Sharpe Plot
            fig.add_trace(go.Scatter(
                y = [max_sr_ret],
                x = [max_sr_vol],
                mode = 'markers',
                marker_symbol = 'star',
                marker = dict(color='red', size=16),
                text = str(np.array(all_ticker_plot[indices_max_sr])) + "<br>" + str(np.array(max_sr_weights).round(2)),
                name = "Maximum Sharpe Ratio Portfolio"
            ))

            # Min Vol Plot
            fig.add_trace(go.Scatter(
                y = [min_vol_ret],
                x = [min_vol_vol],
                mode = 'markers',
                marker_symbol = 'diamond',
                marker = dict(color='black', size=16),
                text = str(np.array(all_ticker_plot[indices_min_vol])) + "<br>" + str(np.array(min_vol_weights).round(2)),
                name = "Minimum Volatility Portfolio"
            ))

            # Only Line
            fig.add_trace(go.Scatter(
                y = retus,
                x = volas,
                mode = 'lines',
                line = dict(shape = 'linear', color = 'rgb(10, 120, 24)', dash = 'dot'),
                name = "Efficient Frontier Line"
            ))


            # custom portfolios
            ret_custom, vol_custom, stocks_custom, wts_custom = [], [], [], []

            if len(custom_weights) > 0:
                for wts in custom_weights:
                    wts = np.array(wts)
                    ret_custom.append(np.sum(wts * rets))
                    vol_custom.append(np.sqrt(np.dot(wts.T, np.dot(cov, wts))))
                    stocks_custom.append(list(df.columns))
                    wts_custom.append(wts)

            if len(custom_weights) > 0:
                fig.add_trace(go.Scatter(
                    y = ret_custom,
                    x = vol_custom,
                    mode = 'markers',
                    name = 'Custom Portfolios',
                    marker = dict(color='blue', size=16),
                    marker_symbol = 'triangle-up',
                    text = [str(np.array(stocks_custom[i])) + "<br>" + str(np.array(wts_custom[i]).round(2)) for i in range(len(stocks_custom))]
                ))

            # Add title/labels
            fig.update_layout(template='plotly_white',
                            xaxis=dict(title='Annualised Risk (Volatility)'),
                            yaxis=dict(title='Annualised Return'),
                            title='Markowitz Efficient Frontier',
                            coloraxis_colorbar=dict(title="Sharpe Ratio"),
                            legend=dict(yanchor="bottom", y=0.1, xanchor="right", x=0.99),
                            font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color="RebeccaPurple"
                                    ), width = graph_width, height = graph_height)

            return fig

        else:

            for x in range(num_ports):
                # Weights
                weights = np.array(np.random.random(len(df.columns)))
                weights = weights / np.sum(weights)

                # Save weights
                all_weights[x, :] = weights

                # Expected return
                ret_arr[x] = np.sum((rets * weights))

                # Expected volatility
                vol_arr[x] = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))

                # Sharpe Ratio
                sharpe_arr[x] = (ret_arr[x] - risk_free_rate) / vol_arr[x]

                # Storing weights and tickers for portfolio plots
                all_weights_plot.append(all_weights[x])
                all_ticker_plot.append(list(df.columns))

            # Max Sharpe Portfolio
            indices_max_sr = sharpe_arr.argmax()
            max_sr_ret = ret_arr[indices_max_sr]
            max_sr_vol = vol_arr[indices_max_sr]
            max_sr_weights = all_weights[indices_max_sr]


            # Min Vol Portfolio
            indices_min_vol = vol_arr.argmin()
            min_vol_ret = ret_arr[indices_min_vol]
            min_vol_vol = vol_arr[indices_min_vol]
            min_vol_weights = all_weights[indices_min_vol]


            # Plot the efficient frontier
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                y = ret_arr,
                x = vol_arr,
                mode = 'markers',
                name = 'Portfolios',
                marker = dict(color=sharpe_arr,
                showscale = True,
                size = 5,
                line = dict(width=1),
                colorscale = colorscale,
                colorbar = dict(title="Sharpe<br>Ratio")),
                text = [str(np.array(all_ticker_plot[i])) + "<br>" + str(np.array(all_weights_plot[i]).round(2)) for i in range(len(all_ticker_plot))]
            ))

            # Max Sharpe Plot
            fig.add_trace(go.Scatter(
                y = [max_sr_ret],
                x = [max_sr_vol],
                mode = 'markers',
                marker_symbol = 'star',
                marker = dict(color='red', size=16),
                text = str(np.array(all_ticker_plot[indices_max_sr])) + "<br>" + str(np.array(max_sr_weights).round(2)),
                name = "Maximum Sharpe Ratio Portfolio"
            ))

            # Min Vol Plot
            fig.add_trace(go.Scatter(
                y = [min_vol_ret],
                x = [min_vol_vol],
                mode = 'markers',
                marker_symbol = 'diamond',
                marker = dict(color='black', size=16),
                text = str(np.array(all_ticker_plot[indices_min_vol])) + "<br>" + str(np.array(min_vol_weights).round(2)),
                name = "Minimum Volatility Portfolio"
            ))

            # custom portfolios
            ret_custom, vol_custom, stocks_custom, wts_custom = [], [], [], []

            if len(custom_weights) > 0:
                for wts in custom_weights:
                    wts = np.array(wts)
                    ret_custom.append(np.sum(wts * rets))
                    vol_custom.append(np.sqrt(np.dot(wts.T, np.dot(cov, wts))))
                    stocks_custom.append(list(df.columns))
                    wts_custom.append(wts)

            if len(custom_weights) > 0:
                fig.add_trace(go.Scatter(
                    y = ret_custom,
                    x = vol_custom,
                    mode = 'markers',
                    name = 'Custom Portfolios',
                    marker = dict(color='blue', size=16),
                    marker_symbol = 'triangle-up',
                    text = [str(np.array(stocks_custom[i])) + "<br>" + str(np.array(wts_custom[i]).round(2)) for i in range(len(stocks_custom))]
                ))

            # Add title/labels
            fig.update_layout(template='plotly_white',
                            xaxis=dict(title='Annualised Risk (Volatility)'),
                            yaxis=dict(title='Annualised Return'),
                            title='Markowitz Efficient Frontier',
                            coloraxis_colorbar=dict(title="Sharpe Ratio"),
                            legend=dict(yanchor="bottom", y=0.1, xanchor="right", x=0.99),
                            font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color="RebeccaPurple"
                                    ), width = graph_width, height = graph_height)

            return fig

    # Exceptions other than Assertion Errors.
    except Exception as e:
        print(e)





def return_plots(df:pd.DataFrame, frequency:str="D", strategy:str='', graph_width:int=1600, graph_height:int=600, yaxis:str="Cumulative Return (%)",
                                                                                                        xaxis:str="", title:str="Cumulative Returns", x_shift:int=25) -> go.Figure:
    '''
    Plots the returns over a period of time for all assets in the given
    dataframe.

    Parameters
    ----------
    df : Pandas DataFrame object
        DataFrame containing the asset prices
    frequency : str, default 'D'    Frequency of the data
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    yaxis : str, default - 'Cumulative Return (%)'
        Label on the yaxis
    xaxis : str, default - ''
        Label on the xaxis
    title : str, default - ''
        Title of the chart
    x_shift : int, default - 25
        Position of the annotation

    Returns
    -------
    plotly.graph_objects : Plots the Return Charts

    Example
    -------
    >>> df.head(2)

                    TCS  NTPC  INFY
    Dates
    2022-01-01      200  300   400
    2022-01-02      202  299   401


    >>> return_plots(df)
    '''
    # Type checking
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(strategy)) == "<class 'str'>"), "Not a string"
    assert (str(type(yaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"

    try:
        # Cumulative Returns
        cum_returns = ((1 + df.pct_change().fillna(0)).cumprod() - 1) * 100

        # Mapping the frequencies
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Yearly'}

        if xaxis == "":
            xaxis = mapper[frequency]

        # Plotting all plots
        fig = go.Figure()

        for assets in cum_returns.columns:
            fig.add_trace(go.Scatter(
                y = cum_returns[f'{assets}'],
                x = cum_returns.index,
                name = f'{assets}'
            ))

            fig.add_annotation(
                y=cum_returns[f'{assets}'].iloc[-1],
                x=cum_returns.index[-1],
                text=str(round(cum_returns[f'{assets}'].iloc[-1], 2)),
                showarrow=False,
                xshift=x_shift,
                bgcolor='rgb(255,0,0)',
                font_color='rgb(255,255,255)'
            )

        fig.update_layout(yaxis_title=yaxis, xaxis_title=xaxis, title=f"{title} {strategy}", font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color="RebeccaPurple"
                                    ), width = graph_width, height = graph_height)

        return fig

    except Exception as e:
        print(e)





def rolling_volatility_plots(df:pd.DataFrame, frequency:str="D", windows:int=30, strategy:str='', graph_width:int=1600, graph_height:int=600, yaxis:str="Volatility (%)",
                                                                                                        xaxis:str="", title:str="Rolling Volatility", x_shift:int=25) -> go.Figure:
    '''
    Plots the rolling volatilities over a period of time for all assets in the given
    dataframe.

    Parameters
    ----------
    df : Pandas DataFrame object
        DataFrame containing the asset prices
    frequency : str, default 'D'    Frequency of the data
    windows : int, default 30
        Size of the rolling window for calculation of volatility
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    yaxis : str, default - 'Cumulative Return (%)'
        Label on the yaxis
    xaxis : str, default - ''
        Label on the xaxis
    title : str, default - ''
        Title of the chart
    x_shift : int or float, default - 25
        Position of annotation

    Returns
    -------
    plotly.graph_objects : Plots the Rolling Volatility Charts

    Example
    -------
    >>> df.head(2)

                    TCS  NTPC  INFY
    Dates
    2022-01-01      200  300   400
    2022-01-02      202  299   401


    >>> volatility_plots(df)
    '''
    # Type checking
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (str(type(windows))) == "<class 'int'>", "Expects an integer value"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(strategy)) == "<class 'str'>"), "Not a string"
    assert (str(type(yaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"


    try:
        # Mapping the frequencies
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Yearly'}

        # Time Mapper
        mapper_time = {'D': 252, 'M': 12, 'W': 52, 'Q': 4, 'Y': 1, '6M': 2}

        # Volatility
        volas = df.pct_change().rolling(window=windows).std().apply(lambda x: x * np.sqrt(mapper_time[frequency])).dropna() * 100

        if xaxis == "":
            xaxis = mapper[frequency]

        # Plotting all plots
        fig = go.Figure()

        for assets in volas.columns:
            fig.add_trace(go.Scatter(
                y = volas[f'{assets}'],
                x = volas.index,
                name = f'{assets}'
            ))

            fig.add_annotation(
                y=volas[f'{assets}'].iloc[-1],
                x=volas.index[-1],
                text=str(round(volas[f'{assets}'].iloc[-1], 2)),
                showarrow=False,
                xshift=x_shift,
                bgcolor='rgb(255,0,0)',
                font_color='rgb(255,255,255)'
            )

        fig.update_layout(yaxis_title=yaxis, xaxis_title=xaxis, title=f"{title} {strategy}", font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color="RebeccaPurple"
                                    ), width = graph_width, height = graph_height)
        return fig

    except Exception as e:
        print(e)





def rolling_max_drawdown_plots(df:pd.DataFrame, frequency:str='D', windows:int=10, strategy:str='', graph_width:int=1600, graph_height:int=600,
                                                        yaxis:str="Maximum Drawdown in (%)", xaxis:str="", title:str="Rolling Maximum Drawdown") -> go.Figure:
    '''
    Plots the rolling max drawdown over a period of time for all assets in the given
    dataframe.

    Parameters
    ----------
    df : Pandas DataFrame object
        DataFrame containing the asset prices
    frequency : str, default 'D'    Frequency of the data
    windows : int, default 10
        Size of the rolling window for calculation of max drawdown
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    yaxis : str, default - 'Cumulative Return (%)'
        Label on the yaxis
    xaxis : str, default - ''
        Label on the xaxis
    title : str, default - ''
        Title of the chart

    Returns
    -------
    plotly.graph_objects : Plots the Rolling Maximum Drawdown Charts

    Example
    -------
    >>> df.head(2)

                    TCS  NTPC  INFY
    Dates
    2022-01-01      200  300   400
    2022-01-02      202  299   401


    >>> drawdown_plots(df)
    '''
    # Type checking
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (str(type(windows))) == "<class 'int'>", "Expects an integer value"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(strategy)) == "<class 'str'>"), "Not a string"
    assert (str(type(yaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"


    try:
        # Mapping the frequencies
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Year'}

        # Maximum Drawdown
        rolling_max = df.rolling(window=windows).max()
        rolling_max_diff_close = (df / rolling_max) - 1
        max_drawdown_ = rolling_max_diff_close.rolling(window=windows).min().dropna() * 100

        if xaxis == "":
            xaxis = mapper[frequency]


        # Plotting all plots
        fig = go.Figure()

        for assets in max_drawdown_.columns:
            fig.add_trace(go.Scatter(
                y = max_drawdown_[f'{assets}'],
                x = max_drawdown_.index,
                name = f'{assets}',
                fill = 'tozeroy'
            ))

        fig.update_layout(yaxis_title=yaxis, xaxis_title=xaxis, title=f"{title} {strategy}", font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color = "RebeccaPurple"
                                    ), width = graph_width, height = graph_height)
        return fig

    except Exception as e:
        print(e)





def annualised_periodic_returns(df:pd.DataFrame, securities:list, strategy:str='', frequency:str='D', graph_width:int=1600, graph_height:int=600,
                                                                    yaxis:str="Return Percentage (%)", xaxis:str="", title:str="Annualised Return") -> go.Figure:
    '''
    Plots the annualised returns over a period of time in the given dataframe

    Parameters
    ----------
    df : Pandas DataFrame object
        DataFrame containing the asset prices
    frequency : str, default 'D'   Frequency of the data
    securities : list, default - blank list
        Contains the name of the securities
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    yaxis : str, default - 'Cumulative Return (%)'
        Label on the yaxis
    xaxis : str, default - ''
        Label on the xaxis
    title : str, default - ''
        Title of the chart

    Returns
    -------
    plotly.graph_objects : Plots the Annualised Returns

    '''

    # Type checking
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(strategy)) == "<class 'str'>"), "Not a string"
    assert (str(type(securities)) == "<class 'list'>"), "Not a list object"
    assert (str(type(yaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"


    try:
        # Mapping the frequencies
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Yearly'}

        if xaxis == "":
            xaxis = mapper[frequency]

        fig = go.Figure()

        # plotting each security and their means
        for name in securities:
            periods = list(df.columns)
            periods.remove('Security Name')

            periodic_returns = (df[df['Security Name']==name].loc['Return'].values[:]).tolist()
            periodic_returns.remove(name)
            periodic_returns = np.array(periodic_returns).astype('float')
            mean_returns = np.mean(periodic_returns)


            fig.add_trace(go.Bar(
                y = periodic_returns,
                x = periods,
                name = f'{name}',
                text = periodic_returns,
                textposition = 'outside'
            ))


            fig.add_trace(go.Scatter(y = [mean_returns, mean_returns],
                                    x = [min(periods), max(periods)],
                                    mode = 'lines',
                                    line = dict(width=2, dash='dash'),
                                    name = f'Mean {name}')
                        )

        fig.update_layout(yaxis_title=f"{yaxis}", xaxis_title=f"{xaxis}", showlegend=True, title=f"{title} {strategy}", font=dict(
                                                                                                                                    family = "Courier New, monospace",
                                                                                                                                    size = 12,
                                                                                                                                    color="RebeccaPurple"
                                                                                                                                    ), width = graph_width, height = graph_height)
        return fig

    except Exception as e:
        print(e)





def max_drawdown_plots(df:pd.DataFrame, strategy:str='', frequency:str='D', graph_width:int=1600, graph_height:int=600, yaxis:str="Maximum Drawdown (%)",
                                                                                                                    xaxis:str="", title:str="Maximum Drawdown") -> go.Figure:
    '''
    Plots the drawdown over a period of time for all assets in the given
    dataframe.

    Parameters
    ----------
    df : Pandas DataFrame object
        DataFrame containing the asset prices
    frequency : str, default 'D'   Frequency of the data
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    yaxis : str, default - 'Cumulative Return (%)'
        Label on the yaxis
    xaxis : str, default - ''
        Label on the xaxis
    title : str, default - ''
        Title of the chart

    Returns
    -------
    plotly.graph_objects : Plots the Drawdown Charts

    Example
    -------
    >>> df.head(2)
                    TCS  NTPC  INFY
    Dates
    2022-01-01      200  300   400
    2022-01-02      202  299   401

    >>> drawdown_plots(df)
    '''
    # Type checking
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(strategy)) == "<class 'str'>"), "Not a string"
    assert (str(type(yaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"

    try:
        # Mapping the frequencies
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Yearly'}

        if xaxis == "":
            xaxis = mapper[frequency]

        returns = df.pct_change().fillna(0)
        df_cum_rets = ep.cum_returns(returns, starting_value=1.0)
        running_max = np.maximum.accumulate(df_cum_rets)
        underwater = -100 * ((running_max - df_cum_rets) / running_max)

        # Plotting all plots
        fig = go.Figure()
        for assets in underwater.columns:
            fig.add_trace(go.Scatter(
                y = underwater[f'{assets}'],
                x = underwater.index,
                fill='tozeroy',
                name = f'{assets}'
            ))

        fig.update_layout(yaxis_title=yaxis, xaxis_title=f"{xaxis}", title=f"{title} {strategy}", font=dict(family = "Courier New, monospace",
                                                                                                            size = 12,
                                                                                                            color = "RebeccaPurple"
                                                                                                        ), width = graph_width, height = graph_height)

        return fig

    except Exception as e:
        print(e)





def plotly_create_subplots(*figs, column: int, row: int, subplot_title: tuple,
            xaxes_title=None, yaxes_title=None, hs:float=0.15) -> go.Figure:
    """
    This function helps us to create sub plots in plotly

    Parameters:
    -----------
        column : int
            Number of columns
        row : int
            Number of rows
        subplot_title : tuple
            subplot title
        xaxes_title : str, optional
            Title of X axis (defaults None).
        yaxes_title : str, optional
            Title of Y axis (defaults None).
        hs : float, default - 0.15
            Horizontal spacing between the subplots

    Returns:
    --------
        go.Figure : object
    """

    assert(len(figs) <= column*row), "Shape mismatched"
    assert(len(figs) == len(subplot_title)), "Number of subplot and number of subplot title are mismatched"

    try:
        fig_sub_plot_object = make_subplots(rows=row, cols=column, subplot_titles=subplot_title, horizontal_spacing=hs)
        row_idx = 1
        col_idx = 1
        for fig in figs:
            for i in range(len(fig.data)):
                fig_sub_plot_object.add_trace(fig.data[i], row=row_idx, col=col_idx)
            fig_sub_plot_object.update_xaxes(title_text=xaxes_title, row=row_idx, col=col_idx)
            fig_sub_plot_object.update_yaxes(title_text=yaxes_title, row=row_idx, col=col_idx)
            col_idx += 1
            if col_idx > column:
                row_idx += 1
                col_idx = 1

        return fig_sub_plot_object

    except Exception as e:
        print(e)





def plotly_figure_show(figure: go.Figure, height: int=600, width: int=800, figure_title: str=None) -> None:
    """
    This function help us to show the plotly plots

    Parameters:
    -----------
        figure : plotly.Figure
            plotly figure object which we want to show
        height : int, optional
            height of the plot (default 600).
        width : int, optional
            width of the plot (default 800).
        figure_title : str, optional
            title of the figure. (defaults None).
    """
    try:

        figure.update_layout(height=height, width=width, title_text=figure_title)
        figure.show()

    except Exception as e:
        print(e)





def general_plots(df:pd.DataFrame, frequency:str="D", strategy:str='', graph_width:int=1600, graph_height:int=600, y_title:str='', chart_title:str='', x_title:str='', x_shift:int=25) -> go.Figure:
    '''
    Plots any given dataframe

    Parameters
    ----------
    df : Pandas DataFrame object
        DataFrame containing the asset prices
    frequency : str, default 'D'    Frequency of the data
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    y_title : str, default - ''
        Y axis title
    x_title : str, default - ''
        X axis title
    chart_title : str, default - ''
        Title of the chart
    x_shift : int, default - 25
        position of annotation on axis

    Returns
    -------
    plotly.graph_objects : Plots Any DataFrame

    Example
    -------
    >>> df.head(2)

                    TCS  NTPC  INFY
    Dates
    2022-01-01      200  300   400
    2022-01-02      202  299   401


    >>> general_plots(df)
    '''
    # Type checking
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(strategy)) == "<class 'str'>"), "Not a string"
    assert (str(type(y_title)) == "<class 'str'>"), "Not a string"
    assert (str(type(chart_title)) == "<class 'str'>"), "Not a string"
    assert (str(type(x_title)) == "<class 'str'>"), "Not a string"

    try:
        # Mapping the frequencies
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Yearly'}

        # Plotting all plots
        fig = go.Figure()

        for assets in df.columns:
            fig.add_trace(go.Scatter(
                y = df[f'{assets}'],
                x = df.index,
                name = f'{assets}'
            ))

            fig.add_annotation(
                y=df[f'{assets}'].iloc[-1],
                x=df.index[-1],
                text=str(round(df[f'{assets}'].iloc[-1], 2)),
                showarrow=False,
                xshift=x_shift,
                bgcolor='rgb(255,0,0)',
                font_color='rgb(255,255,255)'
            )

        fig.update_layout(yaxis_title=f"{y_title}", xaxis_title=f"{x_title}", title=f"{chart_title} {strategy}", font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color="RebeccaPurple"
                                    ), width = graph_width, height = graph_height)
        return fig

    except Exception as e:
        print(e)





def plot_returns_heatmap(returns:pd.DataFrame, z:float, strategy:str='', frequency:str='D', graph_width:int=1600, graph_height:int=600, color_scale_heatmap:str='RdYlGn',
                                                                                                    yaxis:str="Month",
                                                                                                    xaxis:str="", title:str="Return Heatmap in (%)", colorbar_title:str="Return (%)") -> go.Figure:
    """
    Plots a heatmap of returns

    Parameters
    ----------
    returns : pd.DataFrame
        Daily, Monthly, Weekly etc. returns of the strategy, noncumulative
    frequency : str, default 'D'    Frequency of the data
    strategy : str, default - blank string
        Name of the strategy
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    color_scale_heatmap : str, default - "RdYlGn"
        color scale of the heatmap
    yaxis : str, default - 'Cumulative Return (%)'
        Label on the yaxis
    xaxis : str, default - ''
        Label on the xaxis
    title : str, default - ''
        Title of the chart
    colorbar_title : str, default - Return
        Title of the colorbar
    z : float, int default - None
        range of the colorbar

    Returns
    -------
    plotly.graph_objects : Plots a Heatmap
    """
    # Type checking
    assert (str(type(returns)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'Q', 'W', 'Y', '6M'"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(strategy)) == "<class 'str'>"), "Not a string"
    assert (str(type(color_scale_heatmap)) == "<class 'str'>"), "Not a string"
    assert (str(type(yaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis)) == "<class 'str'>"), "Not a string"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"
    assert (str(type(colorbar_title)) == "<class 'str'>"), "Not a string"

    try:
        # Mapping the frequencies
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Yearly'}

        if xaxis == "":
            xaxis = "Year"

        fig = px.imshow(returns,
                         labels=dict(color=f"{colorbar_title}"),
                         color_continuous_scale=color_scale_heatmap,
                         text_auto=True,
                         zmin=-z,
                         zmax=z
               )

        fig.update_layout(yaxis_title=f"{yaxis}", xaxis_title=f"{xaxis}", title=f"{title} {strategy}", font=dict(family = "Courier New, monospace",
                                          size = 12,
                                          color="RebeccaPurple"
                                        ), width = graph_width, height = graph_height)


        return fig

    except Exception as e:
        print(e)





def rv_distribution_scatter_plots(data:pd.DataFrame, scatter:bool=False, colors:list=['#A56CC1'], graph_width:int=800, graph_height:int=400, frequency:str='M',
                                                            price_col:str='Adj Close', date_col:str='Date', single_scatter=False, annualised:bool=False) -> go.Figure:
    '''
    Plots the scatter and distribution plots for return and volatilities

    Parameters
    ----------
    data : pd.DataFrame, default - None
        A dataframe containing the prices with a Date column
    scatter : bool, default - False
        Plots the scatter plot
    single_scatter : bool, deafult - False
        Plot single variable scatter plots
    colors: list, default - ['#A56CC1']
        colors for the plots
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    frequency : str, default - 'M'
        frequncy over which Return and Volatility plots to be plotted
    price_col : str, default - 'Adj Close'
        Price column of the dataframe
    annualised : bool, default - False
        Annualise the returns and the volatility
    date_col : str, default - 'Date
        Name of the date column
    
    Return
    ------
    plotly.graph_objects (tuples): Plotly scatter and displot objects

    3 object tuple : single_scatter = True
    1 object tuple : single_scatter = False, scatter = True
    2 object tuple : single_scatter = False, scatter = False 
    '''
    assert (str(type(data)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (str(type(scatter)) == "<class 'bool'>"), "Not a boolean value"
    assert (str(type(single_scatter)) == "<class 'bool'>"), "Not a boolean value"
    assert (str(type(annualised)) == "<class 'bool'>"), "Not a boolean value"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (frequency in ['M', 'Q', 'W', 'Y', '6M', 'D']), "Should be one of the values of 'M', 'Q', 'W', 'Y', '6M', 'D'"
    assert (str(type(price_col)) == "<class 'str'>"), "Not a string"
    assert (str(type(date_col)) == "<class 'str'>"), "Not a string"

    try:
        data[date_col] = pd.to_datetime(data[date_col])
        data.set_index(date_col, inplace=True)
        trading_days = - ({'M': 22, 'W': 5, 'Q': 66, 'D': 1, '6M': 126, 'Y': 252}[frequency])

        # Time Mapper
        mapper_time = {'D': 252, 'M': 12, 'W': 52, 'Q': 4, 'Y': 1, '6M': 2}

        periodic = data.resample(frequency).last()
        ret, vol = [], []
        prev = periodic.index[0]

        # Annualised
        for dates in periodic.index.unique()[1:]:
            if annualised:

                vol_cal = np.std(data.loc[:dates, price_col][trading_days:].pct_change().dropna().values) * np.sqrt(mapper_time[frequency])
                vol.append(vol_cal)
                rets = ((periodic.loc[dates][price_col] / periodic.loc[prev][price_col]) - 1) * mapper_time[frequency]
                ret.append(rets)
                prev = dates
            else:

                vol_cal = np.std(data.loc[:dates, price_col][trading_days:].pct_change().dropna().values)
                vol.append(vol_cal)
                rets = ((periodic.loc[dates][price_col] / periodic.loc[prev][price_col]) - 1)
                ret.append(rets)
                prev = dates
        
        # percentage format
        ret = pd.Series(ret).dropna().apply(lambda x: x * 100).values.tolist()
        vol = pd.Series(vol).dropna().apply(lambda x: x * 100).values.tolist()
        
        if not scatter:

            hist_data = [ret]

            group_labels = ['Return']
            colors = colors

            fig = ff.create_distplot(hist_data, group_labels, colors=colors,
                                    bin_size=.2, show_rug=False)

            # Return Distribution
            fig.update_layout(title_text='Return Distribution', xaxis_title="Return (%)", yaxis_title="Probability Density")

            group_labels = ['Volatility']
            hist_data = [vol]

            fig1 = ff.create_distplot(hist_data, group_labels, colors=colors,
                                    bin_size=.2, show_rug=False)

            # Volatility Distribution
            fig1.update_layout(title_text='Volatility Distribution', xaxis_title="Volatility (%)", yaxis_title="Probability Density", font=dict(family = "Courier New, monospace",
                                        size = 12,
                                        color="RebeccaPurple"
                                        ), width = graph_width, height = graph_height)
        
            return fig, fig1

        else:

            if single_scatter:
                # Single Volatility
                fig2 = go.Figure()

                fig2.add_trace(go.Scatter(
                    x = vol,
                    y = [0]*len(vol),
                    mode = 'markers',
                    marker = dict(size=7, color = (
                            pd.Series(ret) > 0
                        ).astype('int'),
                    colorscale = ([[0, 'red'], [1, 'green']])),
                    name = 'Volatility'
                ))

                fig2.update_layout(
                    title = "Volatility Scatter Plot",
                    xaxis_title = "Volatility (%)",
                    yaxis_visible = False,
                    font=dict(family = "Courier New, monospace",
                                              size = 12,
                                              color="RebeccaPurple"
                                            ), width = graph_width, height = graph_height
                )

                # Single Return
                fig3 = go.Figure()

                fig3.add_trace(go.Scatter(
                    x = ret,
                    y = [0]*len(ret),
                    mode = 'markers',
                    marker = dict(size=7, color = (
                            pd.Series(ret) > 0
                        ).astype('int'),
                    colorscale = ([[0, 'red'], [1, 'green']])),
                    name = 'Return'
                ))

                fig3.update_layout(
                    title = "Return Scatter Plot",
                    xaxis_title = "Return (%)",
                    yaxis_visible = False,
                    font=dict(family = "Courier New, monospace",
                                              size = 12,
                                              color="RebeccaPurple"
                                            ), width = graph_width, height = graph_height
                )



            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x = vol,
                y = ret,
                mode = 'markers',
                name = 'Return vs Volatility',
                marker = dict(
                    size = 7,
                    color = (
                            pd.Series(ret) > 0
                        ).astype('int'),
                    colorscale=[[0, 'red'], [1, 'green']]
                    )
                )
            )

            fig.update_layout(
                title = "Return-Volatility",
                xaxis_title = "Volatility (%)",
                yaxis_title = "Return (%)",
                font=dict(family = "Courier New, monospace",
                                          size = 12,
                                          color="RebeccaPurple"
                                        ), width = graph_width, height = graph_height
            )

            if single_scatter:

                return fig, fig2, fig3

            return fig

    except Exception as e:
        print(e)





def rv_time_distribution_scatter_plots(data:pd.DataFrame, colors:list=['#A56CC1'], graph_width:int=800, graph_height:int=400, frequency:str='M',
                                                                                         price_col:str='Adj Close', date_col:str='Date', annualised:bool=False) -> go.Figure:
    '''
    Plots the time distribution plots for return and volatilities.

    Parameters
    ----------
    data : pd.DataFrame, default - None
        A dataframe containing the prices with a Date column
    colors: list, default - ['#A56CC1']
        colors for the plots
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    frequency : str, default - 'M'
        frequncy over which Return and Volatility plots to be plotted
    price_col : str, default - 'Adj Close'
        Price column of the dataframe
    annualised : bool, default - False
        Annualise the returns and the volatility
    date_col : str, default - 'Date
        Name of the date column

    Return
    ------
    plotly.graph_objects (tuples): Plotly scatter and displot objects

    2 Figure objects (tuple)
    '''
    assert (str(type(data)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (frequency in ['D', 'M', 'Q', 'W', 'Y', '6M']), "Should be one of the values of 'M', 'Q', 'W', 'Y', '6M', 'D'"
    assert (str(type(price_col)) == "<class 'str'>"), "Not a string"
    assert (str(type(date_col)) == "<class 'str'>"), "Not a string"
    assert (str(type(annualised)) == "<class 'bool'>"), "Not a boolean value"

    try:
        data[date_col] = pd.to_datetime(data[date_col])
        data.set_index(date_col, inplace=True)
        trading_days = - ({'M': 22, 'W': 5, 'Q': 66, 'D': 1, '6M': 126, 'Y': 252}[frequency])

        # Time Mapper
        mapper_time = {'D': 252, 'M': 12, 'W': 52, 'Q': 4, 'Y': 1, '6M': 2}

        periodic = data.resample(frequency).last()
        ret, vol = [], []
        prev = periodic.index[0]

        # Annualised
        for dates in periodic.index.unique()[1:]:
            if annualised:

                vol_cal = np.std(data.loc[:dates, price_col][trading_days:].pct_change().dropna().values) * np.sqrt(mapper_time[frequency])
                vol.append(vol_cal)
                rets = ((periodic.loc[dates][price_col] / periodic.loc[prev][price_col]) - 1) * mapper_time[frequency]
                ret.append(rets)
                prev = dates
            else:

                vol_cal = np.std(data.loc[:dates, price_col][trading_days:].pct_change().dropna().values)
                vol.append(vol_cal)
                rets = ((periodic.loc[dates][price_col] / periodic.loc[prev][price_col]) - 1)
                ret.append(rets)
                prev = dates

        # percentage format
        ret = pd.Series(ret).dropna().apply(lambda x: x * 100).values.tolist()
        vol = pd.Series(vol).dropna().apply(lambda x: x * 100).values.tolist()



        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = periodic.index,
            y = ret,
            mode = 'markers',
            name = 'Return vs Volatility',
            marker = dict(
                size = 7,
                color = (
                        pd.Series(ret) > 0
                    ).astype('int'),
                colorscale=[[0, 'red'], [1, 'green']]
                )
            )
        )

        fig.update_layout(
            title = "Time Distribution of Returns",
            xaxis_title = "Time",
            yaxis_title = "Return (%)",
            font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color="RebeccaPurple"
                                    ), width = graph_width, height = graph_height
        )



        fig1 = go.Figure()

        fig1.add_trace(go.Scatter(
            x = periodic.index,
            y = vol,
            mode = 'markers',
            name = 'Return vs Volatility',
            marker = dict(
                size = 7,
                color = (
                        pd.Series(ret) > 0
                    ).astype('int'),
                colorscale=[[0, 'red'], [1, 'green']]
                )
            )
        )

        fig1.update_layout(
            title = "Time Distribution of Volatility",
            xaxis_title = "Time",
            yaxis_title = "Volatility (%)",
            font=dict(family = "Courier New, monospace",
                                      size = 12,
                                      color="RebeccaPurple"
                                    ), width = graph_width, height = graph_height
        )


        return fig, fig1

    except Exception as e:
        print(e)





def candlestick_plot(
        df : pd.DataFrame,
        date_column_name : str = 'Date',
        chart_title : str = 'Candlestick Chart',
        xaxis_title : str = 'Date',
        yaxis_title : str = 'Prices',
        xaxis_rangeslider_visible : bool = False,
        graph_width:int=800,
        graph_height:int=400,
        yaxis_side : str = 'right',
        xshift_value : int = 25,
        yshift_value : int = 0
    ) -> go.Figure:
    '''
    Plots the Candlestick chart of stock data.

    Parameters
    ----------
    df : pd.DataFrame, default - None
        A dataframe containing the prices with a Date column (must have Open, High, Low, Close columns)
    date_column_name: str, default - 'Date'
        Date column of the dataset
    graph_width : int, default - 1600
        Width of the graph object
    graph_height : int, default - 600
        Height of the graph object
    yaxis_title: str, default - 'Prices'
        Title of the yaxis
    xaxis_title : str, default - 'Date'
        Title of the x-axis
    chart_title : str, default - 'Candlestick Chart'
        Name of the plot
    xaxis_rangeslider_visible : bool, default - False
        x-axis slider
    yaxis_side : str, default - 'right'
        Position of the y-axis
    xhift_value : int, default - 25
        Annotation to be shifted on the x-axis
    yshift_value : int, default - 0
        Annotation to be shifted on the yaxis

    Return
    ------
    plotly.graph_objects : Plotly object
    '''
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (str(type(date_column_name)) == "<class 'str'>"), "Not a string"
    assert (str(type(chart_title)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis_title)) == "<class 'str'>"), "Not a string"
    assert (str(type(yaxis_title)) == "<class 'str'>"), "Not a string"
    assert (str(type(yaxis_side)) == "<class 'str'>"), "Not a string"
    assert (str(type(xaxis_rangeslider_visible)) == "<class 'bool'>"), "Not a boolean value"
    assert (str(type(graph_width)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(graph_height)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(xshift_value)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(yshift_value)) == "<class 'int'>"), "Not an integer value"

    try:
        df[date_column_name] = pd.to_datetime(df[date_column_name])
        df.set_index(date_column_name, inplace=True)

        # Create Chart Object

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(

            go.Candlestick(

                x=df.index,

                open=df['Open'],

                high=df['High'],

                low=df['Low'],

                close=df['Close']

            ),

            secondary_y=True

        )

        fig.update_xaxes(title_text=xaxis_title, range=[df.index[0], df.index[-1]])

        fig.update_yaxes(title_text=yaxis_title, secondary_y=True)

        fig.update_layout(title=chart_title)



        fig.update_layout(

            width=graph_width,

            height=graph_height,

            xaxis_rangeslider_visible=xaxis_rangeslider_visible,

            yaxis=dict(side=yaxis_side)

        )



        # Determine text-annotation and back-ground color

        if df.Open[-1] > df.Close[-1] :

            y=df.Open[-1]

            bgcolor='rgb(3,75,3)' # deep-green



        if df.Open[-1] < df.Close[-1] :

            y=df.Close[-1]

            bgcolor='rgb(255,0,0)' # red



        # Show the annotation

        fig.add_annotation(

            x=df.index[-1],

            y=y,

            text=str(round(y)),

            showarrow=False,

            xshift=xshift_value,

            bgcolor=bgcolor,

            font_color='rgb(255,255,255)'

        )

        return fig

    except Exception as e:
        print(e)





def weight_graphs(weights_file:str, ticker:str, threshold:float, path:str='', price_col:str='Adj Close', frequency:str='M') -> go.Figure:
    '''
    Plots the weight charts and the buy/sell signals of individual assets.

    Parameters
    ----------
    weights_file:str, default-None
        A string containing the path of the weights of the asset (file to be .xlsx or a csv with sheet name as "Weights")
    ticker:str, default-None
        Name of the ticker - e.g (AAPL)
    threshold:float, default - None
        A value below which no bar is plotted
    path:str, default - ''
        A location where the raw prices of the asset is located. Leave it blank if inside the same folder where the function is being called.
        Eg: if asset prices is in a path such as 'Data/....csv' just give path='Data/'
    price_col:str, default-Adj Close
        Name of the price column
    frequency:str, deafult - 'M'
        Frequency of data supplied for weights

    Return
    ------
    go.Figure object: Weight and Buy/Sell Plots
    '''
    try:

        def get_options(df_weights:pd.DataFrame, ticker:str, threshold:float) -> np.array:
            df_weights = df_weights.apply(lambda x:round(x, 6))
            df_weights['difference'] = df_weights[ticker]-df_weights[ticker].shift(1)
            df_weights['difference_2'] = df_weights['difference'].where(np.absolute(df_weights['difference']) > threshold, other=0)
            options = np.sign(df_weights['difference_2'])
            df_weights.drop(['difference'], axis=1, inplace=True)

            if df_weights[ticker].iloc[0] > 0:
                options[0] = 1.0

            return options


        def df_function(weights_file:str, ticker:str, threshold:float, path:str):
            # Extracting the Ticker Weights
            try:
                df_weights = pd.read_csv(weights_file, index_col=0)
            except:
                df_weights = pd.read_excel(weights_file, index_col=0, sheet_name="Weights")

            df_weights.dropna(inplace=True)
            df_weights.index = pd.to_datetime(df_weights.index)
            df_ticker_weights = df_weights[[ticker]]
            df_ticker_weights.index = pd.Series(df_ticker_weights.index).apply(lambda x: x.strftime("%Y-%m-%d"))

            # Extracting the Adj Close for ticker
            ticker_csv_path = os.path.join(path,ticker+'.csv')
            df_price = pd.read_csv(ticker_csv_path, index_col=0)
            df_price.dropna(inplace=True)
            df_price.index = pd.to_datetime(df_price.index)
            df_ticker_price = df_price[[price_col]]
            df_ticker_price = df_ticker_price.resample(frequency).last()
            df_ticker_price.index = pd.Series(df_ticker_price.index).apply(lambda x: x.strftime("%Y-%m-%d"))
            df_ticker_price.index.name = 'date'

            # Merging Weights and Prices
            df = df_ticker_price.merge(df_ticker_weights, on='date')

            # Adding Option Column
            df['Option']=get_options(df_weights=df_ticker_weights, ticker=ticker, threshold=threshold)
            df.fillna(0, inplace=True)

            df[ticker] = df[ticker].where(df[ticker] > threshold, other=0)
            df[ticker] = df[ticker].apply(lambda x: x * 100)

            return df


        def get_bar_text(df:pd.DataFrame,ticker:str):
            text = []
            for i in df[ticker]:
                if round(i,2) == 0.00:
                    i = ''
                    text.append(i)
                else:
                    text.append(round(i*100, 2))
            text_df = pd.DataFrame(data={'text':text})
            text_df.replace(np.nan, '')

            return text_df.text

        # Extracting Weights and Prices
        df = df_function(weights_file, ticker=ticker, threshold=threshold, path=path)

        # Making figure object
        fig = make_subplots(
                        rows=2,
                        cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.02,
                        row_heights=[0.7,0.3],
                        specs=[
                                [{"secondary_y": True}],
                                [{"secondary_y": True}]
                            ]
                    )
        # Buy - markers
        fig.add_trace(
            go.Scatter(
                x=df[df['Option'] == 1].index,
                y=df[df['Option'] == 1][price_col],
                mode = 'markers',
                marker = dict(size = 10, symbol = 'triangle-up',color='green'),
                name='Buy'        ),
            row=1,
            col=1    )

        # Sell - markers
        fig.add_trace(
            go.Scatter(
                x=df[df['Option'] == -1].index,
                y=df[df['Option'] == -1][price_col],
                mode = 'markers',
                marker = dict(size = 10, symbol = 'triangle-down',color = 'red'),
                name='Sell'        ),
            row=1,
            col=1    )

        # Original Line (Line to be shown in plot)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[price_col],
                mode='lines',
                name=f'{price_col}',
                marker = dict(color = 'orange')
            ),
            secondary_y=True,
            row=1,
            col=1    ).update_xaxes(
            range=[df.index[0],df.index[-1]]
        ).add_annotation(
                x=df.index[-1],
                y=df[price_col][-1],
                text=str(round(df[price_col][-1])),
                showarrow=False,
                xshift=15,
                bgcolor='rgb(255,0,0)',
                font_color='rgb(255,255,255)'        )

        # Pseudo Bar (Bar not to be shown in plot)
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[ticker],
                showlegend=False,
                marker_color='white'        ),
            row=2,
            col=1    )

        df[ticker] = df[ticker].replace({0:np.nan})

        # Original Bar (Bar to be shown in plot)
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[ticker],
                name='Weights',
                text=get_bar_text(df=df,ticker=ticker),
                textposition='outside',
                textfont_size=10,
                # width=0.1
            ),
            secondary_y=True,
            row=2,
            col=1    )

        # fig['layout']['yaxis']['title']='Price'
        fig.update_xaxes(row=1, col=1, tickcolor='white')
        fig.update_yaxes(title_text="Price", secondary_y=False, row=1, col=1, range=[min(df[price_col])-5, max(df[price_col])+5])
        fig.update_yaxes(title_text="Price", secondary_y=True, row=1, col=1, range=[min(df[price_col])-5, max(df[price_col])+5])
        fig.update_yaxes(title_text="Weights (in %)", secondary_y=False, row=2, col=1, range=[0,100+0.1])
        fig.update_yaxes(title_text="Weights (in %)", secondary_y=True, row=2, col=1, range=[0,100+0.1])
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_layout(
            width=1500,
            height=1000,
            title=ticker+' (Weight Chart)' )

        return fig

    except Exception as e:
        print(e)
