"""Cached data loaders shared by all pages (one cache for the whole app)."""

import pandas as pd
import streamlit as st

from src import fundamentals as fd
from src.data import load_prices
from src.indicators import add_indicators
from src.model import BacktestResult, train_and_backtest
from src.universe import load_set50, yahoo_symbol


@st.cache_data(ttl="24h")
def set50() -> pd.DataFrame:
    return load_set50()


@st.cache_data(ttl="15m", show_spinner="Loading SET50 prices and valuations...")
def snapshots() -> pd.DataFrame:
    # Raises fd.SnapshotError when too many symbols fail. st.cache_data does not cache
    # exceptions, so a short outage is retried on the next rerun instead of sticking for 15 min.
    return fd.check_snapshot_coverage(fd.get_snapshots(set50()["symbol"].tolist()))


class NoPriceData(RuntimeError):
    pass


@st.cache_data(ttl="1h", max_entries=100)
def prices(symbol: str, period: str = "5y") -> pd.DataFrame:
    df = load_prices(yahoo_symbol(symbol), period)
    if df.empty:
        # Raising (instead of returning empty) means a network blip is NOT cached for an hour.
        raise NoPriceData(f"Could not download prices for {symbol}. Try again in a moment.")
    return add_indicators(df)


@st.cache_data(ttl="24h", max_entries=100)
def financials(symbol: str) -> pd.DataFrame:
    return fd.get_financials(symbol)


@st.cache_data(ttl="24h", max_entries=100)
def dividends(symbol: str) -> pd.Series:
    return fd.get_dividends_per_year(symbol)


@st.cache_data(ttl="24h", max_entries=50)
def backtest(symbol: str) -> BacktestResult:
    return train_and_backtest(prices(symbol, "5y"))
