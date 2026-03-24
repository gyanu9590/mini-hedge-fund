"""
scripts/run_features.py

Reads per-symbol price parquets, generates features, saves
data/features/features.parquet and individual data/features/{SYMBOL}_features.parquet.
"""

import logging
import sys
import os
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

    all_frames = []

    for f in sorted(DATA_DIR.glob("*.parquet")):
        sym = f.stem.replace("NSE_", "").replace("NSE:", "")

        df = pd.read_parquet(f)

        # Ensure required columns exist
        required = {"date", "close"}
        if not required.issubset(df.columns):
            logger.warning("Skipping %s — missing columns %s", f.name, required - set(df.columns))
            continue

        df["symbol"] = sym
        df = df.sort_values("date").reset_index(drop=True)

        try:
            feat_df = add_features(df)
        except Exception as e:
            logger.warning("Feature generation failed for %s: %s", sym, e)
            continue

        feat_df["symbol"] = sym  # re-attach after add_features (which drops it)

        # Save per-symbol file
        sym_out = OUT_DIR / f"{sym}_features.parquet"
        feat_df.to_parquet(sym_out, index=False)

        all_frames.append(feat_df)
        logger.info("✅ %s  →  %d rows, %d features", sym, len(feat_df), len(feat_df.columns))

    if not all_frames:
        logger.error("No feature data generated. Check data/prices/")
        return

    combined = pd.concat(all_frames, ignore_index=True).sort_values(["symbol", "date"])
    combined.to_parquet(OUT_DIR / "features.parquet", index=False)

    logger.info(
        "Combined feature file: %d rows × %d columns",
        len(combined), len(combined.columns),
    )


if __name__ == "__main__":
    main()