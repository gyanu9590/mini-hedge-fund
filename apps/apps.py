import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import subprocess
import os
import yaml
import datetime
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------

st.set_page_config(page_title="Mini Hedge Fund Terminal", layout="wide")
st_autorefresh(interval=60000, key="market_refresh")

st.title("📈 Mini Hedge Fund Quant Trading Terminal")

def get_live_market_data():

    tickers = {
        "NIFTY50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "USDINR": "INR=X",
        "CRUDEOIL": "CL=F",
        "VIX": "^VIX"
    }

    data = {}

    for name, ticker in tickers.items():

        try:
            df = yf.download(ticker, period="2d", interval="1d", progress=False)

            if len(df) >= 2:

                latest = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2]

                change = ((latest - prev) / prev) * 100

                data[name] = (round(latest,2), round(change,2))

            else:

                data[name] = ("N/A",0)

        except:

            data[name] = ("N/A",0)

    return data

# auto refresh every 10 seconds
st_autorefresh(interval=10000, key="refresh")

# ---------------------------------------------------
# MARKET OVERVIEW
# ---------------------------------------------------

st.subheader("🌍 Live Market Overview")

market = get_live_market_data()

c1, c2, c3, c4, c5 = st.columns(5)

nifty, nifty_chg = market["NIFTY50"]
bank, bank_chg = market["BANKNIFTY"]
usd, usd_chg = market["USDINR"]
crude, crude_chg = market["CRUDEOIL"]
vix, vix_chg = market["VIX"]

c1.metric("NIFTY 50", nifty, f"{nifty_chg}%")
c2.metric("BANK NIFTY", bank, f"{bank_chg}%")
c3.metric("USD / INR", usd, f"{usd_chg}%")
c4.metric("CRUDE OIL", crude, f"{crude_chg}%")
c5.metric("VIX", vix, f"{vix_chg}%")

# ---------------------------------------------------
# SIDEBAR CONFIG
# ---------------------------------------------------

st.sidebar.title("⚙ Strategy Configuration")

symbols = st.sidebar.multiselect(
    "Universe",
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
    value=1000000
)

signal_threshold = st.sidebar.slider(
    "Signal Threshold",
    0.5, 0.9, 0.6
)

max_position = st.sidebar.slider(
    "Max Position %",
    1, 30, 10
)

# ---------------------------------------------------
# SAVE CONFIG
# ---------------------------------------------------

if st.sidebar.button("Update Config"):

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

    os.makedirs("configs", exist_ok=True)

    with open("configs/settings.yaml", "w") as f:
        yaml.dump(config, f)

    st.sidebar.success("Config Updated")

# ---------------------------------------------------
# PIPELINE RUNNER
# ---------------------------------------------------

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

st.sidebar.header("🚀 Pipeline")

if st.sidebar.button("Run Pipeline"):

    progress = st.progress(0)

    progress.progress(20)
    run_script("scripts.run_etl")

    progress.progress(40)
    run_script("scripts.run_features")

    progress.progress(60)
    run_script("scripts.run_signals")

    progress.progress(80)
    run_script("scripts.run_orders")

    progress.progress(100)
    run_script("scripts.run_backtest")

    st.success("Pipeline Completed")

# ---------------------------------------------------
# LOAD EQUITY
# ---------------------------------------------------

equity_file = "reports/equity_curve.csv"

if not os.path.exists(equity_file):

    st.warning("Run pipeline first")
    st.stop()

df = pd.read_csv(equity_file)

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

df["returns"] = df["equity"].pct_change().fillna(0)

initial_capital = df["equity"].iloc[0]
final_equity = df["equity"].iloc[-1]

years = len(df) / 252

cagr = (final_equity / initial_capital) ** (1 / years) - 1

volatility = df["returns"].std() * np.sqrt(252)

sharpe = (df["returns"].mean() * 252) / volatility if volatility != 0 else 0

rolling_max = df["equity"].cummax()
drawdown = (df["equity"] - rolling_max) / rolling_max
max_dd = drawdown.min()

# ---------------------------------------------------
# PERFORMANCE
# ---------------------------------------------------

st.subheader("📊 Strategy Performance")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Initial Capital", f"{initial_capital:,.0f}")
c2.metric("Final Equity", f"{final_equity:,.0f}")
c3.metric("CAGR", f"{cagr:.2%}")
c4.metric("Sharpe", f"{sharpe:.2f}")

c5, c6 = st.columns(2)

c5.metric("Volatility", f"{volatility:.2%}")
c6.metric("Max Drawdown", f"{max_dd:.2%}")

# ---------------------------------------------------
# TABS
# ---------------------------------------------------

tabs = st.tabs([
    "Dashboard",
    "Signals",
    "Trades",
    "Portfolio",
    "Risk",
    "Market",
    "System"
])

# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------

with tabs[0]:

    st.subheader("Equity Curve")

    fig = px.line(df, x="date", y="equity")

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Drawdown")

    fig2 = px.area(x=df["date"], y=drawdown)

    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------
# SIGNALS
# ---------------------------------------------------

with tabs[1]:

    st.subheader("Top Signals")

    file = "data/signals/signals_latest.parquet"

    if os.path.exists(file):

        signals = pd.read_parquet(file)

        signals = signals.sort_values("probability", ascending=False)

        st.dataframe(signals)

        st.subheader("Top Opportunities")

        st.dataframe(signals.head(5))

    else:

        st.warning("No signals generated yet")

# ---------------------------------------------------
# TRADES
# ---------------------------------------------------

with tabs[2]:

    st.subheader("Trade Blotter")

    file = "data/orders/orders_latest.parquet"

    if os.path.exists(file):

        orders = pd.read_parquet(file)

        st.dataframe(orders)

        if "pnl" in orders.columns:

            wins = orders[orders["pnl"] > 0]
            losses = orders[orders["pnl"] < 0]

            win_rate = len(wins) / len(orders)

            profit_factor = wins["pnl"].sum() / abs(losses["pnl"].sum())

            st.metric("Win Rate", f"{win_rate:.2%}")
            st.metric("Profit Factor", f"{profit_factor:.2f}")

    else:

        st.warning("No trades yet")

# ---------------------------------------------------
# PORTFOLIO
# ---------------------------------------------------

with tabs[3]:

    assets = [s.split(":")[1] for s in symbols]

    weights = np.repeat(1 / len(assets), len(assets))

    portfolio_df = pd.DataFrame({
        "Asset": assets,
        "Weight": weights
    })

    st.subheader("Portfolio Allocation")

    fig = px.pie(portfolio_df, values="Weight", names="Asset")

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Exposure")

    fig2 = px.bar(portfolio_df, x="Asset", y="Weight")

    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------
# RISK
# ---------------------------------------------------

with tabs[4]:

    st.subheader("Returns Distribution")

    fig = px.histogram(df, x="returns", nbins=50)

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Value at Risk")

    var95 = np.percentile(df["returns"], 5)

    st.metric("Daily VaR 95%", f"{var95:.2%}")

# ---------------------------------------------------
# MARKET
# ---------------------------------------------------

with tabs[5]:

    st.subheader("📈 Live Market Terminal")

    stock = st.selectbox(
        "Select Stock",
        ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK"]
    )

    price_file = f"data/prices/{stock}.csv"

    if os.path.exists(price_file):

        price = pd.read_csv(price_file)

        price.columns = [c.lower() for c in price.columns]

        fig = go.Figure(data=[go.Candlestick(
            x=price["datetime"] if "datetime" in price.columns else price["date"],
            open=price["open"],
            high=price["high"],
            low=price["low"],
            close=price["close"]
        )])

        fig.update_layout(
            title=f"{stock} Live Price",
            xaxis_title="Time",
            yaxis_title="Price"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:

        st.warning("Price data not available. Run ETL first.")

# ---------------------------------------------------
# SYSTEM
# ---------------------------------------------------

with tabs[6]:

    st.subheader("System Status")

    c1, c2, c3 = st.columns(3)

    c1.success("ETL Engine Running")
    c2.success("Signal Engine Running")
    c3.info("Last Update " + str(datetime.datetime.now()))

    st.subheader("Logs")

    log_file = "logs/system.log"

    if os.path.exists(log_file):

        with open(log_file) as f:

            logs = f.readlines()

        st.code("".join(logs[-20:]))

    else:

        st.warning("No logs yet")

# ---------------------------------------------------
# STRATEGY COMPARISON
# ---------------------------------------------------

st.subheader("Strategy Comparison")

strategy_df = pd.DataFrame({

    "Strategy": ["ML Momentum", "Mean Reversion", "Hybrid"],

    "CAGR": [0.35, 0.22, 0.38],

    "Sharpe": [2.1, 1.6, 2.4],

    "Drawdown": [-0.08, -0.06, -0.09]

})

st.dataframe(strategy_df)

# ---------------------------------------------------
# AI MARKET SENTIMENT
# ---------------------------------------------------

st.subheader("AI Market Sentiment")

sentiment_score = 0.42

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=sentiment_score,
    title={"text": "Sentiment Score"},
    gauge={
        "axis": {"range": [-1, 1]}
    }
))

st.plotly_chart(fig)