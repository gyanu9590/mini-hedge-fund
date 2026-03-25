"""
scripts/run_all.py  —  Full pipeline runner.
ETL -> Features -> Signals -> Orders -> Backtest
"""

import io
import logging
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

os.makedirs("logs", exist_ok=True)

# UTF-8 on Windows (prevents emoji crash on cp1252 terminal)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/system.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

import scripts.run_etl      as etl_mod
import scripts.run_features as feat_mod
import scripts.run_signals  as sig_mod
import scripts.run_orders   as ord_mod
import scripts.run_backtest as bt_mod


def run():
    steps = [
        ("ETL",      etl_mod.main),
        ("Features", feat_mod.main),
        ("Signals",  sig_mod.main),
        ("Orders",   ord_mod.main),
        ("Backtest", bt_mod.main),
    ]
    for name, fn in steps:
        logger.info("=== Starting: %s ===", name)
        try:
            fn()
            logger.info("=== Done:     %s ===", name)
        except Exception as e:
            logger.exception("Step %s failed: %s", name, e)
            continue
    logger.info("Pipeline finished.")


if __name__ == "__main__":
    run()