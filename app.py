
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ta.momentum import RSIIndicator
from ta.trend import MACD

# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------
st.set_page_config(
    page_title="Financial Technical Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Financial Technical Analysis Dashboard")
st.markdown(
    "Compare **SPY (U.S. equities)** and **USO (oil exposure)** "
    "using price charts, technical indicators, and trading signals."
)

st.caption(
    "Educational project only. Technical signals are not guarantees "
    "of future performance and are not investment advice."
)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("Dashboard Settings")

ticker = st.sidebar.selectbox(
    "Choose an asset to analyze",
    ["SPY", "USO"]
)

period = st.sidebar.selectbox(
    "Historical period",
    ["6mo", "1y", "2y", "5y"],
    index=1
)

sma_short = st.sidebar.slider(
    "Short moving average (days)",
    min_value=5,
    max_value=50,
    value=20
)

sma_long = st.sidebar.slider(
    "Long moving average (days)",
    min_value=20,
    max_value=200,
    value=50
)

show_bollinger = st.sidebar.checkbox(
    "Show Bollinger Bands",
    value=True
)

show_signals = st.sidebar.checkbox(
    "Show Golden Cross / Death Cross",
    value=True
)

# --------------------------------------------------
# DOWNLOAD DATA
# --------------------------------------------------
@st.cache_data(ttl=3600)
def load_data(symbol, selected_period):
    data = yf.download(
        symbol,
        period=selected_period,
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    if data.empty:
        return pd.DataFrame()

    # Handle different yfinance column formats
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.loc[:, ~data.columns.duplicated()]
    data = data[["Open", "High", "Low", "Close", "Volume"]]
    data = data.dropna(subset=["Open", "High", "Low", "Close"])

    # Moving averages
    data["SMA_Short"] = data["Close"].rolling(sma_short).mean()
    data["SMA_Long"] = data["Close"].rolling(sma_long).mean()

    # Bollinger Bands: 20-day average +/- 2 standard deviations
    data["BB_Middle"] = data["Close"].rolling(20).mean()
    rolling_std = data["Close"].rolling(20).std()

    data["BB_Upper"] = data["BB_Middle"] + 2 * rolling_std
    data["BB_Lower"] = data["BB_Middle"] - 2 * rolling_std

    # RSI
    data["RSI"] = RSIIndicator(
        close=data["Close"],
        window=14
    ).rsi()

    # MACD
    macd = MACD(
        close=data["Close"],
        window_fast=12,
        window_slow=26,
        window_sign=9
    )

    data["MACD"] = macd.macd()
    data["MACD_Signal"] = macd.macd_signal()
    data["MACD_Histogram"] = macd.macd_diff()

    # Golden Cross / Death Cross
    data["Cross"] = 0
    data.loc[
        (data["SMA_Short"] > data["SMA_Long"])
        & (data["SMA_Short"].shift(1) <= data["SMA_Long"].shift(1)),
        "Cross"
    ] = 1

    data.loc[
        (data["SMA_Short"] < data["SMA_Long"])
        & (data["SMA_Short"].shift(1) >= data["SMA_Long"].shift(1)),
        "Cross"
    ] = -1

    # Illustrative RSI-based signals
    data["Buy_Signal"] = (
        (data["RSI"] < 30)
        & (data["RSI"].shift(1) >= 30)
    )

    data["Sell_Signal"] = (
        (data["RSI"] > 70)
        & (data["RSI"].shift(1) <= 70)
    )

    return data


with st.spinner(f"Loading {ticker} market data..."):
    df = load_data.clear() if False else None
    data = load_data(ticker, period)

# --------------------------------------------------
# ERROR HANDLING
# --------------------------------------------------
if data.empty:
    st.error(
        "No market data was returned. Check your internet connection "
        "or try a different historical period."
    )
    st.stop()

# --------------------------------------------------
# KEY METRICS
# --------------------------------------------------
latest_close = data["Close"].iloc[-1]
previous_close = data["Close"].iloc[-2] if len(data) > 1 else latest_close
daily_change = (
    (latest_close / previous_close - 1) * 100
    if previous_close != 0 else 0
)

first_close = data["Close"].iloc[0]
period_return = (
    (latest_close / first_close - 1) * 100
    if first_close != 0 else 0
)

latest_rsi = data["RSI"].iloc[-1]
latest_rsi_text = (
    f"{latest_rsi:.2f}"
    if pd.notna(latest_rsi) else "N/A"
)

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    f"{ticker} Latest Price",
    f"${latest_close:,.2f}",
    f"{daily_change:+.2f}%"
)

metric2.metric(
    "Period Return",
    f"{period_return:+.2f}%"
)

metric3.metric(
    "Latest RSI",
    latest_rsi_text
)

metric4.metric(
    "Latest Trading Volume",
    f"{data['Volume'].iloc[-1]:,.0f}"
)

st.divider()

# --------------------------------------------------
# CANDLESTICK CHART
# --------------------------------------------------
st.subheader(f"{ticker} Price and Technical Indicators")

fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name="Candlesticks"
    )
)

fig.add_trace(
    go.Scatter(
        x=data.index,
        y=data["SMA_Short"],
        mode="lines",
        name=f"SMA {sma_short}",
        line=dict(color="orange", width=1.5)
    )
)

fig.add_trace(
    go.Scatter(
        x=data.index,
        y=data["SMA_Long"],
        mode="lines",
        name=f"SMA {sma_long}",
        line=dict(color="royalblue", width=1.5)
    )
)

if show_bollinger:
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["BB_Upper"],
            mode="lines",
            name="Bollinger Upper",
            line=dict(color="gray", dash="dot", width=1),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["BB_Lower"],
            mode="lines",
            name="Bollinger Lower",
            line=dict(color="gray", dash="dot", width=1),
            fill="tonexty",
            fillcolor="rgba(128,128,128,0.08)"
        )
    )

if show_signals:
    golden_cross = data[data["Cross"] == 1]
    death_cross = data[data["Cross"] == -1]

    fig.add_trace(
        go.Scatter(
            x=golden_cross.index,
            y=golden_cross["Close"],
            mode="markers",
            name="Golden Cross",
            marker=dict(symbol="triangle-up", size=12, color="green")
        )
    )

    fig.add_trace(
        go.Scatter(
            x=death_cross.index,
            y=death_cross["Close"],
            mode="markers",
            name="Death Cross",
            marker=dict(symbol="triangle-down", size=12, color="red")
        )
    )

buy_points = data[data["Buy_Signal"]]
sell_points = data[data["Sell_Signal"]]

fig.add_trace(
    go.Scatter(
        x=buy_points.index,
        y=buy_points["Close"],
        mode="markers",
        name="RSI Buy Signal",
        marker=dict(symbol="star", size=11, color="green")
    )
)

fig.add_trace(
    go.Scatter(
        x=sell_points.index,
        y=sell_points["Close"],
        mode="markers",
        name="RSI Sell Signal",
        marker=dict(symbol="x", size=10, color="red")
    )
)

fig.update_layout(
    height=600,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# RSI CHART
# --------------------------------------------------
st.subheader("Relative Strength Index (RSI)")

rsi_fig = go.Figure()

rsi_fig.add_trace(
    go.Scatter(
        x=data.index,
        y=data["RSI"],
        name="RSI",
        line=dict(color="mediumpurple", width=2)
    )
)

rsi_fig.add_hline(
    y=70,
    line_dash="dash",
    line_color="red",
    annotation_text="Overbought (70)"
)

rsi_fig.add_hline(
    y=30,
    line_dash="dash",
    line_color="green",
    annotation_text="Oversold (30)"
)

rsi_fig.update_layout(
    height=300,
    template="plotly_dark",
    yaxis=dict(range=[0, 100]),
    hovermode="x unified"
)

st.plotly_chart(rsi_fig, use_container_width=True)

# --------------------------------------------------
# MACD CHART
# --------------------------------------------------
st.subheader("Moving Average Convergence Divergence (MACD)")

macd_fig = make_subplots(specs=[[{"secondary_y": False}]])

macd_fig.add_trace(
    go.Scatter(
        x=data.index,
        y=data["MACD"],
        name="MACD",
        line=dict(color="cyan", width=2)
    )
)

macd_fig.add_trace(
    go.Scatter(
        x=data.index,
        y=data["MACD_Signal"],
        name="Signal Line",
        line=dict(color="orange", width=2)
    )
)

macd_fig.add_trace(
    go.Bar(
        x=data.index,
        y=data["MACD_Histogram"],
        name="Histogram"
    )
)

macd_fig.add_hline(y=0, line_dash="dash", line_color="gray")

macd_fig.update_layout(
    height=350,
    template="plotly_dark",
    hovermode="x unified"
)

st.plotly_chart(macd_fig, use_container_width=True)

# --------------------------------------------------
# SPY VS USO PERFORMANCE COMPARISON
# --------------------------------------------------
st.divider()
st.subheader("SPY vs. USO: Relative Performance")

with st.spinner("Comparing SPY and USO..."):
    comparison = yf.download(
        ["SPY", "USO"],
        period=period,
        auto_adjust=True,
        progress=False
    )

if not comparison.empty:
    if isinstance(comparison.columns, pd.MultiIndex):
        close_prices = comparison["Close"]
    else:
        close_prices = pd.DataFrame()

    if {"SPY", "USO"}.issubset(close_prices.columns):
        close_prices = close_prices[["SPY", "USO"]].dropna()

        if not close_prices.empty:
            normalized = close_prices.div(close_prices.iloc[0]).mul(100)

            comparison_fig = go.Figure()

            comparison_fig.add_trace(
                go.Scatter(
                    x=normalized.index,
                    y=normalized["SPY"],
                    name="SPY",
                    mode="lines"
                )
            )

            comparison_fig.add_trace(
                go.Scatter(
                    x=normalized.index,
                    y=normalized["USO"],
                    name="USO",
                    mode="lines"
                )
            )

            comparison_fig.update_layout(
                title="Growth of $100 (Normalized to 100)",
                yaxis_title="Indexed Value",
                xaxis_title="Date",
                height=400,
                template="plotly_dark",
                hovermode="x unified"
            )

            st.plotly_chart(
                comparison_fig,
                use_container_width=True
            )
        else:
            st.warning("Not enough overlapping data to compare SPY and USO.")
    else:
        st.warning("Could not identify both SPY and USO closing prices.")
else:
    st.warning("Could not download the SPY vs. USO comparison data.")

# --------------------------------------------------
# SIGNAL SUMMARY AND DATA
# --------------------------------------------------
st.divider()
st.subheader("Latest Technical Summary")

last_row = data.iloc[-1]

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Moving Average Trend**")

    if pd.isna(last_row["SMA_Short"]) or pd.isna(last_row["SMA_Long"]):
        st.info("Not enough data to calculate both moving averages.")
    elif last_row["SMA_Short"] > last_row["SMA_Long"]:
        st.success("Short moving average is above the long moving average.")
    else:
        st.warning("Short moving average is below the long moving average.")

with col2:
    st.markdown("**RSI Interpretation**")

    if pd.isna(last_row["RSI"]):
        st.info("RSI is not available.")
    elif last_row["RSI"] >= 70:
        st.warning("RSI is at or above 70: potentially overbought.")
    elif last_row["RSI"] <= 30:
        st.success("RSI is at or below 30: potentially oversold.")
    else:
        st.info("RSI is between 30 and 70.")

st.subheader("Recent Market Data")

display_columns = [
    "Open", "High", "Low", "Close", "Volume",
    "SMA_Short", "SMA_Long", "RSI", "MACD"
]

st.dataframe(
    data[display_columns].tail(15).round(2),
    use_container_width=True
)

st.caption(
    "Data source: Yahoo Finance via yfinance. "
    "Prices and indicators depend on the data available when the app runs. "
    "Signals are illustrative rules, not a tested trading strategy."
)