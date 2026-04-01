"""
scripts/run_live.py

Lightweight live signal refresh — runs every 15 minutes during market hours.
Skips ETL (too slow) and just re-scores existing features with latest price.

Use this for intraday signal updates during 9:15 AM - 3:30 PM IST.
Run run_all.py once in the morning to download history,
then run_live.py every 15 minutes for live updates.
"""

import logging
import os
import sys
import time
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)

from src.data.live_market import is_market_open
from src.model.ml_model import generate_signals
from src.research.features import add_features

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
OUT_DIR = Path("data/signals")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_live_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch current market price for each symbol using fast batch download."""
    prices = {}
    yf_syms = [s + ".NS" for s in symbols]
    try:
        data = yf.download(yf_syms, period="1d", interval="5m", progress=False, timeout=20)
        if data is None or data.empty:
            return prices

        close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)
        if isinstance(close, pd.Series):
            close = close.to_frame()

        for col in close.columns:
            sym = str(col).replace(".NS", "")
            val = close[col].dropna()
            if not val.empty:
                prices[sym] = float(val.iloc[-1])
    except Exception as e:
        logger.warning("Batch live price fetch failed: %s", e)
        # Fallback: fetch one by one
        for sym in symbols:
            try:
                t = yf.Ticker(sym + ".NS")
                h = t.history(period="1d", interval="5m")
                if not h.empty:
                    prices[sym] = float(h["Close"].iloc[-1])
            except Exception:
                pass
    return prices


def refresh_signals_with_live_prices(symbols: list[str]) -> None:
    """
    Load historical features, patch today's close with live price,
    then regenerate signals. Takes ~30 seconds vs 2 minutes for full pipeline.
    """
    feature_file = Path("data/features/features.parquet")
    if not feature_file.exists():
        logger.error("features.parquet not found. Run run_all.py first.")
        return

    logger.info("Fetching live prices for %d symbols...", len(symbols))
    live_prices = get_live_prices(symbols)

    if not live_prices:
        logger.error("Could not get any live prices.")
        return

    logger.info("Got live prices: %s",
                {k: f"{v:.2f}" for k, v in list(live_prices.items())[:5]})

    # Load existing features
    df = pd.read_parquet(feature_file)
    df["symbol"] = df["symbol"].str.replace("NSE_","",regex=False).str.replace("NSE:","",regex=False)
    df["date"]   = pd.to_datetime(df["date"])

    # For each symbol: append a fresh row with today's live price
    today     = pd.Timestamp(date.today())
    new_rows  = []
    prices_dir = Path("data/prices")

    for sym, live_price in live_prices.items():
        sym_data = df[df["symbol"] == sym].sort_values("date")
        if sym_data.empty:
            continue

        # Load raw prices to compute fresh features
        px_file = prices_dir / f"{sym}.parquet"
        if not px_file.exists():
            continue

        px = pd.read_parquet(px_file).sort_values("date")
        px["date"] = pd.to_datetime(px["date"])

        # Replace or append today's row with live price
        px = px[px["date"] < today].copy()
        today_row = pd.DataFrame([{
            "date":   today,
            "open":   live_price,
            "high":   live_price,
            "low":    live_price,
            "close":  live_price,
            "volume": 0,
            "symbol": sym,
        }])
        px = pd.concat([px, today_row], ignore_index=True)

        try:
            feat = add_features(px)
            feat["symbol"] = sym
            new_rows.append(feat)
        except Exception as e:
            logger.warning("Feature gen failed for %s: %s", sym, e)

    if not new_rows:
        logger.error("No features generated from live prices.")
        return

    # Combine: historical OOS features + fresh live rows
    live_df = pd.concat(new_rows, ignore_index=True)
    live_df["symbol"] = live_df["symbol"].str.replace("NSE_","",regex=False)

    # Keep only OOS rows from history + today's live rows
    hist_oos = df[df["date"] < today].copy()
    combined = pd.concat([hist_oos, live_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["date","symbol"], keep="last")
    combined = combined.sort_values(["symbol","date"]).reset_index(drop=True)

    logger.info("Generating live signals on %d rows...", len(combined))

    result = generate_signals(combined)
    if result is None:
        logger.error("Signal generation failed.")
        return

    result["symbol"] = result["symbol"].str.replace("NSE_","",regex=False)

    # Save
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_str  = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d_%H%M")
    out_file = OUT_DIR / f"signals_live_{now_str}.parquet"
    result.to_parquet(out_file, index=False)

    # Also overwrite latest dated file so run_orders picks it up
    latest_file = OUT_DIR / f"signals_{date.today()}.parquet"
    result.to_parquet(latest_file, index=False)

    # Save full history
    result.to_parquet(OUT_DIR / "signals_history.parquet", index=False)

    logger.info("Live signals saved -> %s", out_file)

    # Print today's signals
    latest_date = result["date"].max()
    display = result[result["date"] == latest_date][["date","symbol","probability","signal"]]
    display = display.sort_values("probability", ascending=False)
    print("\n-- Live signals as of", datetime.now(IST).strftime("%H:%M IST"), "--")
    print(display.to_string(index=False))
    print("--------------------------------------\n")


def run_scheduler(interval_minutes: int = 15) -> None:
    """
    Runs live signal refresh every `interval_minutes` during market hours.
    Stops automatically when market closes.
    """
    with open("configs/settings.yaml") as f:
        cfg = yaml.safe_load(f)

    symbols = [s.replace("NSE:","").strip() for s in cfg["universe"]]

    logger.info("Live scheduler started. Refreshing every %d minutes during market hours.", interval_minutes)

    while True:
        if is_market_open():
            logger.info("Market is OPEN. Running live signal refresh...")
            try:
                refresh_signals_with_live_prices(symbols)
            except Exception as e:
                logger.exception("Live refresh failed: %s", e)

            logger.info("Next refresh in %d minutes. Press Ctrl+C to stop.", interval_minutes)
            time.sleep(interval_minutes * 60)
        else:
            logger.info("Market is CLOSED. Scheduler stopping.")
            break


if __name__ == "__main__":
    run_scheduler(interval_minutes=15)