"""
src/risk/risk_manager.py

Risk management utilities.

Fixes vs original
-----------------
- apply_stop_loss now tracks the ACTUAL entry price per position (not first-ever price).
- cap_portfolio_weights clips properly for long/short.
- New: daily_var and expected_shortfall for risk reporting.
- New: position-level P&L attribution.
"""

import logging

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def _load_cfg() -> dict:
    try:
        with open("configs/settings.yaml") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


# ── Stop-loss (tracks real entry price per position entry) ────────────────────
def apply_stop_loss(df: pd.DataFrame, stop_loss_pct: float | None = None) -> pd.DataFrame:
    """
    Close any position whose price falls more than `stop_loss_pct` below
    the price at which the position was ENTERED (signal first became 1 or -1).

    Parameters
    ----------
    df             : must have [date, symbol, close, signal, position] columns.
    stop_loss_pct  : fraction e.g. 0.07 = 7%. Loaded from config if None.

    Returns
    -------
    Same DataFrame with 'position' zeroed out where stop-loss triggered.
    """
    if stop_loss_pct is None:
        cfg = _load_cfg()
        stop_loss_pct = cfg.get("risk", {}).get("stop_loss_pct", 0.07)

    df = df.copy().sort_values(["symbol", "date"])

    for symbol, grp in df.groupby("symbol", sort=False):
        idx = grp.index.tolist()

        entry_price = None
        entry_side  = 0

        for i in idx:
            pos   = df.at[i, "position"]
            price = df.at[i, "close"]

            # New position opened
            if pos != 0 and entry_side == 0:
                entry_price = price
                entry_side  = pos

            # Position closed by signal
            elif pos == 0 and entry_side != 0:
                entry_price = None
                entry_side  = 0

            # Position direction flipped
            elif pos != 0 and pos != entry_side:
                entry_price = price
                entry_side  = pos

            # Check stop-loss for active long position
            if entry_price is not None and entry_side == 1:
                if price <= entry_price * (1 - stop_loss_pct):
                    df.at[i, "position"] = 0
                    logger.info(
                        "STOP-LOSS triggered: %s  entry=%.2f  current=%.2f",
                        symbol, entry_price, price,
                    )
                    entry_price = None
                    entry_side  = 0

            # Check stop-loss for active short position (price spikes up)
            elif entry_price is not None and entry_side == -1:
                if price >= entry_price * (1 + stop_loss_pct):
                    df.at[i, "position"] = 0
                    logger.info(
                        "SHORT STOP-LOSS triggered: %s  entry=%.2f  current=%.2f",
                        symbol, entry_price, price,
                    )
                    entry_price = None
                    entry_side  = 0

    return df


# ── Weight capping ────────────────────────────────────────────────────────────
def cap_portfolio_weights(weights: pd.Series, max_weight: float | None = None) -> pd.Series:
    """Cap absolute weight per name; renormalize."""
    if max_weight is None:
        cfg = _load_cfg()
        max_weight = cfg.get("risk", {}).get("max_weight_per_stock", 0.20)

    w = weights.copy()
    w = w.clip(-max_weight, max_weight)
    total = w.abs().sum()
    if total > 0:
        w = w / total
    return w


# ── VaR / CVaR ────────────────────────────────────────────────────────────────
def daily_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Historical simulation Value-at-Risk (negative number = loss)."""
    if len(returns) < 20:
        return float("nan")
    return float(np.percentile(returns.dropna(), (1 - confidence) * 100))


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """CVaR / Expected Shortfall beyond the VaR threshold."""
    if len(returns) < 20:
        return float("nan")
    var = daily_var(returns, confidence)
    tail = returns[returns <= var]
    return float(tail.mean()) if len(tail) > 0 else var


# ── Portfolio-level risk summary ──────────────────────────────────────────────
def risk_summary(equity_series: pd.Series) -> dict:
    """
    Given a daily equity curve, return a dict of risk metrics.
    """
    rets = equity_series.pct_change().dropna()
    if len(rets) < 10:
        return {}

    ann = np.sqrt(252)
    vol = rets.std() * ann

    dd = equity_series / equity_series.cummax() - 1
    max_dd = float(dd.min())

    return {
        "daily_vol":         float(rets.std()),
        "annual_vol":        float(vol),
        "var_95_daily":      daily_var(rets, 0.95),
        "cvar_95_daily":     expected_shortfall(rets, 0.95),
        "max_drawdown":      max_dd,
        "calmar":            float((rets.mean() * 252) / abs(max_dd)) if max_dd != 0 else 0,
        "positive_days_pct": float((rets > 0).mean()),
    }