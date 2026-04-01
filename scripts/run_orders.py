import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def _load_cfg():
    with open("configs/settings.yaml") as f:
        return yaml.safe_load(f)


def _get_latest_price(symbol: str, prices_dir: Path):
    f = prices_dir / f"{symbol}.parquet"
    if f.exists():
        px = pd.read_parquet(f)["close"]
        return float(px.iloc[-1])
    return None


def main():
    cfg = _load_cfg()
    PORTFOLIO_VALUE = cfg["portfolio"]["initial_capital"]
    ROUND_LOT = cfg["portfolio"]["round_lot"]
    MAX_WEIGHT = cfg["risk"]["max_weight_per_stock"]

    signals_dir = Path("data/signals")
    signal_files = sorted(signals_dir.glob("signals_*.parquet"))

    if not signal_files:
        logger.error("No signals found")
        return

    df = pd.read_parquet(signal_files[-1])

    latest_date = pd.to_datetime(df["date"]).max()
    latest = df[df["date"] == latest_date].copy()

    # =========================
    # 🔥 SMART WEIGHTING
    # =========================

    latest["confidence"] = (latest["probability"] - 0.5).clip(lower=0)
    latest = latest[latest["confidence"] > 0.05]

    latest = latest.sort_values("probability", ascending=False).head(5)

    latest["conf_weight"] = latest["confidence"] / latest["confidence"].sum()

    # =========================
    # 🔥 VOLATILITY
    # =========================

    prices_dir = Path("data/prices")
    vol_dict = {}

    for sym in latest["symbol"]:
        f = prices_dir / f"{sym}.parquet"
        if f.exists():
            px = pd.read_parquet(f)["close"]
            vol = px.pct_change().rolling(20).std().iloc[-1]
            vol_dict[sym] = vol if vol > 0 else 0.02
        else:
            vol_dict[sym] = 0.02

    latest["volatility"] = latest["symbol"].map(vol_dict)
    latest["vol_weight"] = 1 / latest["volatility"]

    latest["raw_weight"] = latest["conf_weight"] * latest["vol_weight"]
    latest["weight"] = latest["raw_weight"] / latest["raw_weight"].sum()

    latest["weight"] = latest["weight"].clip(upper=MAX_WEIGHT)
    latest["weight"] = latest["weight"] / latest["weight"].sum()

    # =========================
    # 🔥 ORDER GENERATION
    # =========================

    orders = []

    for _, row in latest.iterrows():
        price = _get_latest_price(row["symbol"], prices_dir)
        if price is None:
            continue

        target_value = PORTFOLIO_VALUE * row["weight"]
        qty = int(target_value / price / ROUND_LOT) * ROUND_LOT

        if qty <= 0:
            continue

        orders.append({
            "date": str(latest_date.date()),
            "symbol": row["symbol"],
            "side": "BUY",
            "qty": qty,
            "price": price,
            "weight": row["weight"],
            "target_value": target_value,
            "probability": row["probability"],
        })

    if not orders:
        logger.warning("No orders generated")
        return

    orders_df = pd.DataFrame(orders)

    out_dir = Path("data/orders")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"orders_{latest_date.date()}.parquet"
    orders_df.to_parquet(out_file, index=False)

    logger.info("Orders saved: %s", out_file)
    print(orders_df)


if __name__ == "__main__":
    main()