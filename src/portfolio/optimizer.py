"""
src/portfolio/optimizer.py

Portfolio optimizers (pure-Python, no hidden deps except numpy/pandas).

Provides
--------
- inverse_vol_weights
- equal_risk_contribution  (ERC / Risk Parity)
- min_variance_weights     (requires PyPortfolioOpt; graceful fallback)
- size_from_signal         ← USED BY run_orders.py
- volatility_target        ← USED BY run_orders.py
- select_optimizer         ← dispatches by config string

All functions accept a `cap` kwarg; sizes are normalized so |weights| sum to 1.
"""

from __future__ import annotations

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


# ── Individual optimizers ─────────────────────────────────────────────────────

def inverse_vol_weights(returns: pd.DataFrame, cap: float = 0.20) -> pd.Series:
    """Allocate inversely proportional to historical volatility."""
    vol = returns.std().replace(0, np.nan).fillna(1.0)
    w   = 1.0 / vol
    w   = w / w.sum()
    w   = np.clip(w, 0, cap)
    w   = w / w.sum()
    return pd.Series(w, index=returns.columns)


def equal_risk_contribution(
    cov: pd.DataFrame,
    max_iter: int = 1_000,
    tol: float = 1e-8,
    cap: float = 0.20,
) -> pd.Series:
    """
    Equal Risk Contribution (Risk Parity).
    Iterative Newton-style convergence.
    """
    n = cov.shape[0]
    if n == 0:
        return pd.Series([], dtype=float)

    w   = np.ones(n) / n
    Sigma = cov.values

    for _ in range(max_iter):
        marginal = Sigma @ w
        rc       = w * marginal
        target   = rc.mean()
        step     = target / (rc + 1e-12)
        w        = np.maximum(w * step, 0)
        total    = w.sum()
        if total <= 1e-12:
            w = np.ones(n) / n
        else:
            w /= total
        if np.max(np.abs(rc - target)) < tol:
            break

    w = np.clip(w, 0, cap)
    w /= w.sum()
    return pd.Series(w, index=cov.columns)


def min_variance_weights(prices: pd.DataFrame, cap: float = 0.20) -> pd.Series:
    """Minimum-variance via PyPortfolioOpt; falls back to inv-vol."""
    try:
        from pypfopt import risk_models, EfficientFrontier, objective_functions
        S  = risk_models.sample_cov(prices)
        ef = EfficientFrontier(np.zeros(S.shape[0]), S, weight_bounds=(0, cap))
        ef.add_objective(objective_functions.L2_reg, gamma=1e-4)
        w  = pd.Series(ef.min_volatility(), index=S.columns)
        w  = w.clip(0, cap)
        w /= w.sum()
        return w
    except Exception as e:
        logger.warning("min_variance fallback to inv_vol: %s", e)
        return inverse_vol_weights(prices.pct_change().dropna(), cap=cap)


def equal_weight(signals: pd.Series, cap: float = 0.20) -> pd.Series:
    """Simple equal-weight, respecting sign of signal."""
    s = signals.copy().fillna(0)
    s = s[s != 0]
    if len(s) == 0:
        return pd.Series(dtype=float)
    w = s.apply(np.sign) / len(s)
    return w.clip(-cap, cap)


# ── Signal-aware sizer (used in run_orders.py) ────────────────────────────────

def size_from_signal(
    signals: pd.Series,
    returns: pd.DataFrame | None = None,
    cap: float | None = None,
) -> pd.Series:
    """
    Convert raw signals (+1/-1/0) into portfolio weights using the optimizer
    specified in configs/settings.yaml.

    If returns DataFrame is provided, proper covariance-based methods are used.
    Otherwise falls back to equal-weight.
    """
    cfg       = _load_cfg()
    risk_cfg  = cfg.get("risk", {})
    method    = risk_cfg.get("portfolio_optimizer", "erc")
    if cap is None:
        cap = risk_cfg.get("max_weight_per_stock", 0.20)

    active = signals[signals != 0].copy()
    if len(active) == 0:
        return pd.Series(dtype=float)

    signs = active.apply(np.sign)  # keep direction (+1 / -1)

    if method == "equal_weight" or returns is None:
        w = equal_weight(active, cap=cap)
        return w

    active_rets = returns[active.index] if active.index.isin(returns.columns).all() else None

    if active_rets is None or active_rets.empty:
        return equal_weight(active, cap=cap)

    if method == "inv_vol":
        raw_w = inverse_vol_weights(active_rets, cap=cap)

    elif method == "min_var":
        raw_w = min_variance_weights(active_rets.cumsum() + 1, cap=cap)

    else:  # default: ERC
        cov = pd.DataFrame(
            np.cov(active_rets.T) if len(active_rets.columns) > 1 else [[active_rets.iloc[:, 0].var()]],
            index=active_rets.columns,
            columns=active_rets.columns,
        )
        raw_w = equal_risk_contribution(cov, cap=cap)

    # Apply signal direction
    signed_w = raw_w * signs
    signed_w = signed_w.clip(-cap, cap)
    total    = signed_w.abs().sum()
    if total > 0:
        signed_w /= total

    return signed_w


# ── Volatility targeting scalar ───────────────────────────────────────────────

def volatility_target(
    returns: pd.Series,
    target_annual_vol: float | None = None,
    lookback: int | None = None,
    trading_days: int = 252,
) -> float:
    """
    Returns a leverage scalar in [0, 3] so that realized vol ≈ target.
    Multiply portfolio weights by this scalar before sizing orders.
    """
    cfg = _load_cfg()
    risk_cfg = cfg.get("risk", {})
    if target_annual_vol is None:
        target_annual_vol = risk_cfg.get("volatility_target_annual", 0.15)
    if lookback is None:
        lookback = risk_cfg.get("volatility_lookback_days", 20)

    recent_vol = returns.rolling(lookback).std().iloc[-1] * np.sqrt(trading_days)
    if recent_vol == 0 or np.isnan(recent_vol):
        return 1.0
    lev = target_annual_vol / recent_vol
    return float(np.clip(lev, 0.0, 3.0))


# ── Dispatcher ────────────────────────────────────────────────────────────────

def select_optimizer(name: str):
    return {
        "equal_weight": equal_weight,
        "inv_vol":      inverse_vol_weights,
        "erc":          equal_risk_contribution,
        "min_var":      min_variance_weights,
    }.get(name, equal_weight)