"""
scripts/run_signals.py

Loads features → generates ML signals via src/model/ml_model.py
Saves TWO files:
  - signals_history.parquet : full OOS history (for backtest)
  - signals_YYYY-MM-DD.parquet : latest date only (for orders)

Key fix: calls ml_model.generate_signals() instead of inline XGBoost.
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.model.ml_model import generate_signals

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path("data/signals")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    feature_file = Path("data/features/features.parquet")
    if not feature_file.exists():
        logger.error("features.parquet not found. Run run_features.py first.")
        return

    df = pd.read_parquet(feature_file)

    # Normalize symbol names
    df["symbol"] = (
        df["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    logger.info("Loaded features: %s rows, %s cols, date range %s to %s",
                len(df), len(df.columns),
                df["date"].min(), df["date"].max())

    result = generate_signals(df)

    if result is None or len(result) == 0:
        logger.error("Signal generation returned nothing.")
        return

    # Normalize symbol names in output
    result["symbol"] = (
        result["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    # Save full OOS history for backtest
    history_file = OUT_DIR / "signals_history.parquet"
    result.to_parquet(history_file, index=False)
    logger.info("Signal history: %d rows -> %s", len(result), history_file)

    # Save latest-date file for orders
    latest_date = pd.to_datetime(result["date"]).max()
    out_file    = OUT_DIR / f"signals_{latest_date.date()}.parquet"
    result.to_parquet(out_file, index=False)
    logger.info("Latest signals -> %s", out_file)

    # Print latest signals table
    display_cols = [c for c in ["date","symbol","probability","signal"] if c in result.columns]
    latest_rows  = (
        result[result["date"] == latest_date][display_cols]
        .sort_values("probability", ascending=False)
    )
    print("\n-- Today's Signals --")
    print(latest_rows.to_string(index=False))
    print("---------------------\n")


if __name__ == "__main__":
    main()