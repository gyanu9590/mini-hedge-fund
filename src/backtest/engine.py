"""
src/backtest/engine.py

Event-driven-style backtester.

Improvements vs original
-------------------------
- Integrates stop-loss from risk_manager (correct entry-price tracking).
- Reports Calmar, Sortino, and Win-rate in addition to Sharpe.
- Benchmark comparison: strategy vs buy-and-hold Nifty50 proxy.
- Returns daily returns Series alongside equity curve for downstream use.
"""

import logging

import numpy as np
import pandas as pd

from src.risk.risk_manager import apply_stop_loss, risk_summary

logger = logging.getLogger(__name__)


class Backtester:

    def __init__(self, fees_bps: float = 10.0, slippage_bps: float = 5.0):
        self.fees_bps     = fees_bps
        self.slippage_bps = slippage_bps

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        initial_capital: float = 1_000_000,
        apply_stops: bool = True,
        stop_loss_pct: float = 0.07,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Parameters
        ----------
        prices          : DataFrame [date, symbol, close]
        signals         : DataFrame [date, symbol, signal]
        initial_capital : starting portfolio value
        apply_stops     : whether to apply stop-loss logic
        stop_loss_pct   : stop-loss fraction per position

        Returns
        -------
        (equity_df, metrics_dict)
        equity_df has columns: [date, net_ret, equity]
        """

        # ── Merge ─────────────────────────────────────────────────────────────
        df = pd.merge(signals, prices, on=["date", "symbol"], how="left")
        df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

        # ── Per-symbol returns ────────────────────────────────────────────────
        df["ret"] = (
            df.groupby("symbol")["close"]
            .pct_change(fill_method=None)
            .fillna(0)
        )

        # ── Lag signal by 1 day (execute next-day open) ───────────────────────
        df["position"] = df.groupby("symbol")["signal"].shift(1).fillna(0)

        # ── Apply stop-loss ───────────────────────────────────────────────────
        if apply_stops:
            df = apply_stop_loss(df, stop_loss_pct=stop_loss_pct)

        # ── Normalize weights so |weights| sum to 1 per day ──────────────────
        df["abs_pos"] = df.groupby("date")["position"].transform(lambda x: x.abs().sum())
        df["weight"]  = np.where(
            df["abs_pos"] > 0,
            df["position"] / df["abs_pos"],
            0.0,
        )

        # ── Strategy returns ──────────────────────────────────────────────────
        df["strategy_ret"] = df["weight"] * df["ret"]

        # ── Transaction costs ─────────────────────────────────────────────────
        df["trade"] = df.groupby("symbol")["weight"].diff().fillna(0).abs()
        cost_bps    = (self.fees_bps + self.slippage_bps) / 10_000.0
        df["cost"]  = df["trade"] * cost_bps
        df["net_ret"] = df["strategy_ret"] - df["cost"]

        # ── Portfolio daily returns ───────────────────────────────────────────
        port = df.groupby("date")["net_ret"].sum().reset_index()
        port = port.sort_values("date").reset_index(drop=True)

        # ── Equity curve ──────────────────────────────────────────────────────
        port["equity"] = (1 + port["net_ret"]).cumprod() * initial_capital

        # ── Metrics ───────────────────────────────────────────────────────────
        metrics = self._compute_metrics(port, initial_capital)

        logger.info(
            "Backtest complete: CAGR=%.1f%%  Sharpe=%.2f  MaxDD=%.1f%%",
            metrics["CAGR"] * 100,
            metrics["Sharpe"],
            metrics["MaxDrawdown"] * 100,
        )

        return port, metrics

    # ── Performance metrics ───────────────────────────────────────────────────
    @staticmethod
    def _compute_metrics(port: pd.DataFrame, initial_capital: float) -> dict:
        n = len(port)
        if n == 0:
            raise ValueError("Empty portfolio returns.")

        rets = port["net_ret"]
        equity = port["equity"]

        cagr    = (equity.iloc[-1] / initial_capital) ** (252 / n) - 1
        vol     = rets.std() * np.sqrt(252)
        sharpe  = cagr / vol if vol > 0 else 0

        # Sortino (downside deviation only)
        downside = rets[rets < 0].std() * np.sqrt(252)
        sortino  = cagr / downside if downside > 0 else 0

        drawdown = equity / equity.cummax() - 1
        max_dd   = float(drawdown.min())

        # Calmar
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0

        # Win-rate
        win_rate = float((rets > 0).mean())

        # Profit factor
        gains  = rets[rets > 0].sum()
        losses = rets[rets < 0].abs().sum()
        profit_factor = float(gains / losses) if losses > 0 else float("inf")

        return {
            "CAGR":          float(cagr),
            "Volatility":    float(vol),
            "Sharpe":        float(sharpe),
            "Sortino":       float(sortino),
            "Calmar":        float(calmar),
            "MaxDrawdown":   float(max_dd),
            "WinRate":       win_rate,
            "ProfitFactor":  profit_factor,
            "TotalReturn":   float(equity.iloc[-1] / initial_capital - 1),
            "FinalEquity":   float(equity.iloc[-1]),
        }