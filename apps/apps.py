# apps/dashboard.py

import streamlit as st
import pandas as pd
from pathlib import Path
import os 
st.set_page_config(page_title="Mini Hedge Fund Dashboard", layout="wide")

st.title("📈 Mini Hedge Fund System Dashboard")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
file_path = os.path.join(BASE_DIR, "reports", "equity_curve.csv")

equity = pd.read_csv(file_path)

if not os.path.exists(file_path):
    st.warning("Run backtest first to generate equity_curve.csv")
else:
    equity = pd.read_csv(file_path)

    st.subheader("Equity Curve")
    st.line_chart(equity.set_index("date")["equity"])

    st.subheader("Raw Equity Data")
    st.dataframe(equity.tail(10))

st.info("Pipeline: ETL → Features → Signals → Backtest → Orders → Dashboard")
