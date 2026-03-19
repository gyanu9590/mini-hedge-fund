from pathlib import Path
import pandas as pd
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.model.ml_model import generate_signals

DATA_DIR = Path("data/features")
OUT_DIR = Path("data/signals")

OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():

    rows = []

    # -----------------------
    # LOAD FEATURES
    # -----------------------

    FEATURE_FILE = Path("data/features/features.parquet")

    df = pd.read_parquet(FEATURE_FILE)

    print("Loaded feature data:", df.shape)

        # 🔥 CLEAN SYMBOL
    df["symbol"] = (
            df["symbol"]
            .astype(str)
            .str.replace("NSE_", "")
            .str.replace("NSE:", "")
        )

    rows.append(df)

    if not rows:
        print("❌ No feature files found")
        return

    df = pd.concat(rows).sort_values(["symbol", "date"]).reset_index(drop=True)

    print(f"Loaded feature data: {df.shape}")

    # -----------------------
    # GENERATE SIGNALS
    # -----------------------

    df = generate_signals(df)

    if df is None:
        print("❌ Signal generation failed")
        return

    # 🔥 FINAL CLEAN (important)
    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.replace("NSE_", "")
        .str.replace("NSE:", "")
    )

    # -----------------------
    # SAVE
    # -----------------------

    latest_date = df["date"].max()

    date_str = pd.to_datetime(latest_date).date()

    out_file = OUT_DIR / f"signals_{date_str}.parquet"

    df.to_parquet(out_file, index=False)

    print(f"✅ Signals saved to: {out_file}")
    print(df[["date", "symbol", "probability", "signal"]].tail(20))


if __name__ == "__main__":
    main()