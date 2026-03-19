import pandas as pd
import numpy as np


class Backtester:

    def __init__(self, fees_bps: float = 1.0, slippage_bps: float = 1.0):
        self.fees_bps = fees_bps
        self.slippage_bps = slippage_bps

    def run(self, prices: pd.DataFrame, signals: pd.DataFrame, initial_capital: float = 1_000_000):

        # -----------------------
        # MERGE DATA
        # -----------------------

        df = pd.merge(signals, prices, on=["date", "symbol"], how="left")
        df = df.sort_values(["date", "symbol"]).reset_index(drop=True)

        # -----------------------
        # RETURNS
        # -----------------------

        df["ret"] = df.groupby("symbol")["close"].pct_change(fill_method=None).fillna(0)

        # -----------------------
        # POSITION (LAG SIGNAL)
        # -----------------------

        df["position"] = df.groupby("symbol")["signal"].shift(1).fillna(0)

        # -----------------------
        # NORMALIZE WEIGHTS
        # -----------------------

        df["abs_pos"] = df.groupby("date")["position"].transform(lambda x: x.abs().sum())

        df["weight"] = np.where(
            df["abs_pos"] > 0,
            df["position"] / df["abs_pos"],
            0
        )

        # -----------------------
        # STRATEGY RETURNS
        # -----------------------

        df["strategy_ret"] = df["weight"] * df["ret"]

        # -----------------------
        # TRANSACTION COSTS
        # -----------------------

        df["trade"] = df.groupby("symbol")["weight"].diff().fillna(0).abs()

        cost_per_trade = (self.fees_bps + self.slippage_bps) / 10000.0

        df["cost"] = df["trade"] * cost_per_trade

        df["net_ret"] = df["strategy_ret"] - df["cost"]

        # -----------------------
        # PORTFOLIO RETURNS
        # -----------------------

        port = df.groupby("date")["net_ret"].sum().reset_index()

        # -----------------------
        # EQUITY CURVE
        # -----------------------

        port["equity"] = (1 + port["net_ret"]).cumprod() * initial_capital

        # -----------------------
        # PERFORMANCE METRICS
        # -----------------------

        total_days = len(port)

        if total_days == 0:
            raise ValueError("No data in backtest")

        cagr = (port["equity"].iloc[-1] / initial_capital) ** (252 / total_days) - 1

        vol = port["net_ret"].std() * np.sqrt(252)

        sharpe = cagr / vol if vol > 0 else 0

        drawdown = port["equity"] / port["equity"].cummax() - 1
        max_dd = drawdown.min()

        metrics = {
            "CAGR": float(cagr),
            "Volatility": float(vol),
            "Sharpe": float(sharpe),
            "MaxDrawdown": float(max_dd)
        }

        return port, metrics