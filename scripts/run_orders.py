# scripts/run_orders.py
from pathlib import Path
import pandas as pd
import numpy as np

from src.portfolio.optimizer import size_from_signal

DATA_SIGNALS = Path("data/signals/signals.parquet")
OUT_ORDERS = Path("data/orders")
OUT_ORDERS.mkdir(parents=True, exist_ok=True)

# Config
PORTFOLIO_VALUE = 1_000_000   # capital in rupees
PER_NAME_CAP = 0.20           # max 20% per name
ROUND_LOT = 1                 # shares per lot (1 for demo)

# Load signals
df = pd.read_parquet(DATA_SIGNALS)
latest_date = df["date"].max()
last = df[df["date"] == latest_date].copy().set_index("symbol")

signals = last["signal"].astype(float).fillna(0.0)

# Compute weights
weights = size_from_signal(signals, cap=PER_NAME_CAP)

# Use close prices for qty calc
prices = last["close"]

orders = []
for sym, w in weights.items():
    price = float(prices[sym])
    if price <= 0 or w == 0:
        continue
    target_value = PORTFOLIO_VALUE * abs(w)
    qty = int(np.floor(target_value / price / ROUND_LOT) * ROUND_LOT)
    if qty == 0:
        continue
    side = "BUY" if w > 0 else "SELL"
    orders.append({
        "date": str(latest_date),
        "symbol": sym,
        "side": side,
        "qty": qty,
        "price": price,
        "weight": float(w),
        "target_value": float(np.sign(w) * target_value)
    })

orders_df = pd.DataFrame(orders)
orders_file = OUT_ORDERS / f"orders_{latest_date.date()}.parquet"
orders_df.to_parquet(orders_file, index=False)

print(f"Saved {len(orders_df)} orders to {orders_file}")
print(orders_df if not orders_df.empty else "No orders generated.")
