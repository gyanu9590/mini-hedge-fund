import pandas as pd

def add_features(df):

    df = df.sort_values("date")

    # daily returns
    df["returns"] = df["close"].pct_change()

    # momentum features
    df["momentum_5"] = df["close"].pct_change(5)
    df["momentum_10"] = df["close"].pct_change(10)

    # moving averages
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()

    return df