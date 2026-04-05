"""
src/research/regime.py

Market Regime Detector  —  Bull / Bear / Sideways

How it works
------------
Uses the Nifty 50 index (^NSEI via yfinance) as the market barometer.
Computes 5 regime signals and combines them into a single label:

  Signal 1 — Trend:      Close vs 200-day MA
  Signal 2 — Momentum:   20-day return (positive = bull)
  Signal 3 — Breadth:    % of Nifty 50 stocks above their 50-day MA
  Signal 4 — Volatility: VIX-like (realized vol vs long-run avg)
  Signal 5 — Drawdown:   distance from 52-week high

Regime labels
-------------
  BULL      — trend up, momentum positive, low vol, low drawdown
  BEAR      — trend down, momentum negative, high vol, deep drawdown
  SIDEWAYS  — mixed signals, market consolidating

Effect on signals
-----------------
  BULL     → only LONG signals (no shorts — don't fight the trend)
  BEAR     → both LONG and SHORT allowed (profit from falling stocks)
  SIDEWAYS → only LONG signals, reduced position size (top_n cut to 3)
"""

import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

REGIME_CACHE_FILE = Path("data/regime_cache.parquet")
NIFTY_TICKER      = "^NSEI"


# ─────────────────────────────────────────────────────────────────────────────
# Core regime computation
# ─────────────────────────────────────────────────────────────────────────────

def detect_regime(prices_dir: str | Path = "data/prices") -> dict:
    """
    Compute today's market regime from Nifty 50 index data.

    Returns
    -------
    {
        "regime":       "BULL" | "BEAR" | "SIDEWAYS",
        "score":        float in [-1, +1]  (+1 = strongest bull),
        "signals": {
            "trend":      1 or -1,
            "momentum":   float,
            "breadth":    float (fraction of stocks above 50d MA),
            "volatility": float (current vol / long-run vol),
            "drawdown":   float (current dd from 52-week high),
        },
        "date": str,
    }
    """
    try:
        nifty = _fetch_nifty()
        if nifty is None or len(nifty) < 200:
            logger.warning("Not enough Nifty data for regime detection. Defaulting to BULL.")
            return _default_regime()

        signals = _compute_signals(nifty, prices_dir)
        regime, score = _classify(signals)

        result = {
            "regime":  regime,
            "score":   round(score, 3),
            "signals": signals,
            "date":    str(date.today()),
        }

        # Cache to disk
        _save_cache(result)
        logger.info("Market regime: %s  (score=%.2f)", regime, score)
        return result

    except Exception as e:
        logger.warning("Regime detection failed: %s — using cache or default.", e)
        return _load_cache_or_default()


def get_cached_regime() -> dict:
    """Return cached regime without re-computing (fast path)."""
    return _load_cache_or_default()


# ─────────────────────────────────────────────────────────────────────────────
# Historical regime series  (for walk-forward backtest)
# ─────────────────────────────────────────────────────────────────────────────

def compute_regime_series(start_date: str = "2019-01-01") -> pd.DataFrame:
    """
    Compute regime label for every trading date since start_date.
    Used by the walk-forward engine to apply regime gating historically.

    Returns DataFrame with columns: [date, regime, score]
    """
    logger.info("Computing historical regime series from %s...", start_date)

    nifty = _fetch_nifty(start_date=start_date)
    if nifty is None or len(nifty) < 200:
        logger.warning("Not enough data for historical regime series.")
        return pd.DataFrame(columns=["date", "regime", "score"])

    nifty = nifty.sort_values("date").reset_index(drop=True)

    rows = []
    for i in range(200, len(nifty)):
        window = nifty.iloc[:i+1]
        try:
            signals = _compute_signals_from_series(window)
            regime, score = _classify(signals)
            rows.append({
                "date":   nifty.iloc[i]["date"],
                "regime": regime,
                "score":  round(score, 3),
            })
        except Exception:
            rows.append({
                "date":   nifty.iloc[i]["date"],
                "regime": "BULL",
                "score":  0.5,
            })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    logger.info("Regime series computed: %d dates, Bull=%d, Bear=%d, Sideways=%d",
                len(df),
                (df["regime"]=="BULL").sum(),
                (df["regime"]=="BEAR").sum(),
                (df["regime"]=="SIDEWAYS").sum())
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_nifty(start_date: str = "2018-01-01") -> pd.DataFrame | None:
    try:
        df = yf.download(NIFTY_TICKER, start=start_date, progress=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index().rename(columns={"Date":"date","Close":"close","High":"high","Low":"low"})
        df["date"] = pd.to_datetime(df["date"])
        return df[["date","close","high","low"]].sort_values("date").reset_index(drop=True)
    except Exception as e:
        logger.warning("Nifty fetch failed: %s", e)
        return None


def _compute_signals(nifty: pd.DataFrame, prices_dir) -> dict:
    return _compute_signals_from_series(nifty, prices_dir=prices_dir)


def _compute_signals_from_series(nifty: pd.DataFrame, prices_dir=None) -> dict:
    close = nifty["close"]

    # Signal 1: Trend  — close vs 200d MA
    ma200   = close.rolling(200).mean().iloc[-1]
    trend   = 1 if close.iloc[-1] > ma200 else -1

    # Signal 2: Momentum — 20d return
    momentum = float(close.pct_change(20).iloc[-1]) if len(close) > 20 else 0.0

    # Signal 3: Volatility regime — 20d realized vol vs 252d avg
    ret      = close.pct_change().dropna()
    vol_20   = float(ret.rolling(20).std().iloc[-1] * np.sqrt(252)) if len(ret) > 20 else 0.2
    vol_252  = float(ret.rolling(252).std().iloc[-1] * np.sqrt(252)) if len(ret) > 252 else vol_20
    vol_ratio = vol_20 / (vol_252 + 1e-9)   # >1 = elevated vol = bearish

    # Signal 4: Drawdown from 52-week high
    high_52w  = close.rolling(252).max().iloc[-1] if len(close) > 252 else close.max()
    drawdown  = float((close.iloc[-1] - high_52w) / (high_52w + 1e-9))

    # Signal 5: Breadth — fraction of universe stocks above their 50d MA
    breadth = _compute_breadth(prices_dir) if prices_dir else 0.5

    return {
        "trend":      trend,
        "momentum":   round(momentum, 4),
        "vol_ratio":  round(vol_ratio, 3),
        "drawdown":   round(drawdown, 4),
        "breadth":    round(breadth, 3),
    }


def _compute_breadth(prices_dir) -> float:
    """Fraction of stocks whose close > 50d MA."""
    if prices_dir is None:
        return 0.5
    above = total = 0
    for f in Path(prices_dir).glob("*.parquet"):
        try:
            px = pd.read_parquet(f)[["date","close"]].sort_values("date")
            if len(px) < 50:
                continue
            ma50  = px["close"].rolling(50).mean().iloc[-1]
            last  = px["close"].iloc[-1]
            above += 1 if last > ma50 else 0
            total += 1
        except Exception:
            pass
    return (above / total) if total > 0 else 0.5


def _classify(signals: dict) -> tuple[str, float]:
    """
    Convert raw signals into BULL / BEAR / SIDEWAYS + a continuous score.
    Score in [-1, +1]: +1 = strongest bull, -1 = strongest bear.
    """
    score = 0.0

    # Trend (+/- 0.30 weight)
    score += 0.30 * signals["trend"]

    # Momentum (+/- 0.25 weight)
    mom_norm = np.clip(signals["momentum"] / 0.10, -1, 1)
    score += 0.25 * mom_norm

    # Breadth (+/- 0.20 weight)  — 0.5 is neutral
    breadth_norm = (signals["breadth"] - 0.5) * 2   # maps [0,1] → [-1,+1]
    score += 0.20 * breadth_norm

    # Volatility (+/- 0.15 weight)  — high vol = bearish
    vol_norm = np.clip(1 - signals["vol_ratio"], -1, 1)
    score += 0.15 * vol_norm

    # Drawdown (+/- 0.10 weight)  — deep dd = bearish
    dd_norm = np.clip(signals["drawdown"] / 0.20, -1, 0)   # dd is negative
    score += 0.10 * (-dd_norm)   # flip sign so deeper dd = lower score

    score = float(np.clip(score, -1, 1))

    if score >= 0.20:
        regime = "BULL"
    elif score <= -0.20:
        regime = "BEAR"
    else:
        regime = "SIDEWAYS"

    return regime, score


# ─────────────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────────────

def _save_cache(result: dict):
    try:
        REGIME_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "date":      result["date"],
            "regime":    result["regime"],
            "score":     result["score"],
            "trend":     result["signals"]["trend"],
            "momentum":  result["signals"]["momentum"],
            "breadth":   result["signals"]["breadth"],
        }
        pd.DataFrame([row]).to_parquet(REGIME_CACHE_FILE, index=False)
    except Exception:
        pass


def _load_cache_or_default() -> dict:
    try:
        if REGIME_CACHE_FILE.exists():
            row = pd.read_parquet(REGIME_CACHE_FILE).iloc[-1]
            return {
                "regime":  row["regime"],
                "score":   float(row["score"]),
                "signals": {
                    "trend":    float(row.get("trend", 1)),
                    "momentum": float(row.get("momentum", 0)),
                    "breadth":  float(row.get("breadth", 0.5)),
                },
                "date": str(row["date"])[:10],
            }
    except Exception:
        pass
    return _default_regime()


def _default_regime() -> dict:
    return {
        "regime": "BULL",
        "score":  0.5,
        "signals": {"trend": 1, "momentum": 0.05, "breadth": 0.6, "vol_ratio": 0.9, "drawdown": -0.02},
        "date": str(date.today()),
    }