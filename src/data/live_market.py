"""
src/data/live_market.py

Smart data fetcher that works at ANY time of day:

- During market hours (9:15 AM - 3:30 PM IST, Mon-Fri):
    Downloads 5-minute intraday bars for today, appends to historical data.
    Uses the latest available bar as "today's close" for signal generation.

- After market hours / weekends:
    Downloads normal daily close data (same as before).

This means you can run the pipeline at 10 AM, 1 PM, or 4 PM and always
get the most current prediction possible.
"""

import logging
from datetime import datetime, time, date
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN  = time(9, 15)
MARKET_CLOSE = time(15, 30)


def is_market_open() -> bool:
    """Returns True if NSE is currently open for trading."""
    now = datetime.now(IST)
    if now.weekday() >= 5:          # Saturday=5, Sunday=6
        return False
    current_time = now.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def is_market_closed_today() -> bool:
    """Returns True if today's market session is fully over."""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return True
    return now.time() > MARKET_CLOSE


def fetch_symbol(
    symbol: str,
    start_date: str,
    prices_dir: Path,
    max_retries: int = 3,
) -> pd.DataFrame | None:
    """
    Fetch price data for a single symbol intelligently:
    - If market is open: get 5-min intraday bars for today
      and merge with existing historical parquet.
    - If market is closed: get daily bars from start_date to today.

    Returns cleaned DataFrame with [date, open, high, low, close, volume, symbol].
    """
    import time as time_mod

    yf_sym = symbol + ".NS"

    if is_market_open():
        return _fetch_intraday(symbol, yf_sym, prices_dir, max_retries)
    else:
        return _fetch_daily(symbol, yf_sym, start_date, max_retries)


def _fetch_daily(symbol: str, yf_sym: str, start_date: str, max_retries: int) -> pd.DataFrame | None:
    """Standard daily close fetch with retry."""
    import time as time_mod

    for attempt in range(1, max_retries + 1):
        try:
            df = yf.download(yf_sym, start=start_date, progress=False, timeout=30)
            if df is not None and not df.empty:
                return _clean(df, symbol, freq="daily")
            logger.warning("  Attempt %d: empty daily data for %s", attempt, yf_sym)
        except Exception as e:
            logger.warning("  Attempt %d daily failed %s: %s", attempt, yf_sym, e)
        if attempt < max_retries:
            time_mod.sleep(5)
    return None


def _fetch_intraday(symbol: str, yf_sym: str, prices_dir: Path, max_retries: int) -> pd.DataFrame | None:
    """
    Fetch today's 5-minute bars and merge with existing daily history.
    The latest 5-min bar becomes 'today's close' for feature generation.
    """
    import time as time_mod

    # Load existing daily history
    existing_file = prices_dir / f"{symbol}.parquet"
    if existing_file.exists():
        hist = pd.read_parquet(existing_file)
        hist["date"] = pd.to_datetime(hist["date"])
        # Keep only dates before today
        today = pd.Timestamp(date.today())
        hist = hist[hist["date"] < today].copy()
    else:
        hist = pd.DataFrame()

    # Fetch today's 5-minute intraday data
    for attempt in range(1, max_retries + 1):
        try:
            intra = yf.download(
                yf_sym,
                period="1d",
                interval="5m",
                progress=False,
                timeout=30,
            )
            if intra is not None and not intra.empty:
                break
            logger.warning("  Attempt %d: empty intraday for %s", attempt, yf_sym)
        except Exception as e:
            logger.warning("  Attempt %d intraday failed %s: %s", attempt, yf_sym, e)
            intra = pd.DataFrame()
        if attempt < max_retries:
            time_mod.sleep(3)

    if intra is None or intra.empty:
        logger.warning("  No intraday data for %s, using historical only", symbol)
        return hist if not hist.empty else None

    # Flatten MultiIndex
    if isinstance(intra.columns, pd.MultiIndex):
        intra.columns = intra.columns.get_level_values(0)

    intra = intra.reset_index().rename(columns={
        "Datetime": "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    intra["date"] = pd.to_datetime(intra["date"]).dt.tz_localize(None)

    # Aggregate intraday bars into a single "today" daily row
    today_row = pd.DataFrame([{
        "date":   pd.Timestamp(date.today()),
        "open":   float(intra["open"].iloc[0]),
        "high":   float(intra["high"].max()),
        "low":    float(intra["low"].min()),
        "close":  float(intra["close"].iloc[-1]),   # latest price = live close
        "volume": int(intra["volume"].sum()),
        "symbol": symbol,
    }])

    now_ist = datetime.now(IST)
    logger.info(
        "  Live price for %s: %.2f (as of %s IST, %d 5-min bars)",
        symbol,
        today_row["close"].iloc[0],
        now_ist.strftime("%H:%M"),
        len(intra),
    )

    if not hist.empty:
        hist["symbol"] = symbol
        combined = pd.concat([hist, today_row], ignore_index=True)
    else:
        combined = today_row

    combined = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return combined


def _clean(df: pd.DataFrame, symbol: str, freq: str = "daily") -> pd.DataFrame:
    """Normalize columns from yfinance output."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index().rename(columns={
        "Date": "date", "Datetime": "date",
        "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })

    cols = [c for c in ["date","open","high","low","close","volume"] if c in df.columns]
    df   = df[cols].copy()
    df["date"]   = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df["symbol"] = symbol
    return df.sort_values("date").reset_index(drop=True)