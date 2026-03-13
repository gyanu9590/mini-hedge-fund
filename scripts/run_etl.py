import yfinance as yf
import pandas as pd
from pathlib import Path
from src.data.live_market import fetch_live_prices

DATA_DIR = Path("data/prices")


def ingest_prices(symbols):
    """
    Download historical daily data for backtesting
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for s in symbols:

        ticker = s.replace("NSE:", "") + ".NS"

        print(f"Downloading historical data for {ticker}")

        df = yf.download(
            ticker,
            start="2020-01-01",
            progress=False
        )

        if df.empty:
            print(f"No data for {ticker}")
            continue

        df = df.reset_index()[["Date", "Close"]]
        df.columns = ["date", "close"]

        file_path = DATA_DIR / f"{s.replace(':','_')}.parquet"

        df.to_parquet(file_path, index=False)

        print(f"Saved historical data → {file_path}")


def main():

    symbols = [
        "NSE:TCS",
        "NSE:INFY",
        "NSE:RELIANCE",
        "NSE:HDFCBANK",
        "NSE:ICICIBANK"
    ]

    # Step 1: Download historical data (for backtesting)
    ingest_prices(symbols)

    # Step 2: Fetch latest intraday prices (live update)
    fetch_live_prices(symbols)

    print("ETL completed successfully")


if __name__ == "__main__":
    main()