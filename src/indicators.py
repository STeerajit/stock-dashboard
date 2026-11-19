"""Technical indicators added as new columns to a price DataFrame.

These columns are drawn on the chart now, and later become the
*features* the prediction model learns from (step 2).
"""

import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with indicator columns added.

    Input columns: Open, High, Low, Close, Volume.
    Every column whose name starts with "SMA" is drawn as a line on the chart.
    """
    df = df.copy()

    # TODO(you): add the indicators you want, 5-10 lines.
    # Useful pandas tools:
    #   df["Close"].rolling(window=20).mean()   -> Simple Moving Average (SMA)
    #   df["Close"].pct_change()                -> daily return (0.01 = +1%)
    #   df["Close"].rolling(20).std()           -> volatility
    # Example:
    #   df["SMA20"] = df["Close"].rolling(window=20).mean()

    return df
