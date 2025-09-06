# src/backtest/engine.py
import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, fees_bps: float = 1.0, slippage_bps: float = 1.0):
        """
        fees_bps: transaction cost in basis points (1 bps = 0.01%)
        slippage_bps: execution slippage in basis points
        """
        self.fees_bps = fees_bps
        self.slippage_bps = slippage_bps

    def run(self, prices: pd.DataFrame, signals: pd.DataFrame, initial_capital: float = 1_000_000):
        """
        Run a simple backtest.
        prices: DataFrame with ['date','symbol','close']
        signals: DataFrame with ['date','symbol','signal'] (weights or positions)
        initial_capital: starting portfolio value
        """
        # Merge signals and prices
        df = pd.merge(signals, prices, on=["date","symbol"], how="left").sort_values(["date","symbol"])
        
        # Daily returns
        df["ret"] = df.groupby("symbol")["close"].pct_change().fillna(0)

        # Position = signal weight
        df["position"] = df["signal"].shift(1).fillna(0)  # lag signals (trade at next bar)

        # Strategy return = position * asset return
        df["strategy_ret"] = df["position"] * df["ret"]

        # Transaction costs (apply when position changes)
        df["trade"] = df.groupby("symbol")["position"].diff().fillna(0).abs()
        cost_per_trade = (self.fees_bps + self.slippage_bps) / 10000.0
        df["cost"] = df["trade"] * cost_per_trade

        # Net return = strategy return - cost
        df["net_ret"] = df["strategy_ret"] - df["cost"]

        # Aggregate portfolio return by date
        port = df.groupby("date")["net_ret"].mean().reset_index()
        port["equity"] = (1 + port["net_ret"]).cumprod() * initial_capital

        # Performance metrics
        cagr = (port["equity"].iloc[-1] / initial_capital) ** (252/len(port)) - 1
        vol = port["net_ret"].std() * np.sqrt(252)
        sharpe = cagr / vol if vol > 0 else 0
        dd = (port["equity"] / port["equity"].cummax() - 1).min()

        metrics = {
            "CAGR": cagr,
            "Volatility": vol,
            "Sharpe": sharpe,
            "MaxDrawdown": dd
        }

        return port, metrics
