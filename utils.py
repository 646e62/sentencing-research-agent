"""
Utility functions for the sentencing data analysis project. More tools will be
added as the project progresses.
"""

# CSV/Pandas conversion tools

import pandas as pd

def csv_to_pandas(file_path: str) -> pd.DataFrame:
    """
    Read a CSV file into a pandas dataframe. This converts the sentencing data 
    stored in the CSV files into a pandas dataframe.

    Args:
        file_path: The path to the CSV filecs
    Returns:
        A pandas dataframe
    """

    df = pd.read_csv(file_path, on_bad_lines='skip', engine='python')
    return df

def pandas_to_csv(df: pd.DataFrame, file_path: str) -> None:
    """
    Save a pandas dataframe to a CSV file.

    Args:
        df: The pandas dataframe to save
        file_path: The path to the CSV file
    Returns:
        None - the dataframe is saved to the file path
    """
    df.to_csv(file_path, index=False)

def append_files(file_paths: list[str]) -> pd.DataFrame:
    """
    Append several CSV files into a single dataframe.

    Args:
        file_paths: A list of paths to the CSV files
    Returns:
        A pandas dataframe
    """
    dataframes = []
    for file_path in file_paths:
        dataframes.append(csv_to_pandas(file_path))
    df = pd.concat(dataframes, ignore_index=True)
    return df

