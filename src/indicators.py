"""Technical indicators added as new columns to a price DataFrame.

These columns are drawn on the chart, and are also the *features*
the prediction model learns from (see src/model.py).

Every indicator here uses only today's and past prices — never future
prices — so the model cannot "cheat" by seeing tomorrow (data leakage).
"""

import numpy as np
import pandas as pd


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (0-100). Above 70 = 'overbought', below 30 = 'oversold'."""
    change = close.diff()
    gain = change.clip(lower=0).ewm(alpha=1 / window, min_periods=window).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1 / window, min_periods=window).mean()
    return 100 - 100 / (1 + gain / loss)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with indicator columns added.

    Input columns: Open, High, Low, Close, Volume.
    SMA20 and SMA50 are always drawn on the chart; SMA200, the Bollinger bands, MACD and OBV can be switched on.
    """
    df = df.copy()
    close = df["Close"]

    # Short and long moving averages: short reacts fast, long shows the big trend.
    df["SMA20"] = close.rolling(window=20).mean()
    df["SMA50"] = close.rolling(window=50).mean()

    df["Return"] = close.pct_change()  # daily return, 0.01 = +1%
    df["Volatility20"] = df["Return"].rolling(20).std()  # how "jumpy" the price is
    df["RSI14"] = rsi(close, 14)
    df["Volume_change"] = df["Volume"].pct_change()

    df["SMA200"] = close.rolling(window=200).mean()  # the long trend; ~ the 10-month average (Faber 2007)

    # MACD 12/26/9: the gap between a fast and a slow average shows short-term momentum turning.
    df["MACD"] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Bollinger bands 20/2: how far the price has swung from its usual range.
    band = 2 * close.rolling(window=20).std(ddof=0)
    df["BB_upper"], df["BB_lower"] = df["SMA20"] + band, df["SMA20"] - band

    # On-balance volume: volume added on up days, subtracted on down days; compared with its 20-day average.
    df["OBV"] = (np.sign(close.diff()).fillna(0) * df["Volume"]).cumsum()
    df["OBV_SMA20"] = df["OBV"].rolling(window=20).mean()

    return df


def sma_10_month(close: pd.Series) -> pd.DataFrame:
    """Month-end close and its 10-month simple average (Faber 2007: checked once a month, on the last day).

    The current, unfinished month counts with its latest close, like a month-end check made today.
    """
    month_end = close.groupby(pd.DatetimeIndex(close.index).to_period("M")).last()
    month_end.index = pd.PeriodIndex(month_end.index).to_timestamp(how="end").normalize()
    return pd.DataFrame({"Close": month_end, "SMA10M": month_end.rolling(10).mean()})


def support_resistance(df: pd.DataFrame, window: int = 10, tolerance: float = 0.02) -> tuple[list, list]:
    """Find simple support (below price) and resistance (above price) levels.

    A swing high/low is a day whose High/Low is the extreme of the surrounding
    `window` days on each side. Swing points within `tolerance` (2%) of each other
    are merged into one level. Returns (supports, resistances), nearest first, max 3 each.
    """
    span = 2 * window + 1
    highs = df["High"][df["High"] == df["High"].rolling(span, center=True).max()]
    lows = df["Low"][df["Low"] == df["Low"].rolling(span, center=True).min()]

    levels: list[float] = []
    for p in sorted(pd.concat([highs, lows]).tolist()):
        if levels and p <= levels[-1] * (1 + tolerance):
            levels[-1] = (levels[-1] + p) / 2  # merge with the previous, close-by level
        else:
            levels.append(p)

    price = df["Close"].iloc[-1]
    supports = sorted([lv for lv in levels if lv < price], reverse=True)[:3]
    resistances = sorted([lv for lv in levels if lv > price])[:3]
    return supports, resistances
