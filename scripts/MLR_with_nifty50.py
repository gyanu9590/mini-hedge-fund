# MLR_with_nifty50.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from datetime import timedelta
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.preprocessing import StandardScaler
import math

# Do NOT call st.set_page_config() here — only in Home.py

def _download_close(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, progress=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"]
    else:
        # fallback if single-level
        if "Close" in df.columns:
            close = df[["Close"]]
            # rename column if needs
        else:
            close = df
    return close

def _compute_returns(close):
    return close.pct_change().dropna()

def _max_drawdown(cum):
    roll_max = cum.cummax()
    drawdown = (cum - roll_max) / roll_max
    return drawdown.min()

def run():
    st.subheader("MLR with NIFTY50 — walk-forward backtest")

    # Sidebar tool controls (local to this tool)
    with st.sidebar:
        st.markdown("### MLR with NIFTY50 - Settings")
    col1, col2 = st.columns(2)
    with col1:
        market = st.text_input("Market ticker (y)", value="^NSEI")
        default_predictors = ["RELIANCE.NS","HDFCBANK.NS","INFY.NS","SBIN.NS","CL=F","INR=X"]
        predictors = st.multiselect("Predictor tickers (X)", default_predictors, default_predictors[:3])
        start = st.date_input("Start date", value=pd.to_datetime("2024-01-01"))
        end = st.date_input("End date", value=pd.to_datetime("today"))
    with col2:
        initial_capital = st.number_input("Initial capital (₹)", value=10000.0, step=1000.0)
        train_years = st.number_input("Training window (years)", value=0.5, min_value=0.1, step=0.1)
        rebalance_days = st.number_input("Retrain every (days)", value=21, min_value=1)
        allow_short = st.checkbox("Allow shorting (long-short strategy)", value=False)
        tx_cost_pct = st.slider("Transaction cost per entry (%)", min_value=0.0, max_value=1.0, value=0.03, step=0.01)
        tx_cost = tx_cost_pct / 100.0
    st.write("Selected predictors:", predictors)

    # Extra options area
    st.markdown("### Options")
    st.checkbox("Show rolling CV per-fold stats", key="show_cv")
    st.checkbox("Show OLS summary (unscaled) - slower", key="show_ols")

    run_btn = st.button("Run strategy")

    if not run_btn:
        st.info("Set parameters and click **Run strategy**")
        return

    if len(predictors) == 0:
        st.error("Pick at least one predictor.")
        return

    # Download
    with st.spinner("Downloading price data..."):
        closes = _download_close([market] + predictors, start, end)
        if closes is None or closes.empty:
            st.error("No data downloaded. Check tickers / date range.")
            return

    # Ensure market present (try alt)
    if market not in closes.columns:
        alt = market.replace("^", "")
        if alt in closes.columns:
            closes[market] = closes[alt]
        else:
            st.error(f"Market ticker {market} not in downloaded data columns: {list(closes.columns)}")
            return

    # Prepare returns & lagged predictors (no lookahead)
    returns = _compute_returns(closes)
    X_raw = returns[predictors].shift(1).dropna()   # use yesterday's returns as features
    y_all = returns[market].reindex(X_raw.index).dropna()
    X = X_raw.reindex(y_all.index)
    y = y_all.reindex(X.index)

    if X.empty or y.empty:
        st.error("No overlapping data after creating lagged features. Try extending start date.")
        return

    # Walk-forward backtest (fixed-length training)
    sim = pd.DataFrame(index=y.index)
    sim["Actual_Return"] = y
    sim["Predicted_Return"] = 0.0

    train_days = int(train_years * 252)
    dates = list(X.index)
    n = len(dates)
    i_train = 0
    all_models = []

    while True:
        train_start = i_train
        train_end = train_start + train_days - 1
        if train_end >= n - 1:
            break
        test_start = train_end + 1
        test_end = min(test_start + rebalance_days - 1, n - 1)

        train_idx = dates[train_start:train_end+1]
        test_idx = dates[test_start:test_end+1]

        X_train = X.loc[train_idx]
        y_train = y.loc[train_idx]
        X_test = X.loc[test_idx]

        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_train)
        X_te_s = scaler.transform(X_test)

        model = Ridge(alpha=1.0)  # regularized linear model
        model.fit(X_tr_s, y_train)
        preds = pd.Series(model.predict(X_te_s), index=test_idx)

        sim.loc[test_idx, "Predicted_Return"] = preds
        all_models.append({"train_idx": (train_idx[0], train_idx[-1]), "test_idx": (test_idx[0], test_idx[-1]),
                           "model": model, "scaler": scaler})

        i_train += rebalance_days
        if i_train + train_days >= n:
            break

    # Build signals and execute next day (no lookahead)
    # Signal raw: 1 long if predicted > 0, -1 short if predicted < 0 and shorting allowed
    if allow_short:
        sim["Signal_raw"] = sim["Predicted_Return"].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    else:
        sim["Signal_raw"] = (sim["Predicted_Return"] > 0).astype(int)
    # Execution shift by 1 day: action based on yesterday's prediction
    sim["Signal"] = sim["Signal_raw"].shift(1).fillna(0).astype(int)

    # If shorting allowed, ensure Signal can be -1; we shifted so convert to int properly
    if allow_short:
        sim["Signal"] = sim["Signal_raw"].shift(1).fillna(0).astype(int)

    # Strategy returns:
    if allow_short:
        # long-short: strategy return = Signal * actual_return (Signal in {-1,0,1})
        sim["Strategy_Return_raw"] = sim["Signal"] * sim["Actual_Return"]
    else:
        # long-only: only get actual return when Signal == 1
        sim["Strategy_Return_raw"] = sim["Actual_Return"] * (sim["Signal"] == 1).astype(int)

    # Transaction costs on entries (0->1 or 0->-1)
    if allow_short:
        # entry occurs when abs(signal) goes from 0 to 1 or 1 to -1 (treat both as entry)
        sim["Entry"] = sim["Signal"].diff().abs() > 0
    else:
        sim["Entry"] = (sim["Signal"].diff() == 1)

    sim["Strategy_Return"] = sim["Strategy_Return_raw"].copy()
    sim.loc[sim["Entry"] == True, "Strategy_Return"] = sim.loc[sim["Entry"] == True, "Strategy_Return"] - tx_cost

    # Cumulatives & portfolios
    sim["Cum_BuyHold"] = (1 + sim["Actual_Return"]).cumprod()
    sim["Cum_Strategy"] = (1 + sim["Strategy_Return"]).cumprod()
    sim["Portfolio_BuyHold"] = initial_capital * sim["Cum_BuyHold"]
    sim["Portfolio_Strategy"] = initial_capital * sim["Cum_Strategy"]

    # Random baseline
    rng = np.random.default_rng(42)
    rand_signals = rng.integers(0, 2, size=len(sim))
    sim["Rand_Return"] = sim["Actual_Return"] * rand_signals
    sim["Cum_Random"] = (1 + sim["Rand_Return"]).cumprod()
    sim["Portfolio_Random"] = initial_capital * sim["Cum_Random"]

    # Metrics
    final_bh = sim["Portfolio_BuyHold"].iloc[-1]
    final_strat = sim["Portfolio_Strategy"].iloc[-1]
    pnl_bh = final_bh - initial_capital
    pnl_str = final_strat - initial_capital
    pct_bh = (pnl_bh / initial_capital) * 100.0
    pct_str = (pnl_str / initial_capital) * 100.0

    days = (sim.index[-1] - sim.index[0]).days
    cagr_bh = (sim["Cum_BuyHold"].iloc[-1]) ** (365.0/days) - 1 if days>0 else np.nan
    cagr_str = (sim["Cum_Strategy"].iloc[-1]) ** (365.0/days) - 1 if days>0 else np.nan

    strat_daily = sim["Strategy_Return"].dropna()
    sharpe = (strat_daily.mean() / strat_daily.std() * math.sqrt(252)) if strat_daily.std()>0 else np.nan
    dir_acc = (np.sign(sim["Actual_Return"]) == np.sign(sim["Predicted_Return"])).mean() * 100.0
    mdd_bh = _max_drawdown(sim["Cum_BuyHold"])
    mdd_str = _max_drawdown(sim["Cum_Strategy"])

    # Display summary
    st.header(f"Simulation: {sim.index[0].date()} → {sim.index[-1].date()}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Buy & Hold (final)", f"₹{final_bh:,.2f}", f"{pct_bh:.2f}%")
        st.write(f"P/L: ₹{pnl_bh:,.2f}")
        st.write(f"CAGR: {cagr_bh:.2%}")
        st.write(f"Max Drawdown: {mdd_bh:.2%}")
    with c2:
        st.metric("Model Strategy (final)", f"₹{final_strat:,.2f}", f"{pct_str:.2f}%")
        st.write(f"P/L: ₹{pnl_str:.2f}")
        st.write(f"CAGR: {cagr_str:.2%}")
        st.write(f"Sharpe (ann.): {sharpe:.2f}")
        st.write(f"Max Drawdown: {mdd_str:.2%}")
    with c3:
        st.metric("Random baseline (final)", f"₹{sim['Portfolio_Random'].iloc[-1]:,.2f}")
        st.write(f"Directional acc.: {dir_acc:.2f}%")
        days_in_market = int((sim["Signal"] != 0).sum())
        pct_in_market = 100.0 * days_in_market / len(sim)
        st.write(f"Days in market: {days_in_market} / {len(sim)} ({pct_in_market:.1f}%)")
        st.write(f"Retrain every {rebalance_days} days; train window {train_years} years")
        st.write(f"Transaction cost per entry: {tx_cost_pct:.2f}%")

    # Portfolio chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sim.index, y=sim["Portfolio_BuyHold"], name="Buy & Hold"))
    fig.add_trace(go.Scatter(x=sim.index, y=sim["Portfolio_Random"], name="Random"))
    fig.add_trace(go.Scatter(x=sim.index, y=sim["Portfolio_Strategy"], name="Model Strategy"))
    fig.update_layout(title="Portfolio value over time", yaxis_title="₹", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Show recent rows
    st.subheader("Recent simulation rows (tail)")
    st.dataframe(sim[["Actual_Return","Predicted_Return","Signal","Entry","Strategy_Return","Portfolio_Strategy"]].tail(30).style.format({
        "Actual_Return":"{:.4%}",
        "Predicted_Return":"{:.4%}",
        "Strategy_Return":"{:.4%}",
        "Portfolio_Strategy":"₹{:.2f}"
    }))

    # Rolling CV stats (optional): compute per-fold metrics from all_models
    if st.session_state.get("show_cv", False):
        st.subheader("Per-fold rolling stats (train -> test)")
        rows = []
        for idx, rec in enumerate(all_models):
            train0, train1 = rec["train_idx"]
            test0, test1 = rec["test_idx"]
            mdl = rec["model"]
            # compute R^2 and directional acc on test
            test_index = pd.date_range(start=test0, end=test1, freq="B") if isinstance(test0, pd.Timestamp) else []
            # easier: use sim Predicted_Return slice:
            preds_slice = sim.loc[test0:test1, "Predicted_Return"]
            actual_slice = sim.loc[test0:test1, "Actual_Return"]
            if len(preds_slice) == 0:
                continue
            r2 = np.corrcoef(actual_slice, preds_slice)[0,1]**2 if len(preds_slice)>1 else np.nan
            diracc = (np.sign(actual_slice) == np.sign(preds_slice)).mean() * 100.0
            rows.append({"fold": idx+1, "train": f"{train0.date()}→{train1.date()}", "test": f"{test0.date()}→{test1.date()}", "r2": r2, "dir_acc%": diracc})
        if rows:
            st.table(pd.DataFrame(rows))

    # Download CSV
    csv = sim.to_csv().encode()
    st.download_button("Download simulation CSV", csv, "sim.csv", "text/csv")

    st.success("Backtest finished.")
