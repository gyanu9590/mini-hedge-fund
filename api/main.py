from fastapi import FastAPI
import pandas as pd
import json
import yfinance as yf
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

@app.get("/metrics")
def get_metrics():
    with open("reports/metrics.json") as f:
        return json.load(f)

@app.get("/signals")
def get_signals():
    df = pd.read_parquet("data/signals/signals.parquet")
    return df.tail(20).to_dict(orient="records")

@app.get("/equity")
def get_equity():
    df = pd.read_csv("reports/equity_curve.csv")
    return df.to_dict(orient="records")
@app.get("/performance")
def get_performance():
    df = pd.read_csv("reports/equity_curve.csv")
    return df.to_dict(orient="records")


@app.get("/live_prices")
def get_live_prices():

    symbols = [
        "TCS.NS","INFY.NS","RELIANCE.NS","HDFCBANK.NS",
        "ICICIBANK.NS","SBIN.NS","AXISBANK.NS","LT.NS",
        "ITC.NS","HINDUNILVR.NS","MARUTI.NS","BAJFINANCE.NS",
        "ASIANPAINT.NS","WIPRO.NS","TITAN.NS","ULTRACEMCO.NS",
        "POWERGRID.NS","NTPC.NS","ADANIENT.NS","ADANIPORTS.NS"
    ]

    data = yf.download(symbols, period="1d", interval="1m")

    latest_prices = []

    for symbol in symbols:
        try:
            price = data["Close"][symbol].dropna().iloc[-1]
            latest_prices.append({
                "symbol": symbol.replace(".NS",""),
                "price": float(price)
            })
        except:
            continue

    return latest_prices

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)