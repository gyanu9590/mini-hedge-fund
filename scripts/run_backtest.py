import pandas as pd
import numpy as np

# =========================
# LOAD DATA
# =========================

signals = pd.read_parquet("data/signals/signals.parquet")
features = pd.read_parquet("data/features/features.parquet")

# =========================
# MERGE
# =========================

df = signals.merge(features, on=["date", "symbol"], how="left")

# =========================
# FIX PRICE COLUMN
# =========================

if "close" in df.columns:
    price_col = "close"
elif "close_x" in df.columns:
    price_col = "close_x"
elif "close_y" in df.columns:
    price_col = "close_y"
else:
    raise ValueError(f"No close column found. Columns: {df.columns}")

print(f"✅ Using price column: {price_col}")

df = df.dropna(subset=[price_col])
df = df.sort_values("date")

# =========================
# PARAMETERS
# =========================

initial_capital = 1_000_000
capital = initial_capital

positions = {}   # {symbol: (entry_price, direction, entry_date)}
portfolio_values = []

stop_loss = 0.10
take_profit = 0.15
position_size = 0.1
max_positions = 5

# =========================
# BACKTEST LOOP
# =========================

for date, day_data in df.groupby("date"):

    # =========================
    # 1. UPDATE EXISTING POSITIONS
    # =========================
    for symbol in list(positions.keys()):

        entry_price, direction, entry_date = positions[symbol]

        current_row = day_data[day_data["symbol"] == symbol]

        if current_row.empty:
            continue

        current_price = current_row[price_col].values[0]

        pnl = (current_price - entry_price) / entry_price

        if direction == -1:
            pnl = -pnl

        # Holding period check
        holding_days = (date - entry_date).days
        if holding_days < 3:
            continue

        # Exit condition
        if pnl <= -stop_loss or pnl >= take_profit:
            trade_return = position_size * pnl
            capital += capital * trade_return

            del positions[symbol]

    # =========================
    # 2. OPEN NEW POSITIONS
    # =========================
    for _, row in day_data.iterrows():

        symbol = row["symbol"]
        signal = row["signal"]
        price = row[price_col]

        if signal == 0:
            continue

        if symbol not in positions and len(positions) < max_positions:
            positions[symbol] = (price, signal, date)

    # =========================
    # 3. TRACK PORTFOLIO
    # =========================
    portfolio_values.append(capital)

# =========================
# METRICS
# =========================

portfolio_values = pd.Series(portfolio_values)
returns = portfolio_values.pct_change().dropna()

cagr = (portfolio_values.iloc[-1] / initial_capital) ** (252 / len(portfolio_values)) - 1

sharpe = 0
if returns.std() != 0:
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252)

rolling_max = portfolio_values.cummax()
drawdown = (portfolio_values - rolling_max) / rolling_max
max_dd = drawdown.min()

# =========================
# OUTPUT
# =========================

print("\n===== PERFORMANCE =====")
print(f"CAGR: {cagr:.4f}")
print(f"Sharpe: {sharpe:.4f}")
print(f"Max Drawdown: {max_dd:.4f}")
print(f"Final Capital: {portfolio_values.iloc[-1]:.2f}")