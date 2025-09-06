# scripts/run_signals.py
from pathlib import Path
import pandas as pd
import numpy as np

DATA_IN = Path("data/features")
OUT = Path("data/signals")
OUT.mkdir(parents=True, exist_ok=True)

# Demo-friendly config (use stricter values for production)
UPPER, LOWER = 0.5, -0.5   # demo thresholds; change to 1.0/-1.0 for production
SMOOTH_WINDOW = 3
MOMENTUM_LAG = 5
FALLBACK_SCALE = 0.3       # fallback momentum strength when z-score absent

all_frames = []
for f in DATA_IN.glob("*_features.parquet"):
    df = pd.read_parquet(f).sort_values("date").copy()
    # ensure expected columns present
    if "z_20" not in df.columns or "close" not in df.columns:
        continue

    # primary mean-reversion by z-score
    df["signal"] = 0.0
    df.loc[df["z_20"] <= LOWER, "signal"] = +1.0
    df.loc[df["z_20"] >= UPPER, "signal"] = -1.0

    # smoothing
    df["signal"] = df["signal"].rolling(SMOOTH_WINDOW, min_periods=1).mean().fillna(0.0)

    # fallback momentum: weak signal if z-score yields zero
    momentum = df["close"] / df["close"].shift(MOMENTUM_LAG) - 1
    fallback = momentum.clip(-1, 1) * FALLBACK_SCALE
    df["signal"] = df["signal"].where(df["signal"].abs() > 0, fallback)
    df["signal"] = df["signal"].clip(-1, 1)

    # keep minimal fields for downstream
    df_out = df[["date", "symbol", "close", "z_20", "signal"]]
    all_frames.append(df_out)

if all_frames:
    out_df = pd.concat(all_frames).sort_values(["date", "symbol"]).reset_index(drop=True)
    out_df.to_parquet(OUT / "signals.parquet", index=False)
    print("Signals saved to", OUT / "signals.parquet")
else:
    print("No feature files found; no signals written.")
