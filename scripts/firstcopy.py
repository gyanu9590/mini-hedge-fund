# file: app_streamlit.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import statsmodels.api as sm          # optional: for OLS summary
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from datetime import datetime
def run():

    #st.set_page_config(layout="wide", page_title="Mini Toolbox")

    # -------------------------
    # Sidebar controls
    # -------------------------
    with st.sidebar:
        st.title("Toolbox")
        start = st.date_input("From", value=pd.to_datetime("2024-01-01"))
        end = st.date_input("To", value=pd.to_datetime("today"))
        market = st.selectbox("Market (y)", ["^NSEI"])
        tickers = st.multiselect(
            "Predictors (X)",
            ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS", "CL=F", "INR=X"],
            default=["RELIANCE.NS", "HDFCBANK.NS", "CL=F"],
        )
        model_type = st.selectbox("Model", ["MLR (returns)"])
        run = st.button("RUN")

    # -------------------------
    # Helper: cached download
    # -------------------------
    @st.cache_data(ttl=60 * 30)
    def download_data(market_ticker, predictor_list, start_date, end_date):
        # Download full OHLC for market AND Close for predictors
        tickers_all = list(set([market_ticker] + predictor_list))
        data = yf.download(tickers_all, start=start_date, end=end_date, progress=False)
        # If data is empty, return None
        #print(data)
        if data is None or data.empty:
            return None
        else:
            scaler = StandardScaler()
            data.columns = pd.MultiIndex.from_tuples(data.columns)

        
        # Normalize MultiIndex if single ticker returned differently
            return data

    # -------------------------
    # Utility functions
    # -------------------------
    def prepare_returns(data, market_ticker, predictors):
        # `data` expected to be multiindex columns like ('Close', ticker)
        # Build close-only frame for tickers of interest
        if ("Close", market_ticker) in data.columns:
            close = data["Close"]
        else:
            # Sometimes yfinance returns single-level df for close column selection
            # Try fallback: if "Close" is not present, but columns are tickers directly
            if isinstance(data.columns, pd.Index) and market_ticker in data.columns:
                close = data
            else:
                raise ValueError("Can't find Close prices in downloaded data.")
        # Build returns (pct_change) on close prices
        closes = close[[market_ticker] + [t for t in predictors if t in close.columns]].dropna()
        returns = closes.pct_change(1).dropna()
        return closes, returns

    # -------------------------
    # Main run
    # -------------------------
    if run:
        if len(tickers) == 0:
            st.error("Select at least one predictor ticker.")
            st.stop()

        with st.spinner("Downloading data and preparing model..."):
            raw_data = download_data(market, tickers, start, end)

        if raw_data is None or raw_data.empty:
            st.error("No data downloaded. Check tickers or date range.")
            st.stop()

        # Prepare closes and returns
        try:
            closes, returns = prepare_returns(raw_data, market, tickers)
        except Exception as e:
            st.error(f"Failed to prepare returns: {e}")
            st.stop()

        if returns.empty or len(returns) < 20:
            st.warning("Not enough data after dropna. Choose a wider date range.")
            st.stop()

        st.subheader("Data preview (last rows)")
        st.dataframe(closes.tail(5))

        # Choose model path
        if model_type == "Logistic (direction)":
            st.info("Logistic direction model not implemented yet. Showing MLR as default.")
            # Continue with MLR for now (you can implement logistic later)

        # Build X, y
        y = returns[market]
        X = returns[[t for t in tickers if t in returns.columns]]

        # Standardize X
        scaler = StandardScaler()
        X_scaled = pd.DataFrame(scaler.fit_transform(X), index=X.index, columns=X.columns)

        # Fit linear regression
        lr = LinearRegression()
        lr.fit(X_scaled, y)

        # Predictions (same index as y)
        preds = pd.Series(lr.predict(X_scaled), index=y.index, name="predicted_return")

        # Predicted price: use previous close (align)
        # For predicted return at day t, predicted price ~ close_{t-1} * (1 + pred_t)
        prev_close = closes[market].shift(1).reindex(preds.index)
        pred_price = prev_close * (1 + preds)

        # Get market OHLC for plotting candlestick if available
        # raw_data should have multiindex columns like ('Open', ticker)
        try:
            if ("Open", market) in raw_data.columns:
                market_ohlc = raw_data.loc[:, ["Open", "High", "Low", "Close"]][market]
                market_ohlc = market_ohlc.dropna()
            else:
                # fallback: use close as flat OHLC (less ideal)
                market_ohlc = pd.DataFrame(
                    {
                        "Open": closes[market],
                        "High": closes[market],
                        "Low": closes[market],
                        "Close": closes[market],
                    }
                )
        except Exception:
            market_ohlc = pd.DataFrame(
                {
                    "Open": closes[market],
                    "High": closes[market],
                    "Low": closes[market],
                    "Close": closes[market],
                }
            )

        # -------------------------
        # Plot: Candlestick with Predicted Price
        # -------------------------
        fig = go.Figure()
        fig.add_trace(
            go.Candlestick(
                x=market_ohlc.index,
                open=market_ohlc["Open"],
                high=market_ohlc["High"],
                low=market_ohlc["Low"],
                close=market_ohlc["Close"],
                name="NIFTY (OHLC)",
            )
        )

        # Plot predicted price aligned (drop NA)
        fig.add_trace(
            go.Scatter(
                x=pred_price.dropna().index,
                y=pred_price.dropna().values,
                mode="lines",
                name="Predicted Price (approx)",
            )
        )
        fig.update_layout(height=600, margin=dict(l=10, r=10, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # -------------------------
        # Latest prediction & signal
        # -------------------------
        latest_pred = preds.iloc[-1]
        latest_pred_pct = latest_pred * 100.0
        st.metric("Predicted return (latest)", f"{latest_pred_pct:.4f} %")

        # Signal thresholds (example: 0.1% threshold)
        thr_pct = 0.1
        if latest_pred_pct > thr_pct:
            st.success("STRONG BUY")
        elif latest_pred_pct > 0:
            st.info("BUY")
        elif latest_pred_pct < -thr_pct:
            st.error("STRONG SELL")
        elif latest_pred_pct < 0:
            st.info("SELL")
        else:
            st.info("HOLD")

        # -------------------------
        # Model diagnostics
        # -------------------------
        st.subheader("Model diagnostics")

        # Coefficients correspond to standardized features (because of StandardScaler)
        coefs = pd.Series(lr.coef_, index=X_scaled.columns)
        st.write("Note: coefficients shown are for scaled features (StandardScaler).")
        st.dataframe(pd.concat([coefs.rename("coef")], axis=1))

        st.write("Intercept:", float(lr.intercept_))
        st.write("R² on training data:", float(lr.score(X_scaled, y)))

        # Plot Predicted vs Actual
        st.subheader("Predicted vs Actual Returns")
        df_compare = pd.DataFrame({"Actual": y, "Predicted": preds})
        st.line_chart(df_compare)

        # Optional: show statsmodels OLS summary (unscaled X for interpretability)
        try:
            show_ols = st.checkbox("Show OLS summary (unscaled X, for stats) - slower")
            if show_ols:
                X_ols = sm.add_constant(X)  # use raw returns (not scaled) for OLS
                ols_model = sm.OLS(y, X_ols).fit()
                st.text(ols_model.summary().as_text())
        except Exception as e:
            st.warning("Could not compute OLS summary: " + str(e))

        st.success("Run complete.")
        
        # Use explicit date to avoid ambiguity
    invest_start = pd.to_datetime("2024-01-01")   # 1 jan 2024
    # Use last date available in preds / closes as "today" in this dataset
    invest_end = preds.index.max()

    # Basic checks
    if invest_start > invest_end:
        st.warning(f"No data available between {invest_start.date()} and {invest_end.date()}. Adjust the start date.")
    else:
        # Build DataFrame with needed series (ensure alignment)
        sim = pd.DataFrame(index=preds.index)
        sim["Actual_Return"] = y.reindex(sim.index)
        sim["Predicted_Return"] = preds.reindex(sim.index)
        # Signal: 1 if predicted > 0 (buy), 0 if predicted <= 0 (stay in cash)
        sim["Signal"] = (sim["Predicted_Return"] > 0).astype(int)
        # Strategy daily return: actual return only when in market
        sim["Strategy_Return"] = sim["Actual_Return"] * sim["Signal"]

        # Filter to the requested period
        sim_period = sim.loc[(sim.index >= invest_start) & (sim.index <= invest_end)].copy()
        if sim_period.empty:
            st.warning("No overlapping dates between model predictions and the chosen start date.")
        else:
            initial_investment = 10000.0

            # Cumulative returns
            sim_period["Cum_Actual"] = (1 + sim_period["Actual_Return"]).cumprod()
            sim_period["Cum_Strategy"] = (1 + sim_period["Strategy_Return"]).cumprod()

            # Portfolio values
            sim_period["Portfolio_BuyHold"] = initial_investment * sim_period["Cum_Actual"]
            sim_period["Portfolio_Strategy"] = initial_investment * sim_period["Cum_Strategy"]

            # Final values
            final_buyhold = float(sim_period["Portfolio_BuyHold"].iloc[-1])
            final_strategy = float(sim_period["Portfolio_Strategy"].iloc[-1])
            pnl_buyhold = final_buyhold - initial_investment
            pnl_strategy = final_strategy - initial_investment
            pct_buyhold = (pnl_buyhold / initial_investment) * 100.0
            pct_strategy = (pnl_strategy / initial_investment) * 100.0

            # Performance metrics: Sharpe (annualized) and CAGR
            # Use trading days approx 252 per year
"""            if sim_period["Strategy_Return"].std() > 0:
                daily_ret = sim_period["Strategy_Return"].mean()
                daily_std = sim_period["Strategy_Return"].std()
                sharpe = (daily_ret / daily_std) * np.sqrt(252)
            else:
                sharpe = np.nan

            # CAGR (approx)
            days = (sim_period.index[-1] - sim_period.index[0]).days
            if days > 0:
                cagr_strategy = (sim_period["Cum_Strategy"].iloc[-1]) ** (365.0 / days) - 1.0
                cagr_buyhold = (sim_period["Cum_Actual"].iloc[-1]) ** (365.0 / days) - 1.0
            else:
                cagr_strategy = np.nan
                cagr_buyhold = np.nan

            # Display summary
            st.subheader(f"Simulation: {invest_start.date()} → {invest_end.date()}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Buy & Hold (final)", f"₹{final_buyhold:,.2f}", f"{pct_buyhold:.2f}%")
                st.write(f"P/L: ₹{pnl_buyhold:,.2f}")
                st.write(f"CAGR: {cagr_buyhold:.2%}" if not np.isnan(cagr_buyhold) else "CAGR: N/A")
            with col2:
                st.metric("Model Strategy (final)", f"₹{final_strategy:,.2f}", f"{pct_strategy:.2f}%")
                st.write(f"P/L: ₹{pnl_strategy:,.2f}")
                st.write(f"CAGR: {cagr_strategy:.2%}" if not np.isnan(cagr_strategy) else "CAGR: N/A")
                st.write(f"Sharpe (ann.): {sharpe:.2f}" if (not np.isnan(sharpe)) else "Sharpe: N/A")

            # Plot portfolio values
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sim_period.index, y=sim_period["Portfolio_BuyHold"],
                                    mode="lines", name="Buy & Hold"))
            fig.add_trace(go.Scatter(x=sim_period.index, y=sim_period["Portfolio_Strategy"],
                                    mode="lines", name="Model Strategy"))
            fig.update_layout(title="Portfolio Value (₹)", yaxis_title="Portfolio Value (₹)",
                            xaxis_title="Date", legend=dict(x=0, y=1))
            st.plotly_chart(fig, use_container_width=True)

            # Show table of last few rows
            st.subheader("Last 10 days (simulation)")
            st.dataframe(sim_period[["Actual_Return", "Predicted_Return", "Signal", "Strategy_Return",
                                    "Portfolio_BuyHold", "Portfolio_Strategy"]].tail(10).style.format({
                                        "Actual_Return":"{:.4%}",
                                        "Predicted_Return":"{:.4%}",
                                        "Strategy_Return":"{:.4%}",
                                        "Portfolio_BuyHold":"₹{:.2f}",
                                        "Portfolio_Strategy":"₹{:.2f}"
                                    }))"""

"""           # Directional accuracy in the period
            dir_acc = (np.sign(sim_period["Actual_Return"]) == np.sign(sim_period["Predicted_Return"])).mean() * 100.0
            st.write(f"Directional accuracy in this period: **{dir_acc:.2f}%**")
            n_days = len(sim_period)
            days_in_market = sim_period['Signal'].sum()
            pct_in_market = 100.0 * days_in_market / n_days

            # directional accuracy
            dir_acc = (np.sign(sim_period['Actual_Return']) == np.sign(sim_period['Predicted_Return'])).mean() * 100.0

            # number of trades (count signal changes)
            trades = sim_period['Signal'].diff().abs().sum()
            # approximate number of buy operations:
            num_buys = ((sim_period['Signal'].diff() == 1).sum())

            # average return while in market
            avg_return_in_market = sim_period.loc[sim_period['Signal']==1, 'Actual_Return'].mean()

            # max drawdown function
            def max_drawdown(series):
                cum = series.cummax()
                drawdown = (series - cum) / cum
                return drawdown.min()

            mdd_buy = max_drawdown(sim_period['Cum_Actual'])
            mdd_strategy = max_drawdown(sim_period['Cum_Strategy'])

            st.subheader("Trade & risk diagnostics")
            st.write(f"Days in period: {n_days}")
            st.write(f"Days in market: {int(days_in_market)} ({pct_in_market:.1f}%)")
            st.write(f"Number of trades (entries/exits): {int(trades)}")
            st.write(f"Number of buys (entries): {int(num_buys)}")
            st.write(f"Directional accuracy: {dir_acc:.2f}%")
            st.write(f"Average daily return while in market: {avg_return_in_market:.4%}")
            st.write(f"Max drawdown (Buy & Hold): {mdd_buy:.2%}")
            st.write(f"Max drawdown (Strategy): {mdd_strategy:.2%}")

            # ---- Add transaction costs (example: 0.03% per trade) ----
            tc = 0.0003  # 0.03% per trade round-trip (you can tune)
            sim_tc = sim_period.copy()
            # apply cost on every entry (when Signal goes from 0->1)
            entry_mask = sim_tc['Signal'].diff() == 1
            sim_tc.loc[entry_mask, 'Strategy_Return'] = sim_tc.loc[entry_mask, 'Strategy_Return'] - tc
            # recompute cum and portfolio
            sim_tc['Cum_Strategy_tc'] = (1 + sim_tc['Strategy_Return']).cumprod()
            sim_tc['Portfolio_Strategy_tc'] = initial_investment * sim_tc['Cum_Strategy_tc']
            st.write("Final strategy value with tx cost:", f"₹{sim_tc['Portfolio_Strategy_tc'].iloc[-1]:,.2f}")

            # ---- Show first/last 10 trade rows for inspection ----
            st.subheader("Sample trade rows (first / last 10)")
            st.dataframe(sim_period[['Actual_Return','Predicted_Return','Signal','Portfolio_Strategy']].head(10))
            st.dataframe(sim_period[['Actual_Return','Predicted_Return','Signal','Portfolio_Strategy']].tail(10))"""