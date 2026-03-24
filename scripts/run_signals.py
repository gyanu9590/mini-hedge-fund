import pandas as pd
import numpy as np
from xgboost import XGBClassifier

# =========================
# LOAD DATA
# =========================

df = pd.read_parquet("data/features/features.parquet")
df = df.sort_values(["date", "symbol"]).dropna()

features = [
    "returns", "momentum_5", "momentum_10",
    "volatility", "rsi", "ma_20", "ma_50"
]

# =========================
# TIME-BASED SPLIT
# =========================

split_date = df["date"].quantile(0.8)

train = df[df["date"] <= split_date]
test = df[df["date"] > split_date].copy()

X_train = train[features]
y_train = train["target"]

X_test = test[features]

# =========================
# MODEL (STRONGER)
# =========================

model = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# Predictions
test["prob"] = model.predict_proba(X_test)[:, 1]

# =========================
# 🔥 ADVANCED SIGNAL LOGIC
# =========================

def generate_signals(df):
    signals = []

    for date, group in df.groupby("date"):

        # 🧠 TREND FILTER
        group = group.copy()
        group["trend"] = group["close"] > group["ma_50"]

        # LONG: strong prob + uptrend
        longs = group[
            (group["prob"] > 0.65) &
            (group["trend"] == True)
        ].sort_values("prob", ascending=False).head(3)

        # SHORT: strong negative + downtrend
        shorts = group[
            (group["prob"] < 0.35) &
            (group["trend"] == False)
        ].sort_values("prob").head(3)

        if not longs.empty:
            longs["signal"] = 1

        if not shorts.empty:
            shorts["signal"] = -1

        daily = pd.concat([longs, shorts])

        if not daily.empty:
            signals.append(daily)

    if len(signals) == 0:
        return pd.DataFrame()

    return pd.concat(signals)

# Generate signals
signals = generate_signals(test)

# =========================
# SAFETY CHECK
# =========================

if signals.empty:
    raise ValueError("❌ No signals generated — adjust thresholds")

signals = signals[["date", "symbol", "prob", "signal"]]

signals.to_parquet("data/signals/signals.parquet")

print("✅ Signals generated")
print(signals.head())