import logging
import numpy as np
import pandas as pd
import yaml

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.backtest.walkforward import walk_forward_training

logger = logging.getLogger(__name__)


def _load_cfg():
    try:
        with open("configs/settings.yaml") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


_EXCLUDE = {
    "date", "symbol", "target", "future_return",
    "future_return_5d", "future_return_10d",
    "probability", "signal",
    "close", "open", "high", "low", "volume",
}


def _feature_cols(df):
    return [c for c in df.columns if c not in _EXCLUDE]


def generate_signals(df: pd.DataFrame):

    cfg       = _load_cfg()
    model_cfg = cfg.get("model", {})
    sig_cfg   = model_cfg.get("signal", {})

    train_window = model_cfg.get("train_window_days", 252)
    step_days    = model_cfg.get("step_days", 21)
    min_rows     = model_cfg.get("min_train_rows", 120)
    horizon      = model_cfg.get("target_horizon_days", 5)

    top_n    = int(sig_cfg.get("top_n", 5))
    bottom_n = int(sig_cfg.get("bottom_n", 0))

    logger.info("Signal config: top_n=%d  bottom_n=%d", top_n, bottom_n)

    # =========================
    # 🔥 FIX 1: FORCE FEATURE SHIFT (NO LEAKAGE)
    # =========================
    feature_cols_all = _feature_cols(df)

    for col in feature_cols_all:
        df[col] = df.groupby("symbol")[col].shift(1)

    df = df.dropna().reset_index(drop=True)

    # =========================
    # 🔥 WALK FORWARD
    # =========================
    oos = walk_forward_training(
        df,
        train_window_days=train_window,
        step_days=step_days,
        min_train_rows=min_rows,
        target_horizon=horizon,
        target_threshold=0.02,
    )

    if oos is None or len(oos) == 0:
        logger.error("Walk-forward returned no data.")
        return None

    feature_cols = _feature_cols(oos)
    oos = oos.dropna(subset=feature_cols).copy()

    # =========================
    # 🔥 TRAIN ENSEMBLE (IN-SAMPLE)
    # =========================
    first_oos_date = oos["date"].min()
    in_sample = df[df["date"] < first_oos_date].copy()

    # Future return (SAFE — because we already shifted features)
    in_sample["future_return"] = in_sample.groupby("symbol")["close"].transform(
        lambda s: s.shift(-horizon) / s - 1
    )

    # =========================
    # 🔥 HARDER TARGET (REALISTIC)
    # =========================
    upper = in_sample.groupby("date")["future_return"].transform(lambda x: x.quantile(0.7))
    lower = in_sample.groupby("date")["future_return"].transform(lambda x: x.quantile(0.3))

    in_sample["target"] = 0
    in_sample.loc[in_sample["future_return"] >= upper, "target"] = 1
    in_sample.loc[in_sample["future_return"] <= lower, "target"] = -1

    in_sample = in_sample[in_sample["target"] != 0].dropna(subset=feature_cols)

    if len(in_sample) >= min_rows:

        X_train = in_sample[feature_cols]
        y_train = (in_sample["target"] == 1).astype(int)
        X_oos   = oos[feature_cols]

        # =========================
        # 🔥 TIME DECAY WEIGHT
        # =========================
        sample_weights = np.linspace(0.5, 1.0, len(X_train))

        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=7,
            min_samples_leaf=8,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )

        lr_pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=5000, C=0.5, random_state=42)),
        ])

        xgb = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=5,
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
            verbosity=0,
        )

        rf.fit(X_train, y_train, sample_weight=sample_weights)
        xgb.fit(X_train, y_train, sample_weight=sample_weights)
        lr_pipe.fit(X_train, y_train)

        oos["probability"] = (
            0.5 * xgb.predict_proba(X_oos)[:, 1] +
            0.3 * rf.predict_proba(X_oos)[:, 1] +
            0.2 * lr_pipe.predict_proba(X_oos)[:, 1]
        )

        # =========================
        # 🔥 PROBABILITY CONTROL
        # =========================
        oos["probability"] = oos["probability"].clip(0.05, 0.95)

        # =========================
        # 🔥 CROSS-SECTION NORMALIZATION
        # =========================
        oos["probability"] = oos.groupby("date")["probability"].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-6)
        )

        # =========================
        # 🔥 SIGNAL STRENGTH FILTER
        # =========================
        oos["signal_strength"] = abs(oos["probability"])
        oos = oos[oos["signal_strength"] > 0.5]

        logger.info(
            "Final signals: %d rows | mean=%.3f std=%.3f",
            len(oos),
            oos["probability"].mean(),
            oos["probability"].std(),
        )

    # =========================
    # 🔥 ASSIGN SIGNALS
    # =========================
    return _assign_signals_by_rank(oos, top_n, bottom_n)


def _assign_signals_by_rank(df, top_n: int, bottom_n: int):

    df = df.copy()
    df["signal"] = 0

    dates = sorted(df["date"].unique())

    for date in dates:
        mask = df["date"] == date
        day  = df[mask].sort_values("probability", ascending=False)

        if len(day) == 0:
            continue

        long_syms = day.iloc[:top_n]["symbol"].values
        df.loc[mask & df["symbol"].isin(long_syms), "signal"] = 1

        if bottom_n > 0:
            short_syms = day.iloc[-bottom_n:]["symbol"].values
            df.loc[mask & df["symbol"].isin(short_syms), "signal"] = -1

    return df