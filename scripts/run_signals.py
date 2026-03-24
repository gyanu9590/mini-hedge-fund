"""
scripts/run_signals.py

Generates ML signals and saves TWO files:
  - signals_YYYY-MM-DD.parquet  : today's actionable signals (for orders)
  - signals_history.parquet     : full OOS history (for backtest)
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
        logger.error("Feature file not found. Run run_features.py first.")
        return

    df = pd.read_parquet(feature_file)
    df["symbol"] = (
        df["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    logger.info("Loaded feature data: %s", df.shape)

    df = generate_signals(df)

    if df is None:
        logger.error("Signal generation failed.")
        return

    df["symbol"] = (
        df["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    # ── Save FULL OOS history for backtest ────────────────────────────────────
    history_file = OUT_DIR / "signals_history.parquet"
    df.to_parquet(history_file, index=False)
    logger.info("Full signal history saved -> %s  (%d rows)", history_file, len(df))

    # ── Save LATEST date file for orders ──────────────────────────────────────
    latest_date = pd.to_datetime(df["date"]).max()
    date_str    = latest_date.date()
    out_file    = OUT_DIR / f"signals_{date_str}.parquet"
    df.to_parquet(out_file, index=False)
    logger.info("Latest signals saved -> %s", out_file)

    display_cols = [c for c in ["date", "symbol", "probability", "signal"] if c in df.columns]
    latest_rows  = df[df["date"] == latest_date][display_cols].sort_values("probability", ascending=False)
    print("\n-- Latest signals --")
    print(latest_rows.to_string(index=False))
    print("--------------------\n")


if __name__ == "__main__":
    main()