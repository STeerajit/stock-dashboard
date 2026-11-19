"""Streamlit dashboard. Run with:  streamlit run app.py"""

import plotly.graph_objects as go
import streamlit as st

from src.data import load_prices
from src.indicators import add_indicators

st.set_page_config(page_title="Stock Dashboard", page_icon="📈", layout="wide")
st.title("📈 Stock Dashboard")

# --- Sidebar: user inputs ---
with st.sidebar:
    ticker = st.text_input("Ticker", value="AAPL", help='Thai stocks end with ".BK", e.g. PTT.BK').strip().upper()
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)


@st.cache_data(ttl=3600)  # re-download at most once per hour per ticker/period
def get_data(ticker: str, period: str):
    return load_prices(ticker, period)


df = get_data(ticker, period)
if df.empty:
    st.error(f"No data found for **{ticker}**. Check the ticker symbol.")
    st.stop()

df = add_indicators(df)

# --- Summary numbers ---
last, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
c1, c2, c3 = st.columns(3)
c1.metric("Last close", f"{last:,.2f}", f"{(last - prev) / prev:+.2%}")
c2.metric("Period high", f"{df['High'].max():,.2f}")
c3.metric("Period low", f"{df['Low'].min():,.2f}")

# --- Candlestick chart + indicator lines ---
fig = go.Figure(
    go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=ticker)
)
for col in [c for c in df.columns if c.startswith("SMA")]:
    fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col))
fig.update_layout(height=550, xaxis_rangeslider_visible=False, margin=dict(t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Raw data"):
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
