import pandas as pd
import numpy as np


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").copy()

    # -------------------------
    # Basic Returns
    # -------------------------
    df["returns"] = df["close"].pct_change()

    # -------------------------
    # Momentum
    # -------------------------
    df["momentum_5"] = df["close"] / df["close"].shift(5) - 1
    df["momentum_10"] = df["close"] / df["close"].shift(10) - 1
    df["momentum_20"] = df["close"] / df["close"].shift(20) - 1

    # -------------------------
    # Moving Averages
    # -------------------------
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["ma_50"] = df["close"].rolling(50).mean()

    # -------------------------
    # Price / MA ratios
    # -------------------------
    df["price_ma10_ratio"] = df["close"] / df["ma_10"]
    df["price_ma20_ratio"] = df["close"] / df["ma_20"]

    # -------------------------
    # Volatility
    # -------------------------
    df["volatility_10"] = df["returns"].rolling(10).std()
    df["volatility_20"] = df["returns"].rolling(20).std()

    # -------------------------
    # RSI
    # -------------------------
    delta = df["close"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # -------------------------
    # MACD
    # -------------------------
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # -------------------------
    # Volume features (only if exists)
    # -------------------------
    if "volume" in df.columns:
        df["volume_ma10"] = df["volume"].rolling(10).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma10"]

    df = df.dropna()

    return df