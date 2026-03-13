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

    file = "data/signals/signals_latest.parquet"

    if os.path.exists(file):

        df = pd.read_parquet(file)

        return df.to_dict(orient="records")

    return {"error": "no signals found"}


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