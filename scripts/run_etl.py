"""
scripts/run_etl.py

Downloads OHLCV for every symbol in configs/settings.yaml.
Reads start_date / end_date from config - does NOT hardcode dates.
"""

import logging
import os
import sys
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
    end_date   = cfg["data"]["end_date"]

    logger.info("ETL: %d symbols from %s to %s", len(symbols), start_date, end_date)

    for symbol in symbols:
        clean_sym = symbol.replace("NSE:", "").strip()
        yf_sym    = clean_sym + ".NS"

        logger.info("Downloading %s  (%s to %s)...", yf_sym, start_date, end_date)

        try:
            df = yf.download(yf_sym, start=start_date, end=end_date, progress=False)
        except Exception as e:
            logger.warning("Download failed for %s: %s", yf_sym, e)
            continue

        if df.empty:
            logger.warning("No data returned for %s.", yf_sym)
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index().rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })

        cols = [c for c in ["date","open","high","low","close","volume"] if c in df.columns]
        df   = df[cols].copy()
        df["symbol"] = clean_sym

        out = DATA_DIR / f"{clean_sym}.parquet"
        df.to_parquet(out, index=False)
        logger.info("  Saved %d rows -> %s", len(df), out)

    logger.info("ETL complete. Files in %s", DATA_DIR)


if __name__ == "__main__":
    main()