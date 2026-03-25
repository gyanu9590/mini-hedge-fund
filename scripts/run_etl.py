"""
scripts/run_etl.py

Downloads OHLCV for every symbol in configs/settings.yaml.
end_date defaults to TODAY so data is always current.
Deletes old stale feature/signal files to force a clean rebuild.
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/prices")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def main():
    with open("configs/settings.yaml") as f:
        cfg = yaml.safe_load(f)

    symbols    = cfg["universe"]
    start_date = cfg["data"]["start_date"]
    end_date   = cfg["data"].get("end_date", "today")

    # Always use today as end date for real-time data
    if end_date == "today" or not end_date:
        end_date = str(date.today())

    logger.info("ETL: %d symbols | %s to %s", len(symbols), start_date, end_date)

    # Delete stale feature/signal files so downstream steps rebuild cleanly
    for stale_dir in ["data/features", "data/signals"]:
        for f in Path(stale_dir).glob("*.parquet"):
            f.unlink()
            logger.info("Deleted stale file: %s", f)

    success = 0
    for symbol in symbols:
        clean_sym = symbol.replace("NSE:", "").strip()
        yf_sym    = clean_sym + ".NS"

        logger.info("Downloading %s ...", yf_sym)

        try:
            df = yf.download(yf_sym, start=start_date, end=end_date, progress=False)
        except Exception as e:
            logger.warning("Download failed for %s: %s", yf_sym, e)
            continue

        if df.empty:
            logger.warning("No data for %s", yf_sym)
            continue

        # Flatten MultiIndex columns (yfinance quirk)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index().rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })

        cols = [c for c in ["date","open","high","low","close","volume"] if c in df.columns]
        df   = df[cols].copy()
        df["symbol"] = clean_sym

        # Save parquet (primary)
        out_pq = DATA_DIR / f"{clean_sym}.parquet"
        df.to_parquet(out_pq, index=False)

        # Save CSV (for dashboard candlestick chart)
        out_csv = DATA_DIR / f"{clean_sym}.csv"
        df.to_csv(out_csv, index=False)

        logger.info("  Saved %d rows -> %s", len(df), clean_sym)
        success += 1

    logger.info("ETL complete: %d/%d symbols downloaded.", success, len(symbols))


if __name__ == "__main__":
    main()