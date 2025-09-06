# src/research/features.py
import pandas as pd
import numpy as np

def add_features(df):
    """
    Adds common features: returns, rolling mean/std (z-score), RSI, ATR-lite.
    Uses min_periods=1 to avoid NaNs during development.
    """
    df = df.sort_values("date").copy().reset_index(drop=True)
    df["ret_1"] = df["close"].pct_change().fillna(0.0)

    # rolling stats with min_periods to avoid NaN for short series (dev-friendly)
    window = 20
    df["ma_20"] = df["close"].rolling(window, min_periods=1).mean()
    # use ddof=0 for population std to avoid NaNs; replace zeros
    df["std_20"] = df["close"].rolling(window, min_periods=1).std(ddof=0).replace(0, 1e-9)
    df["z_20"] = (df["close"] - df["ma_20"]) / df["std_20"]

    # simple RSI (14)
    delta = df["close"].diff().fillna(0)
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    roll_up = up.rolling(14, min_periods=1).mean()
    roll_down = down.rolling(14, min_periods=1).mean().replace(0, 1e-9)
    rs = roll_up / roll_down
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # ATR-lite: use rolling std of returns as proxy
    df["atr_14"] = df["ret_1"].rolling(14, min_periods=1).std().fillna(0.0)

    return df
