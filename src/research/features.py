"""
src/research/features.py

Feature engineering for a single-symbol price DataFrame.
Input  : DataFrame with columns [date, open, high, low, close, volume]
Output : DataFrame with all features + target columns, NaN rows dropped.
"""

import numpy as np
import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").copy()

    # ── Returns ──────────────────────────────────────────────────
    df["returns"]       = df["close"].pct_change()
    df["log_returns"]   = np.log(df["close"] / df["close"].shift(1))

    # ── Momentum ─────────────────────────────────────────────────
    for w in [5, 10, 20, 60]:
        df[f"momentum_{w}"] = df["close"].pct_change(w)

    # ── Moving averages ──────────────────────────────────────────
    for w in [5, 10, 20, 50, 200]:
        df[f"ma_{w}"] = df["close"].rolling(w).mean()

    df["price_ma10_ratio"]  = df["close"] / df["ma_10"]
    df["price_ma20_ratio"]  = df["close"] / df["ma_20"]
    df["price_ma50_ratio"]  = df["close"] / df["ma_50"]
    df["ma_10_50_cross"]    = df["ma_10"] - df["ma_50"]   # positive = bullish cross
    df["ma_20_200_cross"]   = df["ma_20"] - df["ma_200"]

    # ── Volatility ───────────────────────────────────────────────
    for w in [5, 10, 20, 60]:
        df[f"volatility_{w}"] = df["returns"].rolling(w).std()

    df["vol_regime"] = (df["volatility_20"] / df["volatility_60"]).fillna(1)   # >1 = expanding vol

    # ── RSI ──────────────────────────────────────────────────────
    delta = df["close"].diff()
    gain  = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / (loss + 1e-9)))

    # ── MACD ─────────────────────────────────────────────────────
    df["macd"]        = _ema(df["close"], 12) - _ema(df["close"], 26)
    df["macd_signal"] = _ema(df["macd"], 9)
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # ── Bollinger Bands ──────────────────────────────────────────
    bb_mid            = df["close"].rolling(20).mean()
    bb_std            = df["close"].rolling(20).std()
    df["bb_upper"]    = bb_mid + 2 * bb_std
    df["bb_lower"]    = bb_mid - 2 * bb_std
    df["bb_pct"]      = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)
    df["bb_width"]    = (df["bb_upper"] - df["bb_lower"]) / (bb_mid + 1e-9)

    # ── ATR (Average True Range) ─────────────────────────────────
    if "high" in df.columns and "low" in df.columns:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"]  - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        df["atr_14"]  = tr.rolling(14).mean()
        df["atr_pct"] = df["atr_14"] / df["close"]  # normalised ATR

    # ── Volume features ──────────────────────────────────────────
    if "volume" in df.columns:
        df["volume_ma20"]     = df["volume"].rolling(20).mean()
        df["volume_ratio"]    = df["volume"] / (df["volume_ma20"] + 1)   # >1 = high volume day
        df["price_vol_trend"] = df["returns"] * df["volume_ratio"]       # volume-weighted return

    # ── Trend strength ───────────────────────────────────────────
    df["trend_strength"]  = df["ma_10"] - df["ma_50"]
    df["vol_adj_return"]  = df["returns"] / (df["volatility_10"] + 1e-9)

    # ── Lag features (prevents look-ahead in some learners) ──────
    for lag in [1, 2, 3, 5]:
        df[f"return_lag_{lag}"] = df["returns"].shift(lag)
        df[f"rsi_lag_{lag}"]    = df["rsi"].shift(lag)

    # ── Target ───────────────────────────────────────────────────
    # We define the target here for reference / feature-file storage,
    # but the ML model re-derives it internally to keep config in sync.
    df["future_return_5d"]  = df["close"].shift(-5) / df["close"] - 1
    df["future_return_10d"] = df["close"].shift(-10) / df["close"] - 1
    df["target"]            = np.where(df["future_return_5d"] > 0.02, 1, 0)

    # ── Clean ────────────────────────────────────────────────────
    df = df.dropna().reset_index(drop=True)
    return df