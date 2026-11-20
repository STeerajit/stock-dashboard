"""Cached data loaders shared by all pages (one cache for the whole app).

When the local store (data/market.duckdb, see src/store.py) has a stock, its data is read from there: fast,
and it works offline. Stocks not in the store (e.g. outside SET100), or no store at all, come from the network.
"""

from concurrent.futures import ThreadPoolExecutor

import duckdb
import pandas as pd
import streamlit as st

from src import fundamentals as fd
from src import store
from src.data import load_prices
from src.indicators import add_indicators
from src.model import BacktestResult, train_and_backtest
from src.scoring import piotroski
from src.universe import load_set100, yahoo_symbol


def _stored(symbol: str) -> bool:
    try:
        return store.has(store.STORE_PATH, symbol)
    except duckdb.Error:  # e.g. the file is locked by a running update: use the network meanwhile
        return False


def _last_years(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Rows of the last N years for a period like "5y" (the format load_prices takes)."""
    years = int(period.rstrip("y"))
    return df[df.index > df.index[-1] - pd.DateOffset(years=years)] if not df.empty else df


@st.cache_data(ttl="24h")
def set100() -> pd.DataFrame:
    return load_set100()


@st.cache_data(ttl="15m", show_spinner="Loading SET100 prices and valuations...")
def snapshots() -> pd.DataFrame:
    # Raises fd.SnapshotError when too many symbols fail. st.cache_data does not cache
    # exceptions, so a short outage is retried on the next rerun instead of sticking for 15 min.
    symbols = set100()["symbol"].tolist()
    try:
        if store.as_of(store.STORE_PATH):
            return fd.check_snapshot_coverage(store.load_snapshots(store.STORE_PATH, symbols))
    except duckdb.Error:
        pass
    return fd.check_snapshot_coverage(fd.get_snapshots(symbols))


@st.cache_data(ttl="15m", max_entries=100)
def snapshot(symbol: str) -> pd.DataFrame:
    """The snapshot of one stock outside SET100 (same columns as `snapshots`; NaN price if Yahoo has no data)."""
    return fd.get_snapshots([symbol])


class NoPriceData(RuntimeError):
    pass


@st.cache_data(ttl="1h", max_entries=100)
def prices(symbol: str, period: str = "5y") -> pd.DataFrame:
    if _stored(symbol):
        df = _last_years(store.load_prices(store.STORE_PATH, symbol), period)
    else:
        df = load_prices(yahoo_symbol(symbol), period)
    if df.empty:
        # Raising (instead of returning empty) means a network blip is NOT cached for an hour.
        raise NoPriceData(f"Could not download prices for {symbol}. Try again in a moment.")
    return add_indicators(df)


@st.cache_data(ttl="24h", max_entries=100)
def unadjusted_close(symbol: str) -> pd.Series:
    """Daily close as traded (not adjusted for dividends), last 15 years. Raises NoPriceData."""
    if _stored(symbol):
        close = store.load_close(store.STORE_PATH, symbol)
    else:
        # Not "max" or "20y": Yahoo returned no data at all for PTT.BK and ADVANC.BK with those (checked 2026-11-21).
        close = load_prices(yahoo_symbol(symbol), "15y", adjusted=False).get("Close", pd.Series(dtype=float))
    if close.empty:
        raise NoPriceData(f"Could not download prices for {symbol}. Try again in a moment.")
    return close


def _financials(symbol: str) -> pd.DataFrame:
    if _stored(symbol):
        fin = store.load_financials(store.STORE_PATH, symbol)
        if not fin.empty:
            return fin
    return fd.get_financials(symbol)


@st.cache_data(ttl="24h", max_entries=100)
def financials(symbol: str) -> pd.DataFrame:
    return _financials(symbol)


@st.cache_data(ttl="24h", show_spinner="Loading 5-year growth for SET100 (about 10 seconds, once a day)...")
def growth() -> pd.DataFrame:
    """Per SET100 stock: 5-year revenue / net-income CAGR, average ROE and the Piotroski F-score (points, available)."""
    def one(symbol: str) -> dict:
        try:
            fin = _financials(symbol)
        except Exception:  # both sources down for this stock: blank figures, the screener still shows it
            fin = pd.DataFrame(columns=fd.FIN_COLUMNS)
        score = piotroski(fin)
        return {"symbol": symbol, **fd.growth_quality(fin), "fscore": score.points, "fscore_available": score.available}

    with ThreadPoolExecutor(max_workers=8) as pool:
        return pd.DataFrame(list(pool.map(one, set100()["symbol"].tolist())))


@st.cache_data(ttl="24h", max_entries=100)
def dividends(symbol: str) -> pd.Series:
    if _stored(symbol):
        return store.load_dividends_per_year(store.STORE_PATH, symbol)
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
