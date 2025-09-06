# scripts/run_backtest.py
import pandas as pd
from pathlib import Path
from src.backtest.engine import Backtester

DATA_FEATURES = Path("data/features")
DATA_SIGNALS = Path("data/signals/signals.parquet")

# Load prices (from features parquet files)
price_frames = []
for f in DATA_FEATURES.glob("*_features.parquet"):
    df = pd.read_parquet(f)[["date","symbol","close"]]
    price_frames.append(df)
prices = pd.concat(price_frames)

# Load signals
signals = pd.read_parquet(DATA_SIGNALS)[["date","symbol","signal"]]

# Run backtest
bt = Backtester(fees_bps=1.0, slippage_bps=1.0)
equity, metrics = bt.run(prices, signals)

print("Performance metrics:", metrics)

# Save equity curve
out_file = Path("reports")
out_file.mkdir(parents=True, exist_ok=True)
equity.to_csv(out_file / "equity_curve.csv", index=False)
print("Equity curve saved to reports/equity_curve.csv")
