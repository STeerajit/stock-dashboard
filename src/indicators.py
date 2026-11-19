"""Technical indicators added as new columns to a price DataFrame.

These columns are drawn on the chart, and are also the *features*
the prediction model learns from (see src/model.py).

Every indicator here uses only today's and past prices — never future
prices — so the model cannot "cheat" by seeing tomorrow (data leakage).
"""

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
    Every column whose name starts with "SMA" is drawn as a line on the chart.
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

    return df


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
