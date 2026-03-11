import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import subprocess
import os
import yaml
import datetime

st.set_page_config(page_title="Mini Hedge Fund Dashboard", layout="wide")

st.title("📈 Mini Hedge Fund System Dashboard")

# -----------------------------
# Sidebar Controls
# -----------------------------

st.sidebar.title("⚙ Trading Configuration")

symbols = st.sidebar.multiselect(
    "Select Stocks",
    ["NSE:TCS", "NSE:INFY", "NSE:RELIANCE", "NSE:HDFCBANK", "NSE:ICICIBANK"],
    default=["NSE:TCS", "NSE:INFY"]
)

start_date = st.sidebar.date_input(
    "Start Date",
    datetime.date(2023, 1, 1)
)

end_date = st.sidebar.date_input(
    "End Date",
    datetime.date(2024, 1, 10)
)

initial_capital = st.sidebar.number_input(
    "Initial Capital",
    value=1000000,
    step=10000
)

# -----------------------------
# Ensure folders exist
# -----------------------------

os.makedirs("configs", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# -----------------------------
# Save Config
# -----------------------------

if st.sidebar.button("Update Strategy Config"):

    config = {
        "data": {
            "start_date": str(start_date),
            "end_date": str(end_date)
        },
        "universe": symbols,
        "portfolio": {
            "initial_capital": initial_capital
        }
    }

    with open("configs/settings.yaml", "w") as f:
        yaml.dump(config, f)

    st.sidebar.success("Configuration Updated")

# -----------------------------
# Pipeline Runner
# -----------------------------

def run_script(script):

    result = subprocess.run(
        ["python", "-m", script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        st.error(f"{script} failed")
        st.code(result.stderr)
        st.stop()

# -----------------------------
# Run Pipeline
# -----------------------------

st.sidebar.header("🚀 Pipeline")

if st.sidebar.button("Run Full Pipeline"):

    with st.spinner("Running ETL..."):
        run_script("scripts.run_etl")

    with st.spinner("Generating Features..."):
        run_script("scripts.run_features")

    with st.spinner("Generating Signals..."):
        run_script("scripts.run_signals")

    with st.spinner("Generating Orders..."):
        run_script("scripts.run_orders")

    with st.spinner("Running Backtest..."):
        run_script("scripts.run_backtest")

    st.sidebar.success("Pipeline Completed")

    st.rerun()

# -----------------------------
# Check Data Exists
# -----------------------------

equity_file = "reports/equity_curve.csv"

if not os.path.exists(equity_file):

    st.warning("⚠ No backtest results found. Run the pipeline.")
    st.stop()

# -----------------------------
# Load Data
# -----------------------------

df = pd.read_csv(equity_file)

if "date" not in df.columns or "equity" not in df.columns:
    st.error("equity_curve.csv must contain 'date' and 'equity' columns")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# -----------------------------
# Calculate Returns
# -----------------------------

df["returns"] = df["equity"].pct_change().fillna(0)

initial_capital = float(df["equity"].iloc[0])
final_equity = float(df["equity"].iloc[-1])

# Trading days
years = len(df) / 252

# CAGR
if final_equity <= 0:
    cagr = -1
else:
    cagr = (final_equity / initial_capital) ** (1 / years) - 1

# Volatility
volatility = df["returns"].std() * np.sqrt(252)

# Sharpe
if volatility == 0:
    sharpe = 0
else:
    sharpe = (df["returns"].mean() * 252) / volatility

# Drawdown
rolling_max = df["equity"].cummax()
drawdown = (df["equity"] - rolling_max) / rolling_max
max_dd = drawdown.min()

# -----------------------------
# Performance Metrics
# -----------------------------

st.subheader("📊 Performance Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Initial Capital", f"{initial_capital:,.0f}")
col2.metric("Final Equity", f"{final_equity:,.0f}")
col3.metric("CAGR", f"{cagr:.2%}")
col4.metric("Sharpe Ratio", f"{sharpe:.2f}")

col5, col6 = st.columns(2)

col5.metric("Volatility", f"{volatility:.2%}")
col6.metric("Max Drawdown", f"{max_dd:.2%}")

# -----------------------------
# Equity Curve
# -----------------------------

st.subheader("📈 Equity Curve")

fig = px.line(
    df,
    x="date",
    y="equity",
    title="Portfolio Equity Curve"
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Drawdown
# -----------------------------

st.subheader("📉 Drawdown")

fig_dd = px.area(
    x=df["date"],
    y=drawdown,
    title="Portfolio Drawdown"
)

st.plotly_chart(fig_dd, use_container_width=True)

# -----------------------------
# Returns Distribution
# -----------------------------

st.subheader("📊 Daily Returns Distribution")

fig_hist = px.histogram(
    df,
    x="returns",
    nbins=50,
    title="Daily Returns Distribution"
)

st.plotly_chart(fig_hist, use_container_width=True)

# -----------------------------
# Portfolio Allocation
# -----------------------------

st.subheader("💼 Portfolio Allocation")

assets = [s.split(":")[1] for s in symbols]

weights = np.repeat(1/len(assets), len(assets))

portfolio_df = pd.DataFrame({
    "Asset": assets,
    "Weight": weights
})

fig_pie = px.pie(
    portfolio_df,
    values="Weight",
    names="Asset",
    title="Portfolio Allocation"
)

st.plotly_chart(fig_pie, use_container_width=True)

# -----------------------------
# Sentiment Section (Demo)
# -----------------------------

st.subheader("📰 News Sentiment")

sentiment_score = 0.35

st.metric("Sentiment Score", sentiment_score)

if sentiment_score > 0.2:
    st.success("Bullish News Sentiment")

elif sentiment_score < -0.2:
    st.error("Bearish News Sentiment")

else:
    st.warning("Neutral Sentiment")

# -----------------------------
# Raw Data
# -----------------------------

st.subheader("Raw Equity Data")

st.dataframe(df)

st.markdown(
"""
Pipeline Flow

ETL → Features → Signals → Orders → Backtest → Dashboard
"""
)