import yfinance as yf
import yaml
import pandas as pd
import os

def run_etl():

    os.makedirs("data/prices", exist_ok=True)

    with open("configs/settings.yaml", "r") as f:
        config = yaml.safe_load(f)

    symbols = config["universe"]
    start_date = config["data"]["start_date"]
    end_date = config["data"]["end_date"]

    for symbol in symbols:

        yf_symbol = symbol.replace("NSE:", "") + ".NS"

        print("Downloading:", yf_symbol)

        df = yf.download(yf_symbol, start=start_date, end=end_date)

        if df.empty:
            print("No data:", symbol)
            continue

        df = df.reset_index()

        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })

        df["symbol"] = symbol

        df = df[["date","symbol","open","high","low","close","volume"]]

        path = f"data/prices/{symbol.replace(':','_')}.parquet"

        df.to_parquet(path, index=False)

        print("Saved:", path)

    print("ETL finished")