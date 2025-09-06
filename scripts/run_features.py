from pathlib import Path
import pandas as pd
import duckdb
from src.research.features import add_features

DATA_DIR = Path("data/prices")
OUT_DIR = Path("data/features")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Read all parquet into one DataFrame (symbol inferred from filename)
rows = []
for f in DATA_DIR.glob("*.parquet"):
    sym = f.stem.replace("_", ":")
    df = pd.read_parquet(f)
    df["symbol"] = sym
    rows.append(df)
prices = pd.concat(rows).sort_values(["symbol","date"]).reset_index(drop=True)

# Add features per symbol
# inside scripts/run_features.py where you compute features
features = (
    prices
    .groupby("symbol", group_keys=False, sort=False)
    .apply(lambda g: add_features(g.drop(columns=["symbol"])).assign(symbol=g.name))
    .reset_index(drop=True)
)



# Save per symbol for fast loading
for sym, g in features.groupby("symbol"):
    out = OUT_DIR / f"{sym.replace(':','_')}_features.parquet"
    g.to_parquet(out)
print("Features written to", OUT_DIR)
def add_features(df):
    df = df.sort_values('date').copy()
    df['ret_1'] = df['close'].pct_change()
    # use min_periods=1 so early rows are computed (but be careful interpreting small-sample z)
    df['ma_20'] = df['close'].rolling(20, min_periods=1).mean()
    df['std_20'] = df['close'].rolling(20, min_periods=1).std(ddof=0).replace(0, 1e-9)
    df['z_20'] = (df['close'] - df['ma_20']) / df['std_20']
    return df

