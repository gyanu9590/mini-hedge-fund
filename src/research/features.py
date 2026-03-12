import pandas as pd


def add_features(df):

    df = df.sort_values("date")

    # returns
    df["returns"] = df["close"].pct_change()

    # ---------------------
    # MOMENTUM FEATURES
    # ---------------------

    df["momentum_3"] = df["close"].pct_change(3)
    df["momentum_5"] = df["close"].pct_change(5)
    df["momentum_10"] = df["close"].pct_change(10)
    df["momentum_20"] = df["close"].pct_change(20)
    df["momentum_50"] = df["close"].pct_change(50)

    # ---------------------
    # TREND FEATURES
    # ---------------------

    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["ma_50"] = df["close"].rolling(50).mean()
    df["ma_100"] = df["close"].rolling(100).mean()

    df["ma_ratio"] = df["close"] / df["ma_50"]

    # ---------------------
    # VOLATILITY FEATURES
    # ---------------------

    df["volatility_5"] = df["returns"].rolling(5).std()
    df["volatility_10"] = df["returns"].rolling(10).std()
    df["volatility_20"] = df["returns"].rolling(20).std()

    # ---------------------
    # MEAN REVERSION FEATURES
    # ---------------------

    mean20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()

    df["bollinger_upper"] = mean20 + 2 * std20
    df["bollinger_lower"] = mean20 - 2 * std20

    df["zscore"] = (df["close"] - mean20) / std20
    df["price_ma_distance"] = df["close"] - mean20

    # ---------------------
    # VOLUME FEATURES
    # ---------------------

    if "volume" in df.columns:

        df["volume_change"] = df["volume"].pct_change()
        df["volume_ma"] = df["volume"].rolling(10).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma"]

    # drop missing values
    df = df.dropna()

    return df