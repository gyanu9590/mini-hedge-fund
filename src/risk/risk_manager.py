# src/risk/risk_manager.py

import pandas as pd

def apply_stop_loss(df, stop_loss_pct=0.05):
    """
    If price falls more than stop_loss_pct from entry, close position.
    df must contain: date, symbol, close, position
    """
    df = df.copy()
    df["entry_price"] = df.groupby("symbol")["close"].transform("first")
    df["drawdown"] = (df["close"] - df["entry_price"]) / df["entry_price"]

    df.loc[df["drawdown"] <= -stop_loss_pct, "position"] = 0
    return df


def cap_portfolio_weights(weights, max_weight=0.2):
    """
    Cap max allocation per stock
    """
    return weights.clip(-max_weight, max_weight)
