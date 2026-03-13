import yfinance as yf
import pandas as pd
import os

DATA_PATH = "data/prices"


def fetch_live_prices(symbols):

    os.makedirs(DATA_PATH, exist_ok=True)

    for symbol in symbols:

        ticker = symbol.split(":")[1] + ".NS"

        df = yf.download(
            ticker,
            period="5d",
            interval="5m",
            progress=False
        )

        if df.empty:
            continue

        df = df.reset_index()

        file_path = f"{DATA_PATH}/{ticker.replace('.NS','')}.csv"

        df.to_csv(file_path, index=False)

        print(f"Updated price data for {ticker}")