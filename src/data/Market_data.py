# src/data/market_data.py

from pathlib import Path
import yfinance as yf
import pandas as pd


def fetch_yahoo_prices(symbols, start="2022-01-01", end=None, out_dir="data/prices"):
    """
    Fetch real historical price data from Yahoo Finance
    and save as parquet per symbol.
    """

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for sym in symbols:
        print(f"Downloading {sym}...")
        df = yf.download(sym, start=start, end=end)

        if df.empty:
            print(f"No data for {sym}")
            continue

        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date",
            "Close": "close"
        })

        df = df[["date", "close"]]
        df.to_parquet(out_path / f"{sym.replace(':','_')}.parquet", index=False)

        print(f"Saved {sym} to {out_path}")
