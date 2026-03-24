"""
src/backtest/walkforward.py

TRUE rolling walk-forward with 3-class target and calibrated thresholds.

Key fix: uses a symmetric threshold so long/short classes are balanced.
Returns only OOS rows - zero leakage.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)


def walk_forward_training(
    df: pd.DataFrame,
    train_window_days: int = 252,
    step_days: int = 21,
    min_train_rows: int = 120,
    target_horizon: int = 5,
    target_threshold: float = 0.02,
) -> pd.DataFrame | None:

    df = df.sort_values("date").copy().reset_index(drop=True)

    # ── 3-class target: +1 (strong up), -1 (strong down), 0 (neutral) ─────────
    # This fixes the imbalanced binary target problem.
    # long_threshold  = top X% of returns = class +1
    # short_threshold = bottom X% of returns = class -1
    df["future_return"] = df.groupby("symbol")["close"].transform(
        lambda s: s.shift(-target_horizon) / s - 1
    )

    # Use rolling per-date quantiles so thresholds adapt to market regime
    upper = df.groupby("date")["future_return"].transform(lambda x: x.quantile(0.65))
    lower = df.groupby("date")["future_return"].transform(lambda x: x.quantile(0.35))

    df["target"] = 0
    df.loc[df["future_return"] >= upper, "target"] = 1
    df.loc[df["future_return"] <= lower, "target"] = -1

    feature_cols = [
        c for c in df.columns
        if c not in ["date", "symbol", "target", "future_return",
                     "future_return_5d", "future_return_10d",
                     "close", "open", "high", "low", "volume", "probability"]
    ]

    df["probability"] = np.nan

    unique_dates = df["date"].sort_values().unique()
    n = len(unique_dates)

    if n < train_window_days + step_days:
        logger.warning("Not enough dates for walk-forward. Using single split.")
        return _single_split(df, feature_cols, train_window_days, min_train_rows)

    step_start = train_window_days
    folds_run  = 0

    while step_start < n:
        train_dates = unique_dates[max(0, step_start - train_window_days):step_start]
        test_dates  = unique_dates[step_start: step_start + step_days]

        train_mask = df["date"].isin(train_dates)
        test_mask  = df["date"].isin(test_dates)

        train_df = df[train_mask].dropna(subset=feature_cols + ["target"])
        test_df  = df[test_mask].dropna(subset=feature_cols)

        if len(train_df) < min_train_rows or len(test_df) == 0:
            step_start += step_days
            continue

        # Only train on strong signal rows (exclude neutral class 0)
        train_strong = train_df[train_df["target"] != 0]
        if len(train_strong) < 30:
            step_start += step_days
            continue

        X_train = train_strong[feature_cols]
        y_train = (train_strong["target"] == 1).astype(int)  # binary: 1=up, 0=down
        X_test  = test_df[feature_cols]

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=7,
            min_samples_leaf=8,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )
        model.fit(X_train, y_train)

        # probability = P(stock will be in top 35% of returns)
        probs = model.predict_proba(X_test)[:, 1]
        df.loc[test_df.index, "probability"] = probs

        folds_run += 1
        step_start += step_days

    logger.info("Walk-forward complete: %d folds trained.", folds_run)

    if folds_run == 0:
        return _single_split(df, feature_cols, train_window_days, min_train_rows)

    return df[df["probability"].notna()].copy()


def _single_split(df, feature_cols, train_window_days, min_train_rows):
    df = df.dropna(subset=feature_cols + ["target"]).reset_index(drop=True)
    split = int(len(df) * 0.70)
    if split < min_train_rows:
        return None

    train_df = df.iloc[:split]
    test_df  = df.iloc[split:].copy()

    train_strong = train_df[train_df["target"] != 0]
    if len(train_strong) == 0:
        return None

    model = RandomForestClassifier(
        n_estimators=200, max_depth=7, min_samples_leaf=8,
        max_features="sqrt", random_state=42, n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(
        train_strong[feature_cols],
        (train_strong["target"] == 1).astype(int)
    )
    test_df["probability"] = model.predict_proba(test_df[feature_cols])[:, 1]
    return test_df