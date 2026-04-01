import logging
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.research.features import add_features

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/prices")
OUT_DIR  = Path("data/features")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    price_files = sorted(DATA_DIR.glob("*.parquet"))
    if not price_files:
        logger.error("No price parquet files found in data/prices/. Run run_etl.py first.")
        return

    all_frames = []

    for f in price_files:
        sym = f.stem

        df = pd.read_parquet(f)

        if "close" not in df.columns or "date" not in df.columns:
            logger.warning("Skipping %s - missing date/close columns", sym)
            continue

        df["symbol"] = sym
        df = df.sort_values("date").reset_index(drop=True)

        try:
            feat_df = add_features(df)
        except Exception as e:
            logger.warning("Feature generation failed for %s: %s", sym, e)
            continue

        # =========================
        # 🔥 ADD ALPHA FEATURES
        # =========================
        feat_df["momentum_20"] = feat_df["close"] / feat_df["close"].shift(20) - 1
        feat_df["volatility_20"] = feat_df["close"].pct_change().rolling(20).std()
        feat_df["return_skew_20"] = feat_df["close"].pct_change().rolling(20).skew()

        feat_df = feat_df.dropna().reset_index(drop=True)

        feat_df["symbol"] = sym

        sym_out = OUT_DIR / f"{sym}_features.parquet"
        feat_df.to_parquet(sym_out, index=False)

        all_frames.append(feat_df)
        logger.info("%s: %d rows, %d features", sym, len(feat_df), len(feat_df.columns))

    if not all_frames:
        logger.error("No features generated.")
        return

    combined = (
        pd.concat(all_frames, ignore_index=True)
        .sort_values(["symbol", "date"])
        .reset_index(drop=True)
    )

    combined.to_parquet(OUT_DIR / "features.parquet", index=False)

    logger.info(
        "Combined features: %d rows x %d cols",
        len(combined), len(combined.columns)
    )


if __name__ == "__main__":
    main()