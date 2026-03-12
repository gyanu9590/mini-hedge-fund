import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


def train_model(df):

    features = [
        "momentum_5",
        "momentum_10",
        "ma_10",
        "ma_50",
        "volatility_10"
    ]

    df = df.dropna()

    X = df[features]

    # target = future price movement
    df["target"] = (df["close"].shift(-5) > df["close"]).astype(int)

    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestClassifier(n_estimators=200)

    model.fit(X_train, y_train)

    return model
def generate_predictions(df, model):

    features = [
        "momentum_5",
        "momentum_10",
        "ma_10",
        "ma_50",
        "volatility_10"
    ]

    df = df.dropna()

    df["prediction"] = model.predict(df[features])

    return df