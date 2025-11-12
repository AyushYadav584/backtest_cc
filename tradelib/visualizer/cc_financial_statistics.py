import numpy as np
import pandas as pd
import pymannkendall as mk
import statsmodels.api as sm
import matplotlib.pyplot as plt
from scipy.stats import kurtosis


plt.rcParams['axes.facecolor'] = 'lightblue'


def CAGR(df:pd.DataFrame, t:float, col_name:str="invested") -> float:
    '''
    Calculates the Cumulative Annual Growth Return

    Parameters
    ----------
    df : pd.DataFrame, default - None
        Expects a dataframe which has the invested amounts
    t : str, default - float
        Time period in years
    col_name : str, default - "invested"
        Name of the columns

    Return
    ------
    float : A float value (CAGR)
    '''
    assert (str(type(df)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (str(type(t)) == "<class 'numpy.float64'>"), "Not a float values"
    assert (str(type(col_name)) == "<class 'str'>"), "Not a string"

    try:
        return (((df[col_name].iloc[-1] / df[col_name].iloc[0]) ** (1/t)) - 1) * 100
    except Exception as e:
        print(e)





def information_ratio(returns:pd.Series, benchmark_returns:pd.Series, period:int) -> float:
    '''
    Calculates the Information Ratio

    Parameters
    ----------
    returns : pd.Series, default - None
        Expects a series containing the return series
    benchmark_returns : pd.Series, default - None
        Excepts a series containing the market returns
    period : int, default - None
        The period (monthly or daily etc.)

    Return
    ------
    float : Information Ratio
    '''
    assert (str(type(returns)) == "<class 'pandas.core.series.Series'>"), "Not a Series"
    assert (str(type(period)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(benchmark_returns)) == "<class 'pandas.core.series.Series'>"), "Not a Series"

    try:
        return_difference = returns - benchmark_returns
        volatility = return_difference.std() * np.sqrt(period)
        information_ratio = return_difference.mean() / volatility

        return information_ratio
    except Exception as e:
        print(e)






def financial_summary(df_rets:pd.DataFrame, benchmark_rets:pd.DataFrame=None, frequency:str='D', asset_class:str='None', risk_free_rate:float=0, col_name_cagr:str="invested", title:str='', date_col:str='date') -> pd.DataFrame:
    '''
    Must supply a dataframe with date, retruns as columns
    Note - Don't supply daily returns as % . Keep the date column at the beginning.

    Example:
    date           returns    turnover
    2018-02-09     0.25       0.25
    2018-02-10     0.29       0.00

    Parameters
    ----------
    frequency : Daily (D), Monthly(M) or Weekly(W), default - 'D'.
            Describes the frequency of data provided.
    df_rets : pd.DataFrame, default - None
            All Return Information, Turnover etc.
    asset_class : str, default - ''
            Name of the asset class
    risk_free_rate : float, default 0
            risk free rate of return
    col_name_cagr : str, default - "invested"
            The name of the column for CAGR Calculation (column should be present in df_rets)
    benchmark_rets : pd.DataFrame, default - None
            Market returns for the given period
    date_col : str, default - 'date'
            Name of the date column

    Return
    ------
    pd.DataFrame : Complete Summary of any strategy
    '''
    assert (str(type(df_rets)) == "<class 'pandas.core.frame.DataFrame'>"), "Not a dataframe"
    assert (str(type(col_name_cagr)) == "<class 'str'>"), "Not a string"
    assert (str(type(asset_class)) == "<class 'str'>"), "Not a string"
    assert (frequency in ['D', 'M', 'W', 'Q', 'Y', '6M']), "Should be one of the values of 'D', 'M', 'W', 'Q', 'Y', '6M'"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"

    try:
        mapper = {'D': 'Day', 'M': 'Month', 'W': 'Week', 'Q': 'Quarter', 'Y': 'Year', '6M': 'Half Yearly'}
        mapper_time = {'D': 252, 'M': 12, 'W': 52, 'Q': 4, 'Y': 1, '6M': 2} # period multiplier
        calender_time = {'D': 1, 'M': 30, 'W': 7, 'Q': 90, 'Y': 365, '6M': 182} # in days

        # If turnover is provided we skip, else we take it as 0
        try:
            turnover_col_check = df_rets['turnover']
        except:
            df_rets['turnover'] = 0
            
        # if return column is missing we calculate it
        try:
            ret_col_check = df_rets['returns']
        except:
            df_rets['returns'] = df_rets[col_name_cagr].pct_change().fillna(0)
        
        df_rets['c_ret'] = (1 + df_rets['returns']).cumprod() - 1
        periods = np.around((pd.to_datetime(df_rets.loc[df_rets.iloc[len(df_rets)-1].name, date_col]) - pd.to_datetime(df_rets.loc[df_rets.iloc[0].name, date_col])).days / calender_time[frequency], 2)
        volatility = np.std(df_rets['returns']) * np.sqrt(mapper_time[frequency])
        returns = ((df_rets['c_ret'].values[-1])/(periods)) * mapper_time[frequency]
        sharpe = (returns - risk_free_rate) / volatility
        cagr = CAGR(df_rets, t=np.around((periods/mapper_time[frequency]), 2), col_name=col_name_cagr)
        
        # Default benchmark is None if not provided.
        if benchmark_rets != None:
            info_ratio = information_ratio(df_rets['returns'], benchmark_rets['returns'], mapper_time[frequency])
        elif benchmark_rets == None:
            info_ratio = 0
        
        turnover = df_rets['turnover'].mean()
        market_class = asset_class
        
        # Calculate Max Drawdown
        inv = df_rets[col_name_cagr]
        z = pd.Series(index=range(len(inv)))
        z.iloc[0] = inv.iloc[0]

        for i in range(1, len(inv)):
            z.iloc[i] = max(inv[i], z[i-1])

        maxdrwdn = (inv - z).min()/z.iloc[0]

        sortino = returns / (np.std(df_rets[df_rets['returns'] < 0]['returns']) * np.sqrt(mapper_time[frequency]))
        kurtosiss = kurtosis(df_rets['returns'], fisher=False)
        
        # Data Arrangement
        meta_data = pd.DataFrame(
            data = [
                df_rets.loc[df_rets.iloc[0].name, date_col],
                df_rets.loc[df_rets.iloc[len(df_rets)-1].name, date_col],
                periods,
                asset_class
            ],

            index = ['Start Date', 'End Date', f'Time Period (in {mapper[frequency]})', 'Strategy'], columns=['Meta Data']
        )
        
        summary_data = pd.DataFrame(
            data = [
                f'{np.around(returns*100, 2)}%',
                f'{np.around(volatility*100, 2)}%',
                f'{np.around(cagr, 2)}%',
                f'{np.around(maxdrwdn*100, 2)}%'
            ],

            index = ['Annual Return', 'Annual Volatility', f'CAGR', 'Max. Drawdown'], columns=['Summary']
        )
        
        other_stats = pd.DataFrame(
            data = [
                f'{np.around(sharpe, 2)}',
                f'{np.around(kurtosiss, 2)}',
                f'{np.around(info_ratio, 2)}',
                f'{np.around(turnover*100, 2)}%'
            ],

            index = ['Sharpe Ratio', 'Kurtosis', f'Information Ratio', 'Turnover'], columns=['Statistics']
        )
        
        meta_data = meta_data.reset_index()
        summary_data = summary_data.reset_index()
        other_stats = other_stats.reset_index()

        meta_data.columns = ['', 'Meta Data']
        other_stats.columns = ['', 'Statistics']
        summary_data.columns = ['', 'Summary']

        df = pd.concat([meta_data, summary_data, other_stats], axis=1)
        df = df.style.set_caption(f'<b>{title}</b>')
        
        return df

    except Exception as e:
        print(e)





def drawdown(return_series: pd.Series) -> pd.DataFrame:
    """Takes a time series of asset returns.
       returns a DataFrame with columns for
       the wealth index,
       the previous peaks, and
       the percentage drawdown

       Parameter
       --------
       returns_series : pd.Series, default - None

       Return
       ------
       pd.DataFrame : Drawdown
    """
    assert (str(type(return_series)) == "<class 'pandas.core.series.Series'>"), "Not a Series"

    try:
        return_series = return_series.apply(lambda x: np.log(1+x))
        wealth_index = 1000 * (1+return_series).cumprod()
        previous_peaks = wealth_index.cummax()
        drawdowns = (wealth_index - previous_peaks)/previous_peaks
        return pd.DataFrame({"Wealth": wealth_index,
                            "Previous Peak": previous_peaks,
                            "Drawdown": drawdowns})

    except Exception as e:
        print(e)





def detailed_summary(excelSheet:str, sheets:list, col_name="invested", date_col="date", period=12, prev_yr='2017', title:str='') -> pd.DataFrame:
    '''
    Provides an year-wise summary of portfolio, baseline and the individual securities.

    Parameters
    ----------
    excelSheet: str, default - ''
        Name of the ExcelSheet with the details.
    sheets: list
        A list with sheet Names - ["Portfolio", "Baseline", "Prices"]
    period: int, default - 12
        Data details, whether monthly, daily or quarterly data. Default is 12 i.e. monthly, change it to 4 if quarterly or 252 if daily.
    prev_yr: str, default - '2017'
        Last year preceeding the first date. For Ex: if first date is "2018-03-01", prev_yr = 2017 (Since the first date entry is on 2018)
    col_name: str, default - 'invested'
        Name of the column on which statistics are calculated for the Portfolio Sheet.
    date_col: str, default - 'date'
        Name of the datetime column

    Note: "Provide the entire path to the excelsheet if it is inside a folder."
          "All sheets must have a column named "date" for dates."
          "Adj Close" - In Baseline Sheet.(In Baseline sheet)"

    Return
    ------
    pd.DataFrame: A detailed summary (yearwise)
    '''
    assert (str(type(period)) == "<class 'int'>"), "Not an integer value"
    assert (str(type(prev_yr)) == "<class 'str'>"), "Not a string"
    assert (str(type(excelSheet)) == "<class 'str'>"), "Not a string"
    assert (str(type(col_name)) == "<class 'str'>"), "Not a string"
    assert (str(type(date_col)) == "<class 'str'>"), "Not a string"
    assert (str(type(sheets)) == "<class 'list'>"), "Not a list object"
    assert (str(type(title)) == "<class 'str'>"), "Not a string"


    try:
        def individual_etfs(df):
            Y = list(df.columns[1:len(df.columns)-1])
            dfx = pd.DataFrame()

            # for all etfs in the portfolio
            for etf in Y:
                tf = pd.DataFrame()
                prev_date = prev_yr
                for date in df['year'].unique():
                    y = df[(df_port.date>=prev_date+'-12-31') & (df_port.date<=date+'-12-31')].loc[:, [etf]]
                    y.reset_index(drop=True, inplace=True)

                    # Date update
                    prev_date = date

                    # Log Returns
                    lgrets = np.diff(np.log(y[etf]))
                    lgrets = np.insert(lgrets, 0, np.nan)
                    y['log_returns'] = lgrets
                    y['log_returns'].fillna(0, inplace=True)

                    # Volatility
                    vol = np.std(y.loc[1:, 'log_returns'], ddof=1) * np.sqrt(period)

                    # Annual Return
                    ret = (y.loc[len(y)-1, etf] / y.loc[0, etf]) - 1

                    # Max Drawdown
                    inv = y[etf]
                    z = pd.Series(index=range(len(inv)))
                    z.iloc[0] = inv.iloc[0]

                    for i in range(1, len(inv)):
                        z.iloc[i] = max(inv[i], z[i-1])

                    maxdrwdn = (inv - z).min()/z[0]

                    # Sharpe ratio
                    sharpe = ret / vol

                    new_df = pd.DataFrame(data=[f'{np.around(ret*100, 2)}%', f'{np.around(vol*100, 2)}%', f'{np.around(sharpe, 2)}', f'{np.around(maxdrwdn*100, 2)}%'], columns=[date], index=['Return', 'Volatility', 'Sharpe Ratio', 'Max Drawdown'])
                    tf = pd.concat([tf, new_df], axis=1)

                tf.columns.name = etf
                tf['Security Name'] = etf
                dfx = pd.concat([dfx, tf])

            return dfx


        # Read the entire excel sheet
        portfolio_returns, baseline_returns = [], []

        result = pd.ExcelFile(excelSheet)
        df = pd.DataFrame()
        prev_date = prev_yr

        for ticker in sheets:
            df_port = pd.read_excel(result, ticker)
            df_port['date'] = df_port[date_col]
            df_port['year'] = df_port['date'].apply(lambda x: x[:4])
            tf = pd.DataFrame()

            if ticker == 'Portfolio':
                for date in df_port['year'].unique():
                    y = df_port[(df_port.date>=prev_date+'-12-31') & (df_port.date<=date+'-12-31')]
                    y.reset_index(drop=True, inplace=True)

                    # Date update
                    prev_date = date

                    # Log Returns
                    lgrets = np.diff(np.log(y[col_name]))
                    lgrets = np.insert(lgrets, 0, np.nan)
                    y['log_returns'] = lgrets
                    y['log_returns'].fillna(0, inplace=True)

                    # Volatility
                    vol = np.std(y.loc[1:, 'log_returns'], ddof=1) * np.sqrt(period)

                    # Annual Return
                    ret = (y.loc[len(y)-1, col_name] / y.loc[0, col_name]) - 1

                    # For alpha calculation
                    portfolio_returns.append(ret)

                    # Max Drawdown
                    inv = y[col_name]
                    z = pd.Series(index=range(len(inv)))
                    z.iloc[0] = inv.iloc[0]

                    for i in range(1, len(inv)):
                        z.iloc[i] = max(inv[i], z[i-1])

                    maxdrwdn = (inv - z).min()/z[0]

                    # Sharpe ratio
                    sharpe = ret / vol

                    new_df = pd.DataFrame(data=[f'{np.around(ret*100, 2)}%', f'{np.around(vol*100, 2)}%', f'{np.around(sharpe, 2)}', f'{np.around(maxdrwdn*100, 2)}%'], columns=[date], index=['Return', 'Volatility', 'Sharpe Ratio', 'Max Drawdown'])
                    tf = pd.concat([tf, new_df], axis=1)

                tf.columns.name = ticker
                tf['Security Name'] = ticker
                df = pd.concat([df, tf])

            elif ticker == 'Baseline':
                prev_date = prev_yr

                for date in df_port['year'].unique():
                    y = df_port[(df_port.date>=prev_date+'-12-31') & (df_port.date<=date+'-12-31')]
                    y.reset_index(drop=True, inplace=True)

                    # Date update
                    prev_date = date

                    # Log Returns
                    lgrets = np.diff(np.log(y['Adj Close']))
                    lgrets = np.insert(lgrets, 0, np.nan)
                    y['log_returns'] = lgrets
                    y['log_returns'].fillna(0, inplace=True)

                    # Volatility
                    vol = np.std(y.loc[1:, 'log_returns'], ddof=1) * np.sqrt(period)

                    # Annual Return
                    ret = (y.loc[len(y)-1, 'Adj Close'] / y.loc[0, 'Adj Close']) - 1

                    # For alpha calculation
                    baseline_returns.append(ret)

                    # Max Drawdown
                    inv = y['Adj Close']
                    z = pd.Series(index=range(len(inv)))
                    z.iloc[0] = inv.iloc[0]

                    for i in range(1, len(inv)):
                        z.iloc[i] = max(inv[i], z[i-1])

                    maxdrwdn = (inv - z).min()/z[0]

                    # Sharpe ratio
                    sharpe = ret / vol

                    new_df = pd.DataFrame(data=[f'{np.around(ret*100, 2)}%', f'{np.around(vol*100, 2)}%', f'{np.around(sharpe, 2)}', f'{np.around(maxdrwdn*100, 2)}%'], columns=[date], index=['Return', 'Volatility', 'Sharpe Ratio', 'Max Drawdown'])
                    tf = pd.concat([tf, new_df], axis=1)

                tf.columns.name = ticker
                tf['Security Name'] = ticker
                df = pd.concat([df, tf])

            else:
                tf = individual_etfs(df_port)
                df = pd.concat([df, tf])

        # Set Colors
        def _color_negative_red(val):
            try:
                color = 'red' if float(val.split('%')[-2]) < 0 else 'green'
                return 'color: %s' % color
            except:
                color = 'red' if float(val) < 0 else 'green'
                return 'color: %s' % color


        if len(sheets) > 1 or sheets[0] == 'Prices':
            _return = df.loc['Return'].reset_index().set_index(['index', 'Security Name'])
            _volatility = df.loc['Volatility'].reset_index().set_index(['index', 'Security Name'])
            _sharpe_ratio = df.loc['Sharpe Ratio'].reset_index().set_index(['index', 'Security Name'])
            _max_drawdown = df.loc['Max Drawdown'].reset_index().set_index(['index', 'Security Name'])

            if (len(portfolio_returns) == len(baseline_returns)) and (len(portfolio_returns) > 0):
                alphas = pd.Series(np.array(portfolio_returns) - np.array(baseline_returns)).apply(lambda x: f'{np.around(x * 100, 2)}%')
                _return.loc[('Return', 'Alpha'), :] = alphas.values

            final_df = pd.concat([_return, _volatility, _sharpe_ratio, _max_drawdown], axis = 0)
            final_df.index.names = ['Metric', 'Security Name']

        elif len(sheets) == 1 and (sheets[0] != 'Prices'):
            final_df = df.copy()
            final_df.drop('Security Name', axis=1, inplace=True)

        final_df = final_df.style.applymap(_color_negative_red).set_caption(f'<b>{title}</b>')

        return final_df

    except Exception as e:
        print(e)
