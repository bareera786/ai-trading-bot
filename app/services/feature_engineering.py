"""
Feature engineering for ML models.
Handles creation of lag features, rolling statistics, and data normalization.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any

def create_lag_features(df: pd.DataFrame, columns: List[str], lags: List[int]) -> pd.DataFrame:
    """
    Create lag features for specified columns.
    
    Args:
        df: Input DataFrame
        columns: List of column names to create lags for
        lags: List of lag periods (e.g., [1, 2, 3])
        
    Returns:
        DataFrame with added lag columns
    """
    df_out = df.copy()
    
    for col in columns:
        if col not in df.columns:
            continue
            
        for lag in lags:
            df_out[f'{col}_lag_{lag}'] = df[col].shift(lag)
            
    return df_out

def create_rolling_stats(df: pd.DataFrame, columns: List[str], windows: List[int]) -> pd.DataFrame:
    """
    Create rolling mean and std features.
    
    Args:
        df: Input DataFrame
        columns: List of columns to calculate rolling stats for
        windows: List of window sizes
        
    Returns:
        DataFrame with added rolling statistic columns
    """
    df_out = df.copy()
    
    for col in columns:
        if col not in df.columns:
            continue
            
        for window in windows:
            # Rolling Mean
            df_out[f'{col}_roll_mean_{window}'] = df[col].rolling(window=window).mean()
            # Rolling Std
            df_out[f'{col}_roll_std_{window}'] = df[col].rolling(window=window).std()
            
    return df_out

def create_rsi_feature(df: pd.DataFrame, price_col: str = 'close', period: int = 14) -> pd.DataFrame:
    """
    Calculate RSI if not already present.
    """
    if 'rsi' in df.columns:
        return df
        
    df_out = df.copy()
    delta = df_out[price_col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    df_out['rsi'] = 100 - (100 / (1 + rs))
    return df_out

def prepare_lstm_data(
    df: pd.DataFrame, 
    target_col: str = 'close', 
    lookback: int = 60
) -> Dict[str, Any]:
    """
    Prepare data specifically for LSTM consumption.
    Clean NaNs, normalize, and sequence.
    """
    # drop NaNs created by lags/rolling
    df_clean = df.dropna().copy()
    
    if len(df_clean) < lookback:
        return {"error": "Insufficient data after feature engineering"}
        
    # Validation split point (last 20%)
    split_idx = int(len(df_clean) * 0.8)
    
    return {
        "data": df_clean,
        "split_idx": split_idx
    }
