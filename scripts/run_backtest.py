"""
scripts/run_backtest.py

Runs backtest using the FULL signal history (signals_history.parquet),
not just today's signals. This gives meaningful multi-year performance metrics.
"""

import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.backtest.engine import Backtester

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def main():
    with open("configs/settings.yaml") as f:
        cfg = yaml.safe_load(f)

    initial_capital = cfg["portfolio"]["initial_capital"]
    fees_bps        = cfg["backtest"]["fees_bps"]
    slippage_bps    = cfg["backtest"]["slippage_bps"]
    stop_loss_pct   = cfg["risk"]["stop_loss_pct"]

    # ── Load prices from per-symbol parquets in data/prices/ ─────────────────
    price_frames = []
    prices_dir   = Path("data/prices")
    for f in prices_dir.glob("*.parquet"):
        sym = f.stem.replace("NSE_", "").replace("NSE:", "")
        px  = pd.read_parquet(f)
        if "close" not in px.columns:
            continue
        if "date" not in px.columns:
            px = px.reset_index()
        px["symbol"] = sym
        price_frames.append(px[["date", "symbol", "close"]])

    if not price_frames:
        logger.error("No price data found in data/prices/")
        return

    prices = pd.concat(price_frames, ignore_index=True)
    prices["date"] = pd.to_datetime(prices["date"])
    prices["symbol"] = (
        prices["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    # ── Load FULL signal history for a proper multi-year backtest ─────────────
    history_file = Path("data/signals/signals_history.parquet")
    if not history_file.exists():
        # Fallback: use latest dated file
        dated = sorted(
            [f for f in Path("data/signals").glob("signals_*.parquet") if "history" not in f.name]
        )
        if not dated:
            logger.error("No signal files found. Run run_signals.py first.")
            return
        history_file = dated[-1]
        logger.warning("signals_history.parquet not found, using %s", history_file.name)

    signals = pd.read_parquet(history_file)[["date", "symbol", "signal"]]
    signals["date"] = pd.to_datetime(signals["date"])
    signals["symbol"] = (
        signals["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    logger.info(
        "Backtest: %d signal rows, %d price rows, date range %s to %s",
        len(signals), len(prices),
        signals["date"].min().date(), signals["date"].max().date(),
    )

    # ── Run backtest ──────────────────────────────────────────────────────────
    bt = Backtester(fees_bps=fees_bps, slippage_bps=slippage_bps)
    equity, metrics = bt.run(
        prices, signals,
        initial_capital=initial_capital,
        apply_stops=True,
        stop_loss_pct=stop_loss_pct,
    )

    # ── Save results ──────────────────────────────────────────────────────────
    out = Path("reports")
    out.mkdir(parents=True, exist_ok=True)
    equity.to_csv(out / "equity_curve.csv", index=False)
    with open(out / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Equity curve saved -> reports/equity_curve.csv")
    logger.info("Metrics saved      -> reports/metrics.json")

    print("\n-- Performance Metrics --")
    for k, v in metrics.items():
        print(f"  {k:<16} {v:.4f}")
    print("-------------------------\n")


if __name__ == "__main__":
    main()