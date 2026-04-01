"""
scripts/run_etl.py

Smart ETL that works at ANY time of day.
- Market open  (9:15–3:30 IST): uses 5-min live intraday bars
- Market closed (after 3:30 IST): uses daily close as normal
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.data.live_market import fetch_symbol, is_market_open, is_market_closed_today

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/prices")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def main():
    with open("configs/settings.yaml") as f:
        cfg = yaml.safe_load(f)

    symbols    = cfg["universe"]
    start_date = cfg["data"]["start_date"]

    # Determine mode
    if is_market_open():
        mode = "LIVE (market open — using 5-min intraday bars)"
    elif is_market_closed_today():
        mode = "DAILY (market closed — using today's final close)"
    else:
        mode = "PRE-MARKET (using yesterday's close)"

    logger.info("ETL mode: %s", mode)
    logger.info("Universe: %d symbols | history from %s", len(symbols), start_date)

    # Delete stale feature/signal files so downstream rebuilds cleanly
    for stale_dir in ["data/features", "data/signals"]:
        for f in Path(stale_dir).glob("*.parquet"):
            f.unlink()

    success = 0
    failed  = []

    for symbol in symbols:
        clean_sym = symbol.replace("NSE:", "").strip()
        logger.info("Fetching %s ...", clean_sym)

        df = fetch_symbol(clean_sym, start_date, DATA_DIR)

        if df is None or df.empty:
            logger.warning("  FAILED: %s", clean_sym)
            failed.append(clean_sym)
            continue

        # Save parquet + CSV
        df.to_parquet(DATA_DIR / f"{clean_sym}.parquet", index=False)
        df.to_csv(DATA_DIR / f"{clean_sym}.csv", index=False)

        logger.info("  Saved %d rows -> %s (latest: %s @ %.2f)",
                    len(df), clean_sym,
                    str(df["date"].iloc[-1])[:10],
                    float(df["close"].iloc[-1]))
        success += 1

    logger.info("ETL complete: %d/%d symbols.", success, len(symbols))
    if failed:
        logger.warning("Failed: %s", ", ".join(failed))


if __name__ == "__main__":
    main()