import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier


def generate_signals(df):

    df = df.copy()

    # -----------------------
    # CREATE TARGET
    # -----------------------

    df["future_return_5d"] = df["close"].shift(-5) / df["close"] - 1

    df["target"] = np.where(
        df["future_return_5d"] > 0.02,
        1,
        0
    )

    df = df.dropna()

    # -----------------------
    # SELECT FEATURES
    # -----------------------

    feature_cols = [
    col for col in df.columns
    if col not in [
        "date",
        "symbol",
        "target",
        "future_return_5d",
        "close"
    ]
    ]

    print("Using features:", feature_cols)

    X = df[feature_cols]
    y = df["target"]

    # -----------------------
    # TRAIN MODEL
    # -----------------------

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        random_state=42
    )

    # -----------------------
# WALK-FORWARD TRAINING
# -----------------------

    split_index = int(len(df) * 0.8)

    X_train = X.iloc[:split_index]
    y_train = y.iloc[:split_index]

    X_test = X.iloc[split_index:]

    model = RandomForestClassifier(
    n_estimators=200,
    max_depth=6,
    random_state=42
)

# train on past
    model.fit(X_train, y_train)

# predict future
    train_probs = model.predict_proba(X_train)[:, 1]
    test_probs = model.predict_proba(X_test)[:, 1]

    probs = np.concatenate([train_probs, test_probs])

    df["probability"] = probs

    df["probability"] = probs

    # -----------------------
    # GENERATE SIGNALS
    # -----------------------

    # -----------------------
# STOCK RANKING SIGNALS
# -----------------------

    df["signal"] = 0

    latest_date = df["date"].max()

    latest = df[df["date"] == latest_date].copy()

    latest = latest.sort_values("probability", ascending=False)

    top_n = 2
    bottom_n = 2

    top_symbols = latest.head(top_n)["symbol"]
    bottom_symbols = latest.tail(bottom_n)["symbol"]

    df.loc[(df["date"] == latest_date) & (df["symbol"].isin(top_symbols)), "signal"] = 1
    df.loc[(df["date"] == latest_date) & (df["symbol"].isin(bottom_symbols)), "signal"] = -1

    return df