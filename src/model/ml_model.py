"""
src/model/ml_model.py

Leak-free ensemble. Reads top_n / bottom_n from config correctly.
"""

import logging
import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.backtest.walkforward import walk_forward_training

logger = logging.getLogger(__name__)


def _load_cfg():
    try:
        with open("configs/settings.yaml") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


_EXCLUDE = {
    "date", "symbol", "target", "future_return",
    "future_return_5d", "future_return_10d",
    "probability", "signal",
    "close", "open", "high", "low", "volume",
}


def _feature_cols(df):
    return [c for c in df.columns if c not in _EXCLUDE]


def generate_signals(df: pd.DataFrame):
    cfg       = _load_cfg()
    model_cfg = cfg.get("model", {})
    sig_cfg   = model_cfg.get("signal", {})

    train_window = model_cfg.get("train_window_days", 252)
    step_days    = model_cfg.get("step_days", 21)
    min_rows     = model_cfg.get("min_train_rows", 120)
    horizon      = model_cfg.get("target_horizon_days", 5)
    threshold    = model_cfg.get("target_threshold", 0.02)

    # Read explicitly as int so YAML "0" is never misread
    top_n    = int(sig_cfg.get("top_n", 5))
    bottom_n = int(sig_cfg.get("bottom_n", 0))

    logger.info("Signal config: top_n=%d  bottom_n=%d", top_n, bottom_n)

    ens_w = model_cfg.get("ensemble_weights", {"xgb": 0.50, "rf": 0.30, "lr": 0.20})

    # ── Walk-forward base model ───────────────────────────────────────────────
    oos = walk_forward_training(
        df,
        train_window_days=train_window,
        step_days=step_days,
        min_train_rows=min_rows,
        target_horizon=horizon,
        target_threshold=threshold,
    )

    if oos is None or len(oos) == 0:
        logger.error("Walk-forward returned no data.")
        return None

    feature_cols = _feature_cols(oos)
    oos = oos.dropna(subset=feature_cols).copy()

    # ── Ensemble on in-sample strong examples ─────────────────────────────────
    first_oos_date = oos["date"].min()
    in_sample = df[df["date"] < first_oos_date].copy()

    in_sample["future_return"] = in_sample.groupby("symbol")["close"].transform(
        lambda s: s.shift(-horizon) / s - 1
    )
    upper = in_sample.groupby("date")["future_return"].transform(lambda x: x.quantile(0.65))
    lower = in_sample.groupby("date")["future_return"].transform(lambda x: x.quantile(0.35))
    in_sample["target"] = 0
    in_sample.loc[in_sample["future_return"] >= upper, "target"] = 1
    in_sample.loc[in_sample["future_return"] <= lower, "target"] = -1
    in_sample = in_sample[in_sample["target"] != 0].dropna(subset=feature_cols)

    if len(in_sample) >= min_rows:
        X_train = in_sample[feature_cols]
        y_train = (in_sample["target"] == 1).astype(int)
        X_oos   = oos[feature_cols]

        rf = RandomForestClassifier(
            n_estimators=200, max_depth=7, min_samples_leaf=8,
            max_features="sqrt", random_state=42, n_jobs=-1,
            class_weight="balanced",
        )
        lr_pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=5000, C=0.5, random_state=42)),
        ])
        xgb = XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.7, min_child_weight=5,
            random_state=42, n_jobs=-1, eval_metric="logloss", verbosity=0,
        )

        rf.fit(X_train, y_train)
        lr_pipe.fit(X_train, y_train)
        xgb.fit(X_train, y_train)

        oos["probability"] = (
            ens_w["xgb"] * xgb.predict_proba(X_oos)[:, 1] +
            ens_w["rf"]  * rf.predict_proba(X_oos)[:, 1]  +
            ens_w["lr"]  * lr_pipe.predict_proba(X_oos)[:, 1]
        )

        logger.info(
            "Ensemble on %d OOS rows. Prob mean=%.3f std=%.3f",
            len(oos), oos["probability"].mean(), oos["probability"].std(),
        )

    # ── Assign signals by daily rank ──────────────────────────────────────────
    return _assign_signals_by_rank(oos, top_n, bottom_n)


def _assign_signals_by_rank(df, top_n: int, bottom_n: int):
    """
    Each day rank stocks by probability (high = expected outperformer).
    Top top_n  -> signal +1  (long)
    Bot bottom_n -> signal -1 (short)  -- 0 means no shorts at all
    """
    df = df.copy()
    df["signal"] = 0

    dates = sorted(df["date"].unique())
    total_long = total_short = 0

    for date in dates:
        mask = df["date"] == date
        day  = df[mask].sort_values("probability", ascending=False)
        n    = len(day)

        if n == 0:
            continue

        actual_top    = min(top_n,    n)
        actual_bottom = min(bottom_n, n)

        # Prevent overlap
        if actual_top + actual_bottom > n:
            actual_top    = n // 2
            actual_bottom = n - actual_top

        long_syms = day.iloc[:actual_top]["symbol"].values

        df.loc[mask & df["symbol"].isin(long_syms), "signal"] = 1

        if actual_bottom > 0:
            short_syms = day.iloc[-actual_bottom:]["symbol"].values
            df.loc[mask & df["symbol"].isin(short_syms), "signal"] = -1
            total_short += actual_bottom

        total_long += actual_top

    n_dates = max(len(dates), 1)
    logger.info(
        "Signals across %d dates. Avg/day: %.1f long, %.1f short.",
        len(dates), total_long / n_dates, total_short / n_dates,
    )

    latest = df["date"].max()
    n_l = (df[df["date"] == latest]["signal"] ==  1).sum()
    n_s = (df[df["date"] == latest]["signal"] == -1).sum()
    logger.info("Latest date %s: %d long, %d short.", latest, n_l, n_s)

    return df