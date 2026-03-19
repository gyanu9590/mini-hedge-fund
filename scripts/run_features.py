from pathlib import Path
import pandas as pd
import sys
import os

# -----------------------
# PATH SETUP
# -----------------------

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.research.features import add_features

DATA_DIR = Path("data/prices")
OUT_DIR = Path("data/features")


def main():

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    # -----------------------
    # LOAD PRICE DATA
    # -----------------------

    for f in DATA_DIR.glob("*.parquet"):

        # 🔥 CLEAN SYMBOL
        sym = f.stem.replace("NSE_", "").replace("NSE:", "")

        df = pd.read_parquet(f)
        df["symbol"] = sym

        rows.append(df)

    if not rows:
        print("❌ No price data found")
        return

    prices = pd.concat(rows).sort_values(["symbol", "date"]).reset_index(drop=True)

    # -----------------------
    # FEATURE ENGINEERING
    # -----------------------

    features = (
        prices.groupby("symbol", group_keys=False)
        .apply(lambda g: add_features(g.drop(columns=["symbol"])))
        .reset_index(drop=True)
    )

    # attach symbol properly
    features["symbol"] = prices["symbol"].values[:len(features)]

    # -----------------------
    # SAVE FEATURES
    # -----------------------

    out = OUT_DIR / "features.parquet"
    features.to_parquet(out, index=False)

    print("✅ Features saved to single file")

    print("✅ Features generated cleanly")


if __name__ == "__main__":
    main()