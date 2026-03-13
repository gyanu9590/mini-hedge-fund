import pandas as pd
import os
import glob
import datetime
from src.model.ml_model import generate_signals

FEATURE_DIR = "data/features"
OUTPUT_DIR = "data/signals"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------
# LOAD ALL FEATURE FILES
# ---------------------------------------

files = glob.glob(f"{FEATURE_DIR}/*.parquet")

if len(files) == 0:
    raise Exception("No feature files found. Run feature pipeline first.")

dfs = []

for f in files:
    df = pd.read_parquet(f)
    dfs.append(df)

df = pd.concat(dfs)

print("Loaded feature data:", df.shape)

# ---------------------------------------
# APPLY ML MODEL
# ---------------------------------------

df = generate_signals(df)

print("ML predictions generated")

# ---------------------------------------
# CLEAN SIGNAL TABLE
# ---------------------------------------

signals = df[[
    "date",
    "symbol",
    "probability",
    "signal"
]].copy()

signals = signals.sort_values("date")

signals = signals.groupby("symbol").tail(1)

# ---------------------------------------
# SAVE SIGNAL FILE
# ---------------------------------------

today = datetime.date.today()

file = f"{OUTPUT_DIR}/signals_{today}.parquet"

signals.to_parquet(file)

print("Signals saved to:", file)
print(signals)