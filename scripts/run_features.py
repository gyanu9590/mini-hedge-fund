import pandas as pd
import numpy as np
import glob

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def load_prices():
    files = glob.glob("data/prices/*.parquet")
    dfs = []
    for f in files:
        df = pd.read_parquet(f)
        symbol = f.split("\\")[-1].replace(".parquet", "")
        df["symbol"] = symbol
        dfs.append(df)
    return pd.concat(dfs)

df = load_prices()
df = df.sort_values(["symbol", "date"])

# =========================
# FEATURE ENGINEERING
# =========================

# Returns
df["returns"] = df.groupby("symbol")["close"].pct_change()

# Momentum
df["momentum_5"] = df.groupby("symbol")["close"].pct_change(5)
df["momentum_10"] = df.groupby("symbol")["close"].pct_change(10)

# Volatility
df["volatility"] = df.groupby("symbol")["returns"].rolling(10).std().reset_index(0, drop=True)

# RSI
df["rsi"] = df.groupby("symbol")["close"].transform(lambda x: compute_rsi(x))

# Moving averages
df["ma_20"] = df.groupby("symbol")["close"].transform(lambda x: x.rolling(20).mean())
df["ma_50"] = df.groupby("symbol")["close"].transform(lambda x: x.rolling(50).mean())

# =========================
# 🔥 IMPORTANT: NEW TARGET
# =========================

# Future return (5 days ahead)
df["future_return"] = df.groupby("symbol")["close"].shift(-5) / df["close"] - 1

# Only consider meaningful moves (>2%)
df["target"] = (df["future_return"] > 0.02).astype(int)

df = df.dropna()

df.to_parquet("data/features/features.parquet")
print("✅ Features saved")