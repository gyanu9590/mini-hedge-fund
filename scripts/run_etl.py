import yfinance as yf
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/prices")

def ingest_prices(symbols):

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for s in symbols:
        ticker = s.replace("NSE:", "") + ".NS"

        df = yf.download(ticker, start="2020-01-01")

        df = df.reset_index()[["Date","Close"]]
        df.columns = ["date","close"]

        df.to_parquet(DATA_DIR / f"{s.replace(':','_')}.parquet", index=False)

def main():

    symbols = ["NSE:INFY","NSE:TCS","NSE:RELIANCE"]

    ingest_prices(symbols)

    print("Real market data downloaded")

if __name__ == "__main__":
    main()