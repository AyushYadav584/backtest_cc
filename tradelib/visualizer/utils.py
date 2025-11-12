import pandas as pd
import numpy as np
import sys
import re
# from vasco.exception import VascoException
# from vasco.logger import logging
from pandas.errors import ParserError
from constant import CC_STATISTICS_CATEGORY_NUMBER

def get_feature_type_list(data: pd.DataFrame) -> tuple: # get_feature_type_List
    """
    This function helps us to separates feature list in between Categorical, Numerical, Datetime and String.

    Parameters:
    -----------
    data : pandas.DataFrame
        Name of the dataset

    Returns:
    --------
        tuple :
            Categorical : list of categorical feature
            Numerical : list of numerical feature
            Datetime : list of datetime feature
            String : list of string feature
            Bool : list of boolean feature
    """
    try:
        df = data.copy()
        
        # Change the datatype of the date column
        df = dt_inplace(df)
        
        # Creating column list with all the columns element
        columns = df.columns.to_list()

        # Creating a list of categorical variable
        Categorical = df.dtypes[df.dtypes == object].index.to_list()

        # Creating a list of boolean variable
        Bool = df.dtypes[df.dtypes == bool].index.to_list()
        
        # Creating a list of Datetime variable
        Datetime = df.dtypes[df.dtypes == 'datetime64[ns]'].index.to_list()

        Cat_boll_date_column = Categorical + Bool + Datetime
        rest_columns = list(set(columns) - set(Cat_boll_date_column))

        extra_categorical = []
        for i in rest_columns:
            if df[i].nunique() <= CC_STATISTICS_CATEGORY_NUMBER:
                if df[i].dtypes != int:
                    if not any([not j.is_integer() for j in df[i].dropna().unique()]):
                        extra_categorical.append(i)   
                else:
                    extra_categorical.append(i)

        Categorical.extend(extra_categorical)

        # Creating a list of String variable 
        rows = df.shape[0]
        Threshold = int(rows * 0.1)
        String=[]
        for i in Categorical:
            df[i] = df[i].astype(str)
            # Creating flag variable of link and email
            islink = not pd.Series([not is_link(j) for j in df[i].dropna().unique()]).value_counts().sort_values().index[-1]
            isemail = not pd.Series([not is_email(j) for j in df[i].dropna().unique()]).value_counts().sort_values().index[-1]
            
            if rows - df[i].nunique() <= Threshold or isemail or islink:
                String.append(i)
            else:
                pass

        Categorical = list(set(Categorical) - set(String))

        # Creating a list of Numerical variable
        non_numerical = Categorical + Bool + String + Datetime
        Numerical = list(set(columns) - set(non_numerical))

        return Categorical, Numerical, Datetime, String, Bool

    except Exception as e:
        raise(e)

def dt_inplace(df: pd.DataFrame) -> pd.DataFrame:
    """Automatically detect and convert (in place!) each
    dataframe column of datatype 'object' to a datetime just
    when ALL of its non-NaN values can be successfully parsed
    by pd.to_datetime().  Also returns a ref. to df for
    convenient use in an expression.
    
    Parameters:
    -----------
        df : pandas.DataFrame
            Name of the dataset

    Returns:
    --------
        pandas.DataFrame : 
            Original dataset with transformed datetime column
    """
    try:
        for c in df.columns[df.dtypes=='object']: #don't cnvt num
            try:
                df[c]=pd.to_datetime(df[c])
            except (ParserError,ValueError): #Can't cnvrt some
                pass # ...so leave whole column as-is unconverted

        return df
    except Exception as e:
        print(e)


def is_link(string: str) -> bool:
    """
    This function help us to identify a link

    Parameters:
    -----------
        string : str
            string

    Returns:
    --------
        bool : 
            True, if the input string is a link
            False, if the input string is not a link
    """

    # Define the regular expression pattern to match links
    pattern1 = r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    pattern2 = r'ftp?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    pattern3 = r'www+\.[a-zA-Z]{2,}'

    # Use the search function to check if the pattern matches the input string
    if re.search(pattern1, string) or re.search(pattern2, string) or re.search(pattern3, string):
        return True
    else:
        return False


def is_email(string: str) -> bool:
    """
    This function help us to identify a email

    Parameters:
    -----------
        string : str
            string

    Returns:
    --------
        bool : 
            True, if the input string is a email
            False, if the input string is not a email
    """
    # Define the regular expression pattern to match email addresses
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Use the search function to check if the pattern matches the input string
    if re.search(pattern, string):
        return True
    else:
        return False


def change_data_type(x):
    '''
    This function marks a feature from a dataset as Date, Numerical and String

    Parameters:
    -----------
        x : str 
            Feature name

    Returns:
    --------
        str : Feature type
    '''
    a = str(x)
    if a == 'datetime64[ns]':
        x = 'Date'
    elif a == 'float64' or a == 'float32':
        x = 'Numerical'
    elif a == 'int64' or a == 'int64':
        x = 'Numerical'
    elif a == 'object':
        x = 'String'
    elif a == 'bool':
        x = 'Boolean'
    
    return x


def get_featur_type(df:pd.DataFrame, categorical:list, numerical:list, datetime:list, string:list, boolean:list): # get_feature_type
    '''
    This function marks a feature from a dataset as Date, Numerical and String

    Parameters:
    -----------
        df : pandas.DataFrame 
            Name of the dataset
        categorical : list
             List of categorical variables
        numerical : list
            List of numerical variables
        datetime : list
            List of datetime variables
        string : list 
            List of string variables
        boolean : list 
            List of boolean variables

    Returns:
    --------
        list : 
            List of feature type
    '''
    freature_list = []
    for x in df.columns.to_list():
        if x in categorical or x in boolean:
            freature_list.append("Categorical")
        elif x in datetime:
            freature_list.append("Date")
        elif x in numerical:
            freature_list.append("Non Categorical")
        elif x in string:
            freature_list.append("String")

    return freature_list

def add_dataframe_title(df: pd.DataFrame, title: str) -> pd.DataFrame:
    try:
        """
        It helps us to add title to the dataframe
        
        parameter
        ---------
        df: pd.DataFrame
            _result_
            
        title: str
            _result_
            
        Returns
        -------
            pd.DataFrame
        """
        df = df.style.set_caption(f'{title}')
        return df
    except Exception as e:
        print(e)