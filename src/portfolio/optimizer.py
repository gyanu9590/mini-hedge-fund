"""
Portfolio optimizers (pure-Python).
Provides:
- inverse_vol_weights
- equal_risk_contribution
- min_variance_weights (optional via PyPortfolioOpt)
- size_from_signal
- volatility_target
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def inverse_vol_weights(returns: pd.DataFrame, cap: float | None = 0.15) -> pd.Series:
    vol = returns.std().replace(0, np.nan).fillna(1.0)
    w = 1.0 / vol
    w = w / w.sum()
    if cap is not None:
        w = np.clip(w, 0, cap)
        w = w / w.sum()
    return pd.Series(w, index=returns.columns)


def equal_risk_contribution(S: pd.DataFrame, max_iter: int = 1000, tol: float = 1e-8) -> pd.Series:
    n = S.shape[0]
    if n == 0:
        return pd.Series([], dtype=float)
    w = np.ones(n) / n
    S_val = S.values
    for _ in range(max_iter):
        m = S_val @ w
        rc = w * m
        target = rc.mean()
        step = target / (rc + 1e-12)
        w = np.maximum(w * step, 0)
        w_sum = w.sum()
        if w_sum <= 1e-12:
            w = np.ones(n) / n
        else:
            w = w / w_sum
        if np.max(np.abs(rc - target)) < tol:
            break
    return pd.Series(w, index=S.columns)


def min_variance_weights(prices: pd.DataFrame) -> pd.Series:
    try:
        from pypfopt import risk_models, EfficientFrontier, objective_functions
        S = risk_models.sample_cov(prices)
        ef = EfficientFrontier(np.zeros(S.shape[0]), S, weight_bounds=(0, 1))
        ef.add_objective(objective_functions.L2_reg, gamma=1e-4)
        w = ef.min_volatility()
        w = pd.Series(w, index=S.columns)
        w[w < 0] = 0
        w = w / w.sum()
        return w
    except Exception:
        return inverse_vol_weights(prices.pct_change().dropna())


def size_from_signal(signals: pd.Series, cap: float = 0.15) -> pd.Series:
    s = pd.Series(signals).copy().fillna(0.0)
    s = s.clip(-1.0, 1.0)
    raw = s.copy()
    abs_sum = raw.abs().sum()
    if abs_sum == 0:
        normalized = raw * 0.0
    else:
        normalized = raw / abs_sum
    capped = normalized.clip(-cap, cap)
    gross = capped.abs().sum()
    if gross == 0:
        final = capped
    else:
        final = capped / gross
    return pd.Series(final, index=s.index)


def volatility_target(returns: pd.Series, target_annual_vol: float = 0.12, lookback: int = 20, trading_days: int = 252) -> float:
    vol = returns.rolling(lookback).std().iloc[-1] * np.sqrt(trading_days)
    if vol == 0 or np.isnan(vol):
        return 1.0
    lev = target_annual_vol / vol
    return float(np.clip(lev, 0.0, 3.0))
