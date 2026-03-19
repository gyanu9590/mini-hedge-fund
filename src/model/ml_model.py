import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.backtest.walkforward import walk_forward_training


def generate_signals(df):

    # -----------------------
    # WALK-FORWARD TRAINING
    # -----------------------

    df = walk_forward_training(df)

    if df is None or len(df) == 0:
        print("❌ Model failed completely")
        return None

    df = df.copy()

    # -----------------------
    # FEATURE SELECTION
    # -----------------------

    feature_cols = [
        col for col in df.columns
        if col not in [
            "date",
            "symbol",
            "target",
            "future_return_5d",
            "future_return_10d",
            "probability"
        ]
    ]

    print("Using features:", feature_cols)

    # -----------------------
    # CLEAN DATA
    # -----------------------

    df = df.dropna().reset_index(drop=True)

    X = df[feature_cols]
    y = df["target"]

    # -----------------------
    # MODELS
    # -----------------------

    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=6,
        random_state=42,
        n_jobs=-1
    )

    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=3000))
    ])

    xgb = XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        eval_metric="logloss"
    )

    # -----------------------
    # TRAIN
    # -----------------------

    rf.fit(X, y)
    lr_pipeline.fit(X, y)
    xgb.fit(X, y)

    # -----------------------
    # PREDICT
    # -----------------------

    rf_prob = rf.predict_proba(X)[:, 1]
    lr_prob = lr_pipeline.predict_proba(X)[:, 1]
    xgb_prob = xgb.predict_proba(X)[:, 1]

    # -----------------------
    # ENSEMBLE
    # -----------------------

    df["probability"] = (
        0.5 * xgb_prob +
        0.3 * rf_prob +
        0.2 * lr_prob
    )

    # -----------------------
    # SIGNAL GENERATION (FIXED)
    # -----------------------

    df["signal"] = 0

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date].copy()

    # 🔥 ALWAYS SORT (NO FILTERING)
    latest = latest.sort_values("probability", ascending=False)

    # -----------------------
    # ALWAYS TRADE (IMPORTANT)
    # -----------------------

    top_n = 3
    bottom_n = 3

    # safety if less stocks
    top_n = min(top_n, len(latest))
    bottom_n = min(bottom_n, len(latest))

    top_symbols = latest.head(top_n)["symbol"]
    bottom_symbols = latest.tail(bottom_n)["symbol"]

    # -----------------------
    # ASSIGN SIGNALS
    # -----------------------

    df.loc[
        (df["date"] == latest_date) & (df["symbol"].isin(top_symbols)),
        "signal"
    ] = 1

    df.loc[
        (df["date"] == latest_date) & (df["symbol"].isin(bottom_symbols)),
        "signal"
    ] = -1

    return df