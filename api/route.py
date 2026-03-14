from fastapi import APIRouter
import pandas as pd
import os

router = APIRouter()

# -----------------------------
# MARKET DATA
# -----------------------------

@router.get("/market/{symbol}")
def get_market_data(symbol: str):

    file = f"data/prices/{symbol}.csv"

    if os.path.exists(file):

        df = pd.read_csv(file)

        return df.tail(50).to_dict(orient="records")

    return {"error": "symbol not found"}


# -----------------------------
# SIGNALS
# -----------------------------

@router.get("/signals")
def get_signals():

    folder = "data/signals"

    if not os.path.exists(folder):
        return {"error": "no signals folder"}

    files = sorted(os.listdir(folder))

    if not files:
        return {"error": "no signals"}

    latest = os.path.join(folder, files[-1])

    df = pd.read_parquet(latest)

    return df.to_dict(orient="records")


# -----------------------------
# ORDERS
# -----------------------------

@router.get("/orders")
def get_orders():

    folder = "data/orders"

    if not os.path.exists(folder):

        return {"error": "no orders"}

    files = sorted(os.listdir(folder))

    if not files:

        return {"error": "no orders"}

    latest = os.path.join(folder, files[-1])

    df = pd.read_parquet(latest)

    return df.to_dict(orient="records")


# -----------------------------
# PERFORMANCE
# -----------------------------

@router.get("/performance")
def get_performance():

    file = "reports/equity_curve.csv"

    if not os.path.exists(file):

        return {"error": "run backtest first"}

    df = pd.read_csv(file)

    return df.tail(50).to_dict(orient="records")

@router.get("/metrics")
def get_metrics():

    import pandas as pd
    import numpy as np

    df = pd.read_csv("reports/equity_curve.csv")

    equity = df["equity"]

    returns = equity.pct_change().dropna()

    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (252/len(equity)) - 1

    sharpe = np.sqrt(252) * returns.mean() / returns.std()

    drawdown = (equity / equity.cummax() - 1).min()

    win_rate = (returns > 0).sum() / len(returns)

    return {
        "portfolio_value": round(equity.iloc[-1],2),
        "cagr": round(cagr*100,2),
        "sharpe": round(sharpe,2),
        "drawdown": round(drawdown*100,2),
        "win_rate": round(win_rate*100,2)
    }
import yfinance as yf

@router.get("/live-prices")
def get_live_prices():

    symbols = [
        "TCS.NS",
        "RELIANCE.NS",
        "ICICIBANK.NS",
        "HDFCBANK.NS",
        "INFY.NS"
    ]

    data = []

    for s in symbols:

        ticker = yf.Ticker(s)

        price = ticker.history(period="1d")

        if not price.empty:

            last_price = float(price["Close"].iloc[-1])

            data.append({
                "symbol": s.replace(".NS",""),
                "price": round(last_price,2)
            })

    return data