"""Cached data loaders shared by all pages (one cache for the whole app)."""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st

from src import fundamentals as fd
from src.data import load_prices
from src.indicators import add_indicators
from src.model import BacktestResult, train_and_backtest
from src.scoring import piotroski
from src.universe import load_set100, yahoo_symbol


@st.cache_data(ttl="24h")
def set100() -> pd.DataFrame:
    return load_set100()


@st.cache_data(ttl="15m", show_spinner="Loading SET100 prices and valuations...")
def snapshots() -> pd.DataFrame:
    # Raises fd.SnapshotError when too many symbols fail. st.cache_data does not cache
    # exceptions, so a short outage is retried on the next rerun instead of sticking for 15 min.
    return fd.check_snapshot_coverage(fd.get_snapshots(set100()["symbol"].tolist()))


@st.cache_data(ttl="15m", max_entries=100)
def snapshot(symbol: str) -> pd.DataFrame:
    """The snapshot of one stock outside SET100 (same columns as `snapshots`; NaN price if Yahoo has no data)."""
    return fd.get_snapshots([symbol])


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
def unadjusted_close(symbol: str) -> pd.Series:
    """Daily close as traded (not adjusted for dividends), last 15 years. Raises NoPriceData."""
    # Not "max" or "20y": Yahoo returned no data at all for PTT.BK and ADVANC.BK with those (checked 2026-11-21).
    df = load_prices(yahoo_symbol(symbol), "15y", adjusted=False)
    if df.empty:
        raise NoPriceData(f"Could not download prices for {symbol}. Try again in a moment.")
    return df["Close"]


@st.cache_data(ttl="24h", max_entries=100)
def financials(symbol: str) -> pd.DataFrame:
    return fd.get_financials(symbol)


@st.cache_data(ttl="24h", show_spinner="Loading 5-year growth for SET100 (about 10 seconds, once a day)...")
def growth() -> pd.DataFrame:
    """Per SET100 stock: 5-year revenue / net-income CAGR, average ROE and the Piotroski F-score (points, available)."""
    def one(symbol: str) -> dict:
        try:
            fin = fd.get_financials(symbol)
        except Exception:  # both sources down for this stock: blank figures, the screener still shows it
            fin = pd.DataFrame(columns=fd.FIN_COLUMNS)
        score = piotroski(fin)
        return {"symbol": symbol, **fd.growth_quality(fin), "fscore": score.points, "fscore_available": score.available}

    with ThreadPoolExecutor(max_workers=8) as pool:
        return pd.DataFrame(list(pool.map(one, set100()["symbol"].tolist())))


@st.cache_data(ttl="24h", max_entries=100)
def dividends(symbol: str) -> pd.Series:
    return fd.get_dividends_per_year(symbol)


@st.cache_data(ttl="24h", max_entries=50)
def backtest(symbol: str) -> BacktestResult:
    return train_and_backtest(prices(symbol, "5y"))


def snapshot_of(symbol: str) -> pd.Series:
    """The current snapshot of any symbol: from the shared SET100 table, or its own fetch if outside SET100.

    Raises fd.SnapshotError if Yahoo has no price for it (or too many SET100 fetches failed).
    """
    snaps = snapshots() if symbol in set(set100()["symbol"]) else snapshot(symbol)
    return fd.snapshot_for(snaps, symbol)
