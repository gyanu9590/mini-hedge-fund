from pathlib import Path
import pandas as pd
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)
from src.research.features import add_features

DATA_DIR = Path("data/prices")
OUT_DIR = Path("data/features")

def main():

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for f in DATA_DIR.glob("*.parquet"):
        sym = f.stem.replace("_", ":")
        df = pd.read_parquet(f)
        df["symbol"] = sym
        rows.append(df)

    prices = pd.concat(rows).sort_values(["symbol","date"])

    features = (
        prices.groupby("symbol", group_keys=False)
        .apply(lambda g: add_features(g.drop(columns=["symbol"])).assign(symbol=g.name))
        .reset_index(drop=True)
    )

    for sym, g in features.groupby("symbol"):
        out = OUT_DIR / f"{sym.replace(':','_')}_features.parquet"
        g.to_parquet(out)

    print("Features generated")


if __name__ == "__main__":
    main()