from pathlib import Path
import pandas as pd
import numpy as np

# -----------------------
# LOAD LATEST SIGNAL FILE
# -----------------------

signals_dir = Path("data/signals")
signal_files = sorted(signals_dir.glob("signals_*.parquet"))

if not signal_files:
    raise FileNotFoundError("No signals files found")

DATA_SIGNALS = signal_files[-1]

OUT_ORDERS = Path("data/orders")
OUT_ORDERS.mkdir(parents=True, exist_ok=True)

# -----------------------
# CONFIG
# -----------------------

PORTFOLIO_VALUE = 1_000_000
PER_NAME_CAP = 0.25
ROUND_LOT = 1

# -----------------------
# LOAD DATA
# -----------------------

df = pd.read_parquet(DATA_SIGNALS)

# 🔥 CLEAN SYMBOLS
df["symbol"] = (
    df["symbol"]
    .astype(str)
    .str.replace("NSE_", "")
    .str.replace("NSE:", "")
)

latest_date = pd.to_datetime(df["date"]).max()
df["date"] = pd.to_datetime(df["date"])

latest = df[df["date"] == latest_date].copy()

# remove zero signals
latest = latest[latest["signal"] != 0]

# 🔥 REMOVE DUPLICATES (CRITICAL)
latest = latest.drop_duplicates(subset=["symbol"])

if latest.empty:
    print("No active signals today.")
    exit()

# -----------------------
# POSITION SIZING
# -----------------------

n = len(latest)

latest["weight"] = latest["signal"] / n

latest["weight"] = latest["weight"].clip(-PER_NAME_CAP, PER_NAME_CAP)

# -----------------------
# ORDERS
# -----------------------

orders = []

for _, row in latest.iterrows():

    symbol = row["symbol"]
    weight = row["weight"]

    if "close" not in row or pd.isna(row["close"]):
        continue

    price = float(row["close"])

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

# -----------------------
# SAVE
# -----------------------

orders_df = pd.DataFrame(orders)

date_str = pd.to_datetime(latest_date).date()

orders_file = OUT_ORDERS / f"orders_{latest_date.date()}.parquet"

orders_df.to_parquet(orders_file, index=False)

print(f"✅ Saved {len(orders_df)} orders to {orders_file}")

if not orders_df.empty:
    print(orders_df)
else:
    print("No orders generated.")