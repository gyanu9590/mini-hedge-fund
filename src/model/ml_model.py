import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def generate_signals(df):

    features = []

    possible_features = [
    "returns",
    "momentum_5",
    "momentum_10",
    "ma_5",
    "ma_10",
    "sma_5",
    "sma_10"
]

    for f in possible_features:
        if f in df.columns:
            features.append(f)

    print("Using features:", features)

    X = df[features]

    df = df.dropna()

    # -----------------------
    # CREATE TARGET
    # -----------------------

    df["future_return"] = df["returns"].shift(-1)

    df["target"] = np.where(
        df["future_return"] > 0,
        1,
        0
    )

    df = df.dropna()

    X = df[features]
    y = df["target"]

    # -----------------------
    # TRAIN MODEL
    # -----------------------

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        random_state=42
    )

    model.fit(X, y)

    # -----------------------
    # PREDICT
    # -----------------------

    probs = model.predict_proba(X)[:,1]

    df["probability"] = probs

    # -----------------------
    # SIGNAL RULE
    # -----------------------

    df["signal"] = np.where(
        df["probability"] > 0.6,
        1,
        np.where(
            df["probability"] < 0.4,
            -1,
            0
        )
    )

    return df