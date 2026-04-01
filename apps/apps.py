"""
apps/apps.py  —  QuantEdge ML Trading System Dashboard
Refactored: stable CAGR, no duplicate logic, clean metrics, accurate live data.
"""

import datetime
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QuantEdge ML Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st_autorefresh(interval=60_000, key="market_refresh")   # refresh every 60s

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def load_latest_parquet(folder: str) -> pd.DataFrame | None:
    """Load the most-recently-modified parquet in folder."""
    files = glob.glob(os.path.join(folder, "*.parquet"))
    if not files:
        return None
    try:
        return pd.read_parquet(max(files, key=os.path.getmtime))
    except Exception:
        return None


def load_metrics() -> dict:
    """Load pre-computed metrics from reports/metrics.json (stable, no re-compute)."""
    path = "reports/metrics.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def load_equity() -> pd.DataFrame | None:
    """Load equity curve CSV with guaranteed date + equity columns."""
    path = "reports/equity_curve.csv"
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)

        # Ensure date column
        if "date" not in df.columns:
            df = df.reset_index()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

        # Ensure equity column
        if "equity" not in df.columns:
            for alt in ["portfolio_value", "value", "capital"]:
                if alt in df.columns:
                    df["equity"] = df[alt]
                    break

        if "equity" not in df.columns:
            return None

        df["equity"] = pd.to_numeric(df["equity"], errors="coerce")
        df = df.dropna(subset=["equity"])
        return df
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LIVE MARKET DATA  (cached 60 s to avoid hammering yfinance)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_market_overview() -> dict:
    tickers = {
        "NIFTY 50":   "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "USD/INR":     "INR=X",
        "CRUDE OIL":   "CL=F",
        "VIX":         "^VIX",
    }
    result = {}
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="2d", interval="1d", progress=False)
            if df is None or len(df) < 2:
                result[name] = ("N/A", 0.0)
                continue
            # Always extract scalar — yfinance sometimes returns Series
            latest = float(df["Close"].iloc[-1].item() if hasattr(df["Close"].iloc[-1], "item") else df["Close"].iloc[-1])
            prev   = float(df["Close"].iloc[-2].item() if hasattr(df["Close"].iloc[-2], "item") else df["Close"].iloc[-2])
            chg    = round((latest - prev) / prev * 100, 2)
            result[name] = (round(latest, 2), chg)
        except Exception:
            result[name] = ("N/A", 0.0)
    return result


@st.cache_data(ttl=30)
def get_live_stock_prices(symbols: list[str]) -> pd.DataFrame:
    """Fetch latest 1-minute price for a list of NSE symbols."""
    if not symbols:
        return pd.DataFrame(columns=["symbol", "price", "change_pct"])
    tickers = [s + ".NS" for s in symbols]
    rows = []
    try:
        data = yf.download(tickers, period="2d", interval="1d", progress=False)
        close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])
        for sym in symbols:
            col = sym + ".NS"
            if col in close.columns:
                vals = close[col].dropna()
                if len(vals) >= 2:
                    price = float(vals.iloc[-1])
                    prev  = float(vals.iloc[-2])
                    chg   = round((price - prev) / prev * 100, 2)
                    rows.append({"symbol": sym, "price": round(price, 2), "change_pct": chg})
    except Exception:
        pass
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol", "price", "change_pct"])


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.title("QuantEdge Terminal")
st.sidebar.caption("ML-Based Trading System")
st.sidebar.divider()

# — Pipeline runner —
st.sidebar.header("Pipeline")

def run_pipeline_step(module: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-m", module],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        st.sidebar.error(f"{module} failed")
        st.sidebar.code(result.stderr[-500:])
        return False
    return True

if st.sidebar.button("Run Full Pipeline", use_container_width=True):
    steps = [
        ("ETL",      "scripts.run_etl"),
        ("Features", "scripts.run_features"),
        ("Signals",  "scripts.run_signals"),
        ("Orders",   "scripts.run_orders"),
        ("Backtest", "scripts.run_backtest"),
    ]
    bar = st.sidebar.progress(0, text="Starting…")
    for i, (label, mod) in enumerate(steps):
        bar.progress((i) * 20, text=f"Running {label}…")
        if not run_pipeline_step(mod):
            break
    else:
        bar.progress(100, text="Done!")
        st.sidebar.success("Pipeline complete")
        st.cache_data.clear()   # clear cached data so dashboard refreshes

st.sidebar.divider()

# — Config editor —
st.sidebar.header("Settings")

try:
    with open("configs/settings.yaml") as f:
        cfg = yaml.safe_load(f) or {}
except FileNotFoundError:
    cfg = {}

initial_cap_cfg = cfg.get("portfolio", {}).get("initial_capital", 1_000_000)
initial_capital_input = st.sidebar.number_input(
    "Initial Capital (₹)", value=int(initial_cap_cfg), step=100_000
)
top_n_input = st.sidebar.slider(
    "Signals: top N longs", 1, 10,
    int(cfg.get("model", {}).get("signal", {}).get("top_n", 5))
)
stop_loss_input = st.sidebar.slider(
    "Stop-loss %", 3, 20,
    int(cfg.get("risk", {}).get("stop_loss_pct", 0.07) * 100)
)

if st.sidebar.button("Save Config", use_container_width=True):
    cfg.setdefault("portfolio", {})["initial_capital"] = initial_capital_input
    cfg.setdefault("model", {}).setdefault("signal", {})["top_n"] = top_n_input
    cfg.setdefault("risk", {})["stop_loss_pct"] = stop_loss_input / 100
    os.makedirs("configs", exist_ok=True)
    with open("configs/settings.yaml", "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    st.sidebar.success("Saved — re-run pipeline to apply")

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.title("QuantEdge ML Trading System")
st.caption(f"Last refreshed: {datetime.datetime.now().strftime('%d %b %Y  %H:%M:%S')}")

# ─────────────────────────────────────────────────────────────────────────────
# LIVE MARKET OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Live Market Overview")
market = get_market_overview()
cols = st.columns(len(market))
for col, (name, (price, chg)) in zip(cols, market.items()):
    delta_str = f"{chg:+.2f}%" if isinstance(chg, float) else "—"
    col.metric(name, f"{price:,.2f}" if isinstance(price, float) else price, delta_str)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY PERFORMANCE  — reads from metrics.json (STABLE, no re-compute)
# ─────────────────────────────────────────────────────────────────────────────

st.subheader("Strategy Performance")

metrics = load_metrics()
equity_df = load_equity()

if metrics:
    # Use pre-computed metrics from backtest engine — CAGR never fluctuates
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Initial Capital",  f"₹{initial_cap_cfg:,.0f}")
    c2.metric("Final Equity",     f"₹{metrics.get('FinalEquity', 0):,.0f}")
    c3.metric("CAGR",             f"{metrics.get('CAGR', 0):.2%}")
    c4.metric("Sharpe",           f"{metrics.get('Sharpe', 0):.2f}")
    c5.metric("Max Drawdown",     f"{metrics.get('MaxDrawdown', 0):.2%}")
    c6.metric("Win Rate",         f"{metrics.get('WinRate', 0):.2%}")

    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("Volatility",    f"{metrics.get('Volatility', 0):.2%}")
    r2c2.metric("Sortino",       f"{metrics.get('Sortino', 0):.2f}")
    r2c3.metric("Total Return",  f"{metrics.get('TotalReturn', 0):.2%}")

elif equity_df is not None:
    # Fallback: compute from equity curve if metrics.json missing
    eq  = equity_df["equity"]
    ret = eq.pct_change().fillna(0)
    n   = len(eq)
    ini = float(eq.iloc[0])
    fin = float(eq.iloc[-1])
    cagr_v = (fin / ini) ** (252 / n) - 1 if n > 0 and ini > 0 else 0
    vol_v  = float(ret.std() * np.sqrt(252))
    sharpe_v = cagr_v / vol_v if vol_v > 0 else 0
    dd_v   = float((eq / eq.cummax() - 1).min())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Initial Capital", f"₹{ini:,.0f}")
    c2.metric("Final Equity",    f"₹{fin:,.0f}")
    c3.metric("CAGR",            f"{cagr_v:.2%}")
    c4.metric("Sharpe",          f"{sharpe_v:.2f}")
    c5.metric("Max Drawdown",    f"{dd_v:.2%}")
else:
    st.info("Run the pipeline to see performance metrics.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tabs = st.tabs(["Dashboard", "Signals", "Orders", "Portfolio", "Risk", "Market", "System"])

# ── TAB 0: Dashboard ──────────────────────────────────────────────────────────
with tabs[0]:

    if equity_df is not None:
        # Equity curve
        fig_eq = px.line(
            equity_df, x="date", y="equity",
            title="Equity Curve",
            labels={"equity": "Portfolio Value (₹)", "date": "Date"},
            color_discrete_sequence=["#4A9EFF"],
        )
        fig_eq.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=36, b=0))
        st.plotly_chart(fig_eq, use_container_width=True)

        # Drawdown curve
        equity_df["drawdown"] = equity_df["equity"] / equity_df["equity"].cummax() - 1
        fig_dd = px.area(
            equity_df, x="date", y="drawdown",
            title="Drawdown",
            labels={"drawdown": "Drawdown", "date": "Date"},
            color_discrete_sequence=["#FF4A4A"],
        )
        fig_dd.update_layout(
            yaxis_tickformat=".1%",
            hovermode="x unified",
            margin=dict(l=0, r=0, t=36, b=0),
        )
        st.plotly_chart(fig_dd, use_container_width=True)
    else:
        st.info("Run the pipeline first to see the equity curve.")

# ── TAB 1: Signals ────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Today's ML Signals")

    signals = load_latest_parquet("data/signals")

    if signals is not None:
        # Show only latest date
        if "date" in signals.columns:
            signals["date"] = pd.to_datetime(signals["date"])
            latest_date = signals["date"].max()
            today_sigs = signals[signals["date"] == latest_date].copy()
        else:
            today_sigs = signals.copy()

        if "probability" in today_sigs.columns:
            today_sigs = today_sigs.sort_values("probability", ascending=False)

        st.caption(f"Signal date: {latest_date.date() if 'date' in signals.columns else 'unknown'}")

        # Color-code by signal
        def color_signal(val):
            if val == 1:  return "background-color: #1a3a1a; color: #4cff4c"
            if val == -1: return "background-color: #3a1a1a; color: #ff4c4c"
            return ""

        display_cols = [c for c in ["symbol","probability","signal"] if c in today_sigs.columns]
        st.dataframe(
            today_sigs[display_cols],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No signals yet. Run the pipeline.")

# ── TAB 2: Orders ─────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Latest Orders")

    orders = load_latest_parquet("data/orders")

    if orders is not None and len(orders) > 0:
        # Live P&L if prices available
        syms = orders["symbol"].tolist()
        live = get_live_stock_prices(syms)

        if not live.empty and "price" in live.columns and "price" in orders.columns:
            orders = orders.merge(
                live[["symbol","price"]].rename(columns={"price": "live_price"}),
                on="symbol", how="left"
            )
            orders["pnl_pct"] = (
                (orders["live_price"] - orders["price"]) / orders["price"] * 100
            ).round(2)

        st.dataframe(orders, use_container_width=True, hide_index=True)

        # Summary
        n_buy  = (orders["side"] == "BUY").sum()  if "side" in orders.columns else 0
        n_sell = (orders["side"] == "SELL").sum() if "side" in orders.columns else 0
        tot_val = orders["target_value"].abs().sum() if "target_value" in orders.columns else 0

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("BUY orders",  n_buy)
        mc2.metric("SELL orders", n_sell)
        mc3.metric("Total exposure", f"₹{tot_val:,.0f}")
    else:
        st.warning("No orders yet. Run the pipeline.")

# ── TAB 3: Portfolio ──────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Portfolio Allocation")

    orders = load_latest_parquet("data/orders")

    if orders is not None and len(orders) > 0:
        if "weight" in orders.columns:
            # Clean symbol names
            orders["Asset"] = orders["symbol"].str.replace("NSE:", "", regex=False)

            alloc_df = orders.copy()
            alloc_df["Weight"] = alloc_df["weight"].abs()

            fig_pie = px.pie(
                alloc_df,
                values="Weight",
                names="Asset",
                title="Current Allocation",
                hole=0.4,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

            if "side" in orders.columns:
                fig_bar = px.bar(
                    orders,
                    x="Asset",
                    y="weight",
                    color="side",
                    title="Exposure by Position",
                    color_discrete_map={"BUY": "#4cff4c", "SELL": "#ff4c4c"},
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(orders, use_container_width=True, hide_index=True)
    else:
        st.warning("No orders available. Run the pipeline.")

# ── TAB 4: Risk ───────────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("Risk Analytics")

    if equity_df is not None:
        rets = equity_df["equity"].pct_change().dropna()

        # VaR and CVaR
        var95  = float(np.percentile(rets, 5))
        cvar95 = float(rets[rets <= var95].mean())
        dd_series = equity_df["equity"] / equity_df["equity"].cummax() - 1
        curr_dd = float(dd_series.iloc[-1])
        max_dd  = float(dd_series.min())

        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.metric("Daily VaR 95%",      f"{var95:.2%}")
        r1c2.metric("CVaR 95%",           f"{cvar95:.2%}")
        r1c3.metric("Max Drawdown",        f"{max_dd:.2%}")
        r1c4.metric("Current Drawdown",    f"{curr_dd:.2%}")

        # Returns distribution
        fig_hist = px.histogram(
            rets, nbins=60,
            title="Daily Returns Distribution",
            labels={"value": "Daily Return"},
            color_discrete_sequence=["#4A9EFF"],
        )
        fig_hist.add_vline(x=var95, line_dash="dash", line_color="red",
                           annotation_text=f"VaR 95%: {var95:.2%}")
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)

        # Rolling Sharpe (30-day)
        rolling_ret = rets.rolling(30).mean() * 252
        rolling_vol = rets.rolling(30).std() * np.sqrt(252)

        rolling_sharpe = (rolling_ret / rolling_vol).replace([np.inf, -np.inf], np.nan)

            # ✅ FIX: align index properly
        equity_df["rolling_sharpe"] = np.nan
        equity_df.loc[rolling_sharpe.index, "rolling_sharpe"] = rolling_sharpe

        fig_rs = px.line(
            equity_df.dropna(subset=["rolling_sharpe"]),
            x="date", y="rolling_sharpe",
            title="Rolling 30-day Sharpe Ratio",
            color_discrete_sequence=["#FFD700"],
        )
        fig_rs.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_rs, use_container_width=True)
    else:
        st.info("Run the pipeline to see risk analytics.")

# ── TAB 5: Market ─────────────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("Market Terminal")

    all_syms = [
        s.replace("NSE:", "")
        for s in cfg.get("universe", ["TCS","INFY","RELIANCE","HDFCBANK","ICICIBANK"])
    ]

    stock = st.selectbox("Select Stock", all_syms)

    price_file_csv = f"data/prices/{stock}.csv"
    price_file_pq  = f"data/prices/{stock}.parquet"

    price_df = None
    if os.path.exists(price_file_pq):
        price_df = pd.read_parquet(price_file_pq)
    elif os.path.exists(price_file_csv):
        price_df = pd.read_csv(price_file_csv)

    if price_df is not None:
        price_df.columns = [c.lower() for c in price_df.columns]
        price_df["date"] = pd.to_datetime(price_df["date"])
        price_df = price_df.sort_values("date").tail(252)   # last year

        if all(c in price_df.columns for c in ["open","high","low","close"]):
            fig_candle = go.Figure(data=[go.Candlestick(
                x=price_df["date"],
                open=price_df["open"],
                high=price_df["high"],
                low=price_df["low"],
                close=price_df["close"],
            )])
            fig_candle.update_layout(
                title=f"{stock} — Last 252 Trading Days",
                xaxis_title="Date",
                yaxis_title="Price (₹)",
                xaxis_rangeslider_visible=False,
            )
            st.plotly_chart(fig_candle, use_container_width=True)
        else:
            fig_line = px.line(price_df, x="date", y="close", title=f"{stock} Close")
            st.plotly_chart(fig_line, use_container_width=True)

        # Live price tile
        live_row = get_live_stock_prices([stock])
        if not live_row.empty:
            lp = live_row.iloc[0]
            st.metric(f"{stock} Live Price",
                      f"₹{lp['price']:,.2f}",
                      f"{lp['change_pct']:+.2f}% today")
    else:
        st.warning("Price data not found. Run ETL first.")

# ── TAB 6: System ─────────────────────────────────────────────────────────────
with tabs[6]:
    st.subheader("System Status")

    # File presence checks
    checks = {
        "Price data":    any(glob.glob("data/prices/*.parquet")),
        "Feature data":  os.path.exists("data/features/features.parquet"),
        "Signal data":   any(glob.glob("data/signals/*.parquet")),
        "Order data":    any(glob.glob("data/orders/*.parquet")),
        "Equity curve":  os.path.exists("reports/equity_curve.csv"),
        "Metrics JSON":  os.path.exists("reports/metrics.json"),
    }

    sc = st.columns(3)
    for i, (name, ok) in enumerate(checks.items()):
        sc[i % 3].metric(name, "OK" if ok else "Missing",
                         delta="✓" if ok else "Run pipeline",
                         delta_color="normal" if ok else "inverse")

    # Latest signal date
    sigs = load_latest_parquet("data/signals")
    if sigs is not None and "date" in sigs.columns:
        lat = pd.to_datetime(sigs["date"]).max()
        st.info(f"Latest signal date: **{lat.date()}**  —  "
                f"{'Today' if lat.date() == datetime.date.today() else str((datetime.date.today() - lat.date()).days) + ' days ago'}")

    st.divider()
    st.subheader("System Log (last 30 lines)")
    log_file = "logs/system.log"
    if os.path.exists(log_file):
        with open(log_file, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        st.code("".join(lines[-30:]), language="bash")
    else:
        st.warning("No log file found. Run the pipeline once.")