"""Fake data sources shared by tests — nothing here touches the network."""

import numpy as np
import pandas as pd


def fake_info(price: float = 100.0) -> dict:
    """A Yahoo Finance `Ticker.info` dict with the fields get_snapshot reads."""
    return {
        "currentPrice": price, "previousClose": price * 0.99, "volume": 1_000_000, "averageVolume": 800_000,
        "bid": price - 0.25, "ask": price + 0.25, "fiftyTwoWeekHigh": price * 1.2, "fiftyTwoWeekLow": price * 0.8,
        "marketCap": 1e11, "trailingPE": 12.0, "priceToBook": 1.5, "dividendYield": 4.0,
        "returnOnEquity": 0.12, "debtToEquity": 80.0, "profitMargins": 0.1,
        "exDividendDate": 1_790_000_000, "earningsTimestamp": None,
        "floatShares": 400_000_000, "sharesOutstanding": 1_000_000_000,
    }


def fake_prices(n: int = 600, seed: int = 0, start: str = "2021-01-01") -> pd.DataFrame:
    """Daily OHLCV with a random walk, like src.data.load_prices returns."""
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    idx = pd.bdate_range(start, periods=n)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
         "Volume": rng.integers(1_000, 10_000, n).astype(float)},
        index=idx,
    )


class FakeTicker:
    """Stand-in for yfinance.Ticker. `failing` holds SET symbols (no ".BK") that raise like a network error."""

    failing: set[str] = set()
    down: bool = False  # True = every request fails (Yahoo outage)

    def __init__(self, symbol: str):
        self.symbol = symbol

    def _check(self):
        if FakeTicker.down or self.symbol.removesuffix(".BK") in FakeTicker.failing:
            raise ConnectionError(f"fake network error for {self.symbol}")

    @property
    def info(self) -> dict:
        self._check()
        return fake_info()

    @property
    def dividends(self) -> pd.Series:
        self._check()
        return pd.Series([1.0, 1.2, 1.5], index=pd.to_datetime(["2023-04-10", "2024-04-10", "2025-04-10"]))

    @property
    def income_stmt(self) -> pd.DataFrame:
        self._check()
        cols = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31"])
        return pd.DataFrame({c: {"Total Revenue": 1e9 * (3 - i), "Net Income": 1e8 * (3 - i), "Diluted EPS": 3.0 - i,
                                 "Gross Profit": 4e8 * (3 - i)} for i, c in enumerate(cols)})

    @property
    def balance_sheet(self) -> pd.DataFrame:
        self._check()
        cols = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31"])
        return pd.DataFrame({c: {"Stockholders Equity": 1e9, "Total Debt": 5e8} for c in cols})

    @property
    def cashflow(self) -> pd.DataFrame:
        self._check()
        cols = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31"])
        return pd.DataFrame({c: {"Free Cash Flow": 2e8} for c in cols})


def fake_download(ticker, *args, **kwargs) -> pd.DataFrame:
    """Stand-in for yfinance.download."""
    if FakeTicker.down:
        return pd.DataFrame()
    return fake_prices(n=1300, start="2021-01-01")
