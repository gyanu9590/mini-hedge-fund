import logging
import os
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

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
        logger.error("features.parquet not found.")
        return

    df = pd.read_parquet(feature_file)

    df["symbol"] = (
        df["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    logger.info("Loaded features: %s rows", len(df))

    result = generate_signals(df)

    if result is None or len(result) == 0:
        logger.error("Signal generation failed.")
        return

    # =========================
    # 🔥 SIGNAL FILTER
    # =========================
    if "probability" in result.columns:
        result = result[result["probability"] > 0.55]

    result = result.sort_values(["date", "probability"], ascending=[True, False])
    result = result.groupby("date").head(10)

    # =========================
    # 🔥 MARKET FILTER
    # =========================
    try:
        nifty = yf.download("^NSEI", period="6mo")["Close"]
        sma50 = float(nifty.rolling(50).mean().iloc[-1])
        sma200 = float(nifty.rolling(200).mean().iloc[-1])

        if sma50 < sma200:
            logger.info("Bear market → stricter filter")
            result = result[result["probability"] > 0.65]

    except Exception as e:
        logger.warning("Market filter failed: %s", e)

    result["symbol"] = (
        result["symbol"].astype(str)
        .str.replace("NSE_", "", regex=False)
        .str.replace("NSE:", "", regex=False)
    )

    history_file = OUT_DIR / "signals_history.parquet"
    result.to_parquet(history_file, index=False)

    latest_date = pd.to_datetime(result["date"]).max()
    out_file = OUT_DIR / f"signals_{latest_date.date()}.parquet"
    result.to_parquet(out_file, index=False)

    logger.info("Signals saved: %s", out_file)


if __name__ == "__main__":
    main()