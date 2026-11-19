"""Download stock price data from Yahoo Finance."""

import pandas as pd
import yfinance as yf


def load_prices(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Return daily OHLCV prices for `ticker` (e.g. "AAPL", "PTT.BK").

    Columns: Open, High, Low, Close, Volume. Index: Date.
    Returns an empty DataFrame if the ticker is unknown.
    """
    df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False)
    if df.empty:
        return df
    # yfinance returns 2-level columns like ("Close", "AAPL") — keep only the first level.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
