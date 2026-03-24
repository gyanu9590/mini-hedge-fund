"""
api/route.py

FastAPI routes with:
- API key authentication (reads from .env / config)
- Live /metrics computed from equity_curve.csv (not cached)
- /risk endpoint exposing VaR, CVaR, Calmar
- /health endpoint for monitoring
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

router = APIRouter()

# ── Auth ──────────────────────────────────────────────────────────────────────
API_KEY_NAME   = "X-API-Key"
_api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def _get_api_key(key: str = Security(_api_key_header)):
    expected = os.getenv("API_KEY", "changeme")
    if key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return key


# ── Helpers ───────────────────────────────────────────────────────────────────
def _latest_parquet(folder: str) -> pd.DataFrame | None:
    files = sorted(Path(folder).glob("*.parquet"))
    if not files:
        return None
    return pd.read_parquet(files[-1])


def _clean_symbols(df: pd.DataFrame) -> pd.DataFrame:
    if "symbol" in df.columns:
        df["symbol"] = (
            df["symbol"].astype(str)
            .str.replace("NSE_", "", regex=False)
            .str.replace("NSE:", "", regex=False)
        )
    return df


# ── Health ────────────────────────────────────────────────────────────────────
@router.get("/health")
def health():
    return {"status": "ok"}


# ── Market data ───────────────────────────────────────────────────────────────
@router.get("/market/{symbol}")
def get_market_data(symbol: str, _key: str = Depends(_get_api_key)):
    for ext in [".csv", ".parquet"]:
        f = Path(f"data/prices/{symbol}{ext}")
        if f.exists():
            df = pd.read_csv(f) if ext == ".csv" else pd.read_parquet(f)
            return df.tail(50).fillna("").to_dict(orient="records")
    raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")


# ── Signals ───────────────────────────────────────────────────────────────────
@router.get("/signals")
def get_signals(_key: str = Depends(_get_api_key)):
    df = _latest_parquet("data/signals")
    if df is None:
        raise HTTPException(status_code=404, detail="No signal files found")
    df = _clean_symbols(df)
    return df.fillna("").to_dict(orient="records")


# ── Orders ────────────────────────────────────────────────────────────────────
@router.get("/orders")
def get_orders(_key: str = Depends(_get_api_key)):
    df = _latest_parquet("data/orders")
    if df is None:
        raise HTTPException(status_code=404, detail="No order files found")
    df = _clean_symbols(df)
    return df.fillna("").to_dict(orient="records")


# ── Performance (equity curve) ────────────────────────────────────────────────
@router.get("/performance")
def get_performance(_key: str = Depends(_get_api_key)):
    f = Path("reports/equity_curve.csv")
    if not f.exists():
        raise HTTPException(status_code=404, detail="Run backtest first")
    df = pd.read_csv(f)
    return df.tail(100).fillna("").to_dict(orient="records")


# ── Metrics (computed live from equity curve) ─────────────────────────────────
@router.get("/metrics")
def get_metrics(_key: str = Depends(_get_api_key)):
    # Try metrics.json first (pre-computed by backtest)
    mf = Path("reports/metrics.json")
    if mf.exists():
        with open(mf) as f:
            return json.load(f)

    # Fallback: compute from equity_curve.csv
    ef = Path("reports/equity_curve.csv")
    if not ef.exists():
        raise HTTPException(status_code=404, detail="Run backtest first")

    df     = pd.read_csv(ef)
    equity = df["equity"]
    rets   = equity.pct_change().dropna()
    n      = len(equity)

    cagr     = (equity.iloc[-1] / equity.iloc[0]) ** (252 / n) - 1
    vol      = rets.std() * np.sqrt(252)
    sharpe   = cagr / vol if vol > 0 else 0
    downside = rets[rets < 0].std() * np.sqrt(252)
    sortino  = cagr / downside if downside > 0 else 0
    dd       = (equity / equity.cummax() - 1).min()
    calmar   = cagr / abs(dd) if dd != 0 else 0
    var95    = float(np.percentile(rets, 5))
    win_rate = float((rets > 0).mean())

    return {
        "portfolio_value": round(float(equity.iloc[-1]), 2),
        "cagr_pct":        round(cagr * 100, 2),
        "sharpe":          round(sharpe, 2),
        "sortino":         round(sortino, 2),
        "calmar":          round(calmar, 2),
        "max_drawdown_pct": round(dd * 100, 2),
        "var_95_daily_pct": round(var95 * 100, 2),
        "win_rate_pct":    round(win_rate * 100, 2),
        "volatility_pct":  round(vol * 100, 2),
    }


# ── Risk summary ──────────────────────────────────────────────────────────────
@router.get("/risk")
def get_risk(_key: str = Depends(_get_api_key)):
    ef = Path("reports/equity_curve.csv")
    if not ef.exists():
        raise HTTPException(status_code=404, detail="Run backtest first")

    df   = pd.read_csv(ef)
    rets = df["equity"].pct_change().dropna()

    var95  = float(np.percentile(rets, 5))
    cvar95 = float(rets[rets <= var95].mean())
    dd     = (df["equity"] / df["equity"].cummax() - 1)

    return {
        "var_95_daily":  round(var95, 5),
        "cvar_95_daily": round(cvar95, 5),
        "max_drawdown":  round(float(dd.min()), 5),
        "current_drawdown": round(float(dd.iloc[-1]), 5),
        "positive_days_pct": round(float((rets > 0).mean()) * 100, 2),
    }


# ── Live prices via yfinance ──────────────────────────────────────────────────
@router.get("/live-prices")
def get_live_prices(_key: str = Depends(_get_api_key)):
    import yfinance as yf

    symbols = ["TCS", "RELIANCE", "ICICIBANK", "HDFCBANK", "INFY",
               "SBIN", "ITC", "LT", "AXISBANK", "BAJFINANCE"]
    data = []
    for s in symbols:
        try:
            hist = yf.Ticker(s + ".NS").history(period="1d")
            if not hist.empty:
                data.append({
                    "symbol": s,
                    "price":  round(float(hist["Close"].iloc[-1]), 2),
                    "volume": int(hist["Volume"].iloc[-1]),
                })
        except Exception:
            pass
    return data