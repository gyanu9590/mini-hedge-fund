"""
scripts/run_orders.py

Converts latest signals into sized orders.
Fix: handles both 'probability' and 'prob' column names from different signal formats.
Reads close prices directly from data/prices/ parquets.
"""

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.portfolio.optimizer import size_from_signal, volatility_target

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def _load_cfg():
    with open("configs/settings.yaml") as f:
        return yaml.safe_load(f)


def _get_latest_price(symbol: str, prices_dir: Path):
    for fname in [f"{symbol}.parquet", f"NSE_{symbol}.parquet"]:
        f = prices_dir / fname
        if f.exists():
            px = pd.read_parquet(f)[["date","close"]].sort_values("date")
            if not px.empty:
                return float(px["close"].iloc[-1])
    return None


def main():
    cfg             = _load_cfg()
    PORTFOLIO_VALUE = cfg["portfolio"]["initial_capital"]
    ROUND_LOT       = cfg["portfolio"]["round_lot"]
    MAX_WEIGHT      = cfg["risk"]["max_weight_per_stock"]

    signals_dir  = Path("data/signals")
    signal_files = sorted([
        f for f in signals_dir.glob("signals_*.parquet")
        if "history" not in f.name
    ])

    if not signal_files:
        logger.error("No signals_YYYY-MM-DD.parquet found in data/signals/")
        return

    df = pd.read_parquet(signal_files[-1])
    df["symbol"] = df["symbol"].astype(str).str.replace("NSE_","",regex=False).str.replace("NSE:","",regex=False)

    # Normalize probability column - handle both 'prob' and 'probability'
    if "prob" in df.columns and "probability" not in df.columns:
        df = df.rename(columns={"prob": "probability"})

    latest_date = pd.to_datetime(df["date"]).max()
    df["date"]  = pd.to_datetime(df["date"])
    latest      = df[df["date"] == latest_date].copy()
    latest      = latest[latest["signal"] != 0].drop_duplicates(subset=["symbol"])

    if latest.empty:
        logger.warning("No active signals on %s", latest_date.date())
        return

    logger.info("Active signals on %s: %d", latest_date.date(), len(latest))

    prices_dir     = Path("data/prices")
    returns_frames = {}
    for sym in latest["symbol"].unique():
        for fname in [f"{sym}.parquet", f"NSE_{sym}.parquet"]:
            f = prices_dir / fname
            if f.exists():
                px = pd.read_parquet(f)[["date","close"]].sort_values("date")
                returns_frames[sym] = px["close"].pct_change().dropna()
                break

    if returns_frames:
        min_len = min(len(v) for v in returns_frames.values())
        aligned = pd.DataFrame({k: v.values[-min_len:] for k, v in returns_frames.items()})
    else:
        aligned = None

    signal_series = latest.set_index("symbol")["signal"]
    weights       = size_from_signal(signal_series, returns=aligned, cap=MAX_WEIGHT)

    if aligned is not None and len(aligned) > 20:
        port_rets  = aligned.mean(axis=1)
        vol_scalar = volatility_target(port_rets)
        weights    = (weights * vol_scalar).clip(-MAX_WEIGHT, MAX_WEIGHT)
        logger.info("Vol-target scalar: %.2f", vol_scalar)

    orders = []
    for sym, weight in weights.items():
        price = _get_latest_price(sym, prices_dir)
        if price is None or price <= 0:
            logger.warning("No price for %s - skipping.", sym)
            continue

        target_value = PORTFOLIO_VALUE * abs(weight)
        qty = int(np.floor(target_value / price / ROUND_LOT) * ROUND_LOT)
        if qty <= 0:
            continue

        prob_col = latest[latest["symbol"] == sym]["probability"] if "probability" in latest.columns else pd.Series([0.0])
        prob = float(prob_col.iloc[0]) if not prob_col.empty else 0.0

        orders.append({
            "date":         str(latest_date.date()),
            "symbol":       sym,
            "side":         "BUY" if weight > 0 else "SELL",
            "qty":          qty,
            "price":        price,
            "weight":       float(weight),
            "target_value": float(np.sign(weight) * target_value),
            "probability":  prob,
        })

    if not orders:
        logger.warning("No orders generated.")
        return

    orders_df = pd.DataFrame(orders)
    out_dir   = Path("data/orders")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file  = out_dir / f"orders_{latest_date.date()}.parquet"
    orders_df.to_parquet(out_file, index=False)

    logger.info("Saved %d orders -> %s", len(orders_df), out_file)
    print(orders_df.to_string(index=False))


if __name__ == "__main__":
    main()