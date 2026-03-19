import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier


def walk_forward_training(df):

    try:
        df = df.sort_values("date").copy()

        # -----------------------
        # CREATE TARGET
        # -----------------------

        df["future_return_5d"] = df["close"].shift(-5) / df["close"] - 1
        df["target"] = np.where(df["future_return_5d"] > 0.02, 1, 0)

        df = df.dropna().reset_index(drop=True)

        feature_cols = [
            col for col in df.columns
            if col not in ["date", "symbol", "target", "future_return_5d", "close"]
        ]

        # -----------------------
        # SIMPLE FAST WALK-FORWARD
        # -----------------------

        train_size = int(len(df) * 0.7)

        train_df = df.iloc[:train_size]
        test_df = df.iloc[train_size:]

        if len(test_df) == 0:
            raise ValueError("No test data")

        X_train = train_df[feature_cols]
        y_train = train_df["target"]

        X_test = test_df[feature_cols]

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)

        test_probs = model.predict_proba(X_test)[:, 1]

        train_df = train_df.copy()
        test_df = test_df.copy()

        train_df.loc[:, "probability"] = model.predict_proba(X_train)[:, 1]
        test_df.loc[:, "probability"] = test_probs

        result = pd.concat([train_df, test_df]).sort_values("date")

        return result

    except Exception as e:

        print("⚠️ Walk-forward failed:", str(e))
        print("⚡ Using fallback model")

        # -----------------------
        # FALLBACK MODEL (ALWAYS WORKS)
        # -----------------------

        df = df.copy()

        df["future_return_5d"] = df["close"].shift(-5) / df["close"] - 1
        df["target"] = np.where(df["future_return_5d"] > 0.02, 1, 0)

        df = df.dropna()

        feature_cols = [
            col for col in df.columns
            if col not in ["date", "symbol", "target", "future_return_5d", "close"]
        ]

        X = df[feature_cols]
        y = df["target"]

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X, y)

        df["probability"] = model.predict_proba(X)[:, 1]

        return df