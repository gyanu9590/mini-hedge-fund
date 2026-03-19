import pandas as pd
import numpy as np


def add_features(df):

    df = df.sort_values("date").copy()

    # -----------------------
    # BASIC RETURNS
    # -----------------------

    df["returns"] = df["close"].pct_change()

    # -----------------------
    # MOMENTUM FEATURES
    # -----------------------

    df["momentum_5"] = df["close"].pct_change(5)
    df["momentum_10"] = df["close"].pct_change(10)
    df["momentum_20"] = df["close"].pct_change(20)

    # -----------------------
    # MOVING AVERAGES
    # -----------------------

    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["ma_50"] = df["close"].rolling(50).mean()

    # -----------------------
    # PRICE RELATIVE TO MA
    # -----------------------

    df["price_ma10_ratio"] = df["close"] / df["ma_10"]
    df["price_ma20_ratio"] = df["close"] / df["ma_20"]

    # -----------------------
    # VOLATILITY
    # -----------------------

    df["volatility_10"] = df["returns"].rolling(10).std()
    df["volatility_20"] = df["returns"].rolling(20).std()

    # -----------------------
    # RSI (Relative Strength Index)
    # -----------------------

    delta = df["close"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

    rs = gain / (loss + 1e-9)

    df["rsi"] = 100 - (100 / (1 + rs))

    # -----------------------
    # MACD
    # -----------------------

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # -----------------------
    # TREND STRENGTH
    # -----------------------

    df["trend_strength"] = df["ma_10"] - df["ma_50"]

    # -----------------------
    # VOLATILITY ADJUSTED RETURNS
    # -----------------------

    df["vol_adj_return"] = df["returns"] / (df["volatility_10"] + 1e-9)

    # -----------------------
    # TARGET (IMPROVED)
    # -----------------------

    df["future_return_10d"] = df["close"].shift(-10) / df["close"] - 1

    df["target"] = np.where(
        df["future_return_10d"] > 0.03,   # 3% threshold
        1,
        0
    )

    # -----------------------
    # CLEAN DATA
    # -----------------------

    df = df.dropna().reset_index(drop=True)

    return df