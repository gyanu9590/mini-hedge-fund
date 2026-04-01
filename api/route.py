"""
api/route.py — Production-ready REST API for React frontend
Fixes:
- Absolute paths (critical bug fix)
- Consistent data loading
- Safe error handling
- Clean structure
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

# ─────────────────────────────────────────────────────────────
# BASE PATH (CRITICAL FIX)
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def _auth(key: str = Security(_api_key_header)):
    if key != os.getenv("API_KEY", "changeme"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return key

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _latest_parquet(folder: str) -> pd.DataFrame | None:
    folder_path = BASE_DIR / folder
    files = sorted(folder_path.glob("*.parquet"))
    if not files:
        return None
    try:
        return pd.read_parquet(files[-1])
    except Exception:
        return None

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if "symbol" in df.columns:
        df["symbol"] = (
            df["symbol"]
            .astype(str)
            .str.replace("NSE_", "", regex=False)
            .str.replace("NSE:", "", regex=False)
        )
    return df

# ─────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────
@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/health/detailed")
def health_detailed(_k=Depends(_auth)):
    checks = {
        "prices":   any((BASE_DIR / "data/prices").glob("*.parquet")),
        "features": (BASE_DIR / "data/features/features.parquet").exists(),
        "signals":  any((BASE_DIR / "data/signals").glob("*.parquet")),
        "orders":   any((BASE_DIR / "data/orders").glob("*.parquet")),
        "equity":   (BASE_DIR / "reports/equity_curve.csv").exists(),
        "metrics":  (BASE_DIR / "reports/metrics.json").exists(),
    }

    latest_signal_date = None
    sigs = _latest_parquet("data/signals")
    if sigs is not None and "date" in sigs.columns:
        latest_signal_date = str(pd.to_datetime(sigs["date"]).max().date())

    return {"checks": checks, "latest_signal_date": latest_signal_date}

# ─────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────
@router.get("/metrics")
def get_metrics(_k=Depends(_auth)):
    mf = BASE_DIR / "reports/metrics.json"

    if mf.exists():
        with open(mf) as f:
            return json.load(f)

    ef = BASE_DIR / "reports/equity_curve.csv"
    if not ef.exists():
        raise HTTPException(404, "Run backtest first")

    df = pd.read_csv(ef)
    equity = df["equity"]
    rets = equity.pct_change().dropna()

    ini = float(equity.iloc[0])
    fin = float(equity.iloc[-1])
    n = len(equity)

    cagr = (fin / ini) ** (252 / n) - 1 if n > 0 else 0
    vol = float(rets.std() * np.sqrt(252))
    sharpe = cagr / vol if vol > 0 else 0
    dd = float((equity / equity.cummax() - 1).min())

    return {
        "CAGR": round(cagr, 4),
        "Volatility": round(vol, 4),
        "Sharpe": round(sharpe, 4),
        "MaxDrawdown": round(dd, 4),
        "WinRate": round(float((rets > 0).mean()), 4),
        "TotalReturn": round(float(fin / ini - 1), 4),
        "FinalEquity": round(fin, 2),
    }

# ─────────────────────────────────────────────────────────────
# PERFORMANCE
# ─────────────────────────────────────────────────────────────
@router.get("/performance")
def get_performance(_k=Depends(_auth)):
    f = BASE_DIR / "reports/equity_curve.csv"

    if not f.exists():
        raise HTTPException(404, "Run backtest first")

    df = pd.read_csv(f)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["drawdown"] = (df["equity"] / df["equity"].cummax() - 1).round(4)

    return df[["date", "equity", "drawdown"]].fillna(0).to_dict(orient="records")

# ─────────────────────────────────────────────────────────────
# SIGNALS
# ─────────────────────────────────────────────────────────────
@router.get("/signals")
def get_signals(_k=Depends(_auth)):
    df = _latest_parquet("data/signals")
    if df is None:
        raise HTTPException(404, "No signals")
    return _clean(df).fillna(0).to_dict(orient="records")

@router.get("/signals/today")
def get_signals_today(_k=Depends(_auth)):
    df = _latest_parquet("data/signals")
    if df is None:
        raise HTTPException(404, "No signals")

    df = _clean(df)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] == df["date"].max()]

    if "probability" in df.columns:
        df["probability"] = df["probability"].clip(0, 1)  # FIX >100% BUG
        df = df.sort_values("probability", ascending=False)

    cols = [c for c in ["symbol", "probability", "signal", "date"] if c in df.columns]
    return df[cols].fillna(0).to_dict(orient="records")

# ─────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────
@router.get("/orders")
def get_orders(_k=Depends(_auth)):
    df = _latest_parquet("data/orders")
    if df is None:
        raise HTTPException(404, "No orders")
    return _clean(df).fillna(0).to_dict(orient="records")

# ─────────────────────────────────────────────────────────────
# RISK
# ─────────────────────────────────────────────────────────────
@router.get("/risk")
def get_risk(_k=Depends(_auth)):
    ef = BASE_DIR / "reports/equity_curve.csv"

    if not ef.exists():
        raise HTTPException(404, "Run backtest first")

    df = pd.read_csv(ef)
    rets = df["equity"].pct_change().dropna()

    var95 = float(np.percentile(rets, 5))
    cvar95 = float(rets[rets <= var95].mean())
    dd = df["equity"] / df["equity"].cummax() - 1

    return {
        "var_95": round(var95, 5),
        "cvar_95": round(cvar95, 5),
        "max_drawdown": round(float(dd.min()), 4),
        "current_drawdown": round(float(dd.iloc[-1]), 4),
        "positive_days": round(float((rets > 0).mean()), 4),
    }

# ─────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────
_pipeline_status = {"running": False, "step": "", "error": ""}

def _run_pipeline_bg():
    global _pipeline_status

    steps = [
        ("ETL", "scripts.run_etl"),
        ("Features", "scripts.run_features"),
        ("Signals", "scripts.run_signals"),
        ("Orders", "scripts.run_orders"),
        ("Backtest", "scripts.run_backtest"),
    ]

    _pipeline_status = {"running": True, "step": "Starting", "error": ""}

    for label, mod in steps:
        _pipeline_status["step"] = label

        res = subprocess.run(
            [sys.executable, "-m", mod],
            cwd=str(BASE_DIR),  # FIX path issue
            capture_output=True,
            text=True,
        )

        if res.returncode != 0:
            _pipeline_status = {
                "running": False,
                "step": label,
                "error": res.stderr[-300:],
            }
            return

    _pipeline_status = {"running": False, "step": "Done", "error": ""}

@router.post("/pipeline/run")
def trigger_pipeline(background_tasks: BackgroundTasks, _k=Depends(_auth)):
    if _pipeline_status["running"]:
        return {"status": "already_running", "step": _pipeline_status["step"]}

    background_tasks.add_task(_run_pipeline_bg)
    return {"status": "started"}

@router.get("/pipeline/status")
def pipeline_status(_k=Depends(_auth)):
    return _pipeline_status