# scripts/run_orders.py

from pathlib import Path
import pandas as pd
import numpy as np

# -----------------------------
# LOAD LATEST SIGNALS FILE
# -----------------------------

signals_dir = Path("data/signals")
signal_files = sorted(signals_dir.glob("signals_*.parquet"))

if not signal_files:
    raise FileNotFoundError("No signals files found")

DATA_SIGNALS = signal_files[-1]

OUT_ORDERS = Path("data/orders")
OUT_ORDERS.mkdir(parents=True, exist_ok=True)

PRICES_DIR = Path("data/prices")


# -----------------------------
# CONFIG
# -----------------------------

PORTFOLIO_VALUE = 1_000_000
PER_NAME_CAP = 0.25
ROUND_LOT = 1


# -----------------------------
# LOAD SIGNALS
# -----------------------------

df = pd.read_parquet(DATA_SIGNALS)

latest_date = df["date"].max()

latest = df[df["date"] == latest_date].copy()

signals = latest[latest["signal"] != 0].copy()

if signals.empty:
    print("No active signals today.")
    exit()


# -----------------------------
# PORTFOLIO WEIGHTS
# -----------------------------

n = len(signals)

signals["weight"] = signals["signal"] / n

signals["weight"] = signals["weight"].clip(-PER_NAME_CAP, PER_NAME_CAP)


# -----------------------------
# ORDER GENERATION
# -----------------------------

orders = []

for _, row in signals.iterrows():

    symbol = row["symbol"]
    weight = row["weight"]

    # convert symbol name to file name
    price_file = PRICES_DIR / f"{symbol.replace(':', '_')}.parquet"

    if not price_file.exists():
        continue

    price_df = pd.read_parquet(price_file)

    latest_price = price_df.iloc[-1]["close"]

    price = float(latest_price)

    if price <= 0:
        continue

    target_value = PORTFOLIO_VALUE * abs(weight)

    qty = int(np.floor(target_value / price / ROUND_LOT) * ROUND_LOT)

    if qty <= 0:
        continue

    side = "BUY" if weight > 0 else "SELL"

    orders.append({
        "date": str(latest_date),
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "weight": float(weight),
        "target_value": float(np.sign(weight) * target_value)
    })


# -----------------------------
# SAVE ORDERS
# -----------------------------

orders_df = pd.DataFrame(orders)

orders_file = OUT_ORDERS / f"orders_{latest_date.date()}.parquet"

orders_df.to_parquet(orders_file, index=False)

print(f"Saved {len(orders_df)} orders to {orders_file}")

if not orders_df.empty:
    print(orders_df)
else:
    print("No orders generated.")