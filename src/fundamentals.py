"""Trading snapshot, financial statements, valuation and dividends.

Data sources:
- Yahoo Finance (yfinance): current trading snapshot and valuation (delayed ~15 min),
  dividends, and a fallback of about 4 years of annual statements.
- thaifin: annual financial history from 2010 plus yearly P/E and P/BV (preferred source
  for get_financials).

Fields a source lacks for a stock (e.g. Yahoo's D/E for banks) are NaN.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import cast
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

from src.set_links import free_float
from src.universe import yahoo_symbol

log = logging.getLogger(__name__)


def _ts_to_date(ts):
    """Unix timestamp -> pd.Timestamp (date only), or None."""
    return pd.Timestamp(datetime.fromtimestamp(ts, tz=timezone.utc).date()) if ts else None


def get_snapshot(symbol: str) -> dict:
    """Current trading and valuation numbers for one SET symbol (e.g. "PTT")."""
    info = yf.Ticker(yahoo_symbol(symbol)).info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
    volume = info.get("volume") or info.get("regularMarketVolume")
    high52, low52 = info.get("fiftyTwoWeekHigh"), info.get("fiftyTwoWeekLow")
    dy = info.get("dividendYield")
    de = info.get("debtToEquity")
    return {
        "symbol": symbol,
        "price": price,
        "change_pct": (price / prev - 1) if price and prev else np.nan,
        "volume": volume,
        "avg_volume": info.get("averageVolume"),
        "value_traded": price * volume if price and volume else np.nan,  # baht
        "bid": info.get("bid"),
        "ask": info.get("ask"),
        "high_52w": high52,
        "low_52w": low52,
        # 0 = at the 52-week low, 1 = at the 52-week high
        "pos_52w": (price - low52) / (high52 - low52) if price and high52 and low52 and high52 > low52 else np.nan,
        "market_cap": info.get("marketCap"),
        "pe": info.get("trailingPE"),
        "pbv": info.get("priceToBook"),
        "div_yield": dy / 100 if dy is not None else np.nan,  # yfinance >= 0.2.5x returns percent
        "roe": info.get("returnOnEquity"),
        "de": de / 100 if de is not None else np.nan,  # yfinance returns D/E x100
        "net_margin": info.get("profitMargins"),
        "ex_div_date": _ts_to_date(info.get("exDividendDate")),
        "earnings_date": _ts_to_date(info.get("earningsTimestamp")),
        "free_float": free_float(info.get("floatShares"), info.get("sharesOutstanding")),  # Yahoo's estimate
    }


SNAPSHOT_COLUMNS = ["symbol", "price", "change_pct", "volume", "avg_volume", "value_traded", "bid", "ask",
                    "high_52w", "low_52w", "pos_52w", "market_cap", "pe", "pbv", "div_yield", "roe", "de",
                    "net_margin", "ex_div_date", "earnings_date", "free_float"]


class SnapshotError(RuntimeError):
    """Market data could not be loaded: for too many symbols (the data source is probably
    down), or for the one symbol a page needs. `str(e)` is a message ready to show users."""

    title = "Market data unavailable"


RETRY_HINT = "Please try again in a minute."


def get_snapshots(symbols: list[str], workers: int = 8) -> pd.DataFrame:
    """Snapshots for many symbols, fetched in parallel.

    Always returns every column in SNAPSHOT_COLUMNS, one row per symbol. A symbol whose
    fetch fails gets NaN values (its `price` is NaN), so callers never hit a KeyError.
    """

    def safe(sym: str) -> dict:
        try:
            return get_snapshot(sym)
        except Exception:
            return {"symbol": sym}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(safe, symbols))
    df = pd.DataFrame(rows).reindex(columns=SNAPSHOT_COLUMNS)
    df[["ex_div_date", "earnings_date"]] = df[["ex_div_date", "earnings_date"]].apply(pd.to_datetime)
    return df


def check_snapshot_coverage(snapshots: pd.DataFrame, max_failed: float = 0.2) -> pd.DataFrame:
    """Raise SnapshotError if more than `max_failed` of the symbols have no price; else return them unchanged."""
    failed = snapshots["price"].isna().mean() if len(snapshots) else 1.0
    if failed > max_failed:
        raise SnapshotError(
            f"Could not load market data for {failed:.0%} of stocks — Yahoo Finance may be down. {RETRY_HINT}"
        )
    return snapshots


def snapshot_for(snapshots: pd.DataFrame, symbol: str) -> pd.Series:
    """The snapshot row of one symbol. Raises SnapshotError if its fetch failed (no price)."""
    snap = cast(pd.Series, snapshots.set_index("symbol").loc[symbol])  # symbols are unique
    if pd.isna(snap["price"]):
        raise SnapshotError(f"Could not load current market data for {symbol}. {RETRY_HINT}")
    return snap


def _row(df: pd.DataFrame, name: str) -> pd.Series:
    return cast(pd.Series, df.loc[name]) if name in df.index else pd.Series(np.nan, index=df.columns)


FIN_COLUMNS = ["Revenue", "Net income", "EPS", "Revenue growth", "Net income growth", "Gross margin",
               "Net margin", "ROE", "D/E", "Free cash flow", "P/E", "P/BV"]


def get_financials(symbol: str) -> pd.DataFrame:
    """Yearly key figures, oldest year first. Index: fiscal year (int). Columns: FIN_COLUMNS.

    Tries thaifin first (~15 years, includes yearly P/E and P/BV), then falls back to
    Yahoo (~4 years). `df.attrs["source"]` and `df.attrs["de_definition"]` say which was used.
    After a fallback, `df.attrs["fallback_note"]` is a message ready to show users, so they
    know the history is shorter than usual; otherwise it is None.
    """
    try:
        fin = _financials_thaifin(symbol)
        if len(fin) >= 2:
            fin.attrs["fallback_note"] = None
            return fin
        why = f"thaifin has fewer than 2 years of statements for {symbol}"  # e.g. a new listing
    except Exception:
        # thaifin's source can be down; log it, so a bug in our own thaifin code is not hidden.
        log.warning("thaifin failed for %s; falling back to Yahoo Finance", symbol, exc_info=True)
        why = "thaifin is unavailable right now"
    fin = _financials_yahoo(symbol)
    fin.attrs["fallback_note"] = (
        f"{why}, so these figures come from Yahoo Finance and cover only {len(fin)} years "
        "instead of the usual ~15."
    )
    return fin


def _financials_thaifin(symbol: str) -> pd.DataFrame:
    from thaifin import Stock  # imported lazily: optional, heavier dependency

    raw = Stock(symbol).yearly_dataframe
    num = raw.apply(pd.to_numeric, errors="coerce")  # some cells are None
    pct = lambda col: num[col] / 100  # noqa: E731 — thaifin gives ratios in percent
    fin = pd.DataFrame(
        {
            "Revenue": num["revenue"],
            "Net income": num["net_profit"],
            "EPS": num["earning_per_share"],
            "Revenue growth": pct("revenue_yoy"),
            "Net income growth": pct("net_profit_yoy"),
            "Gross margin": pct("gpm"),
            "Net margin": pct("npm"),
            "ROE": pct("roe"),
            "D/E": num["debt_to_equity"],
            # Approximate FCF = cash from operations + cash from investing (capex is inside investing).
            "Free cash flow": num["operating_activities"] + num["investing_activities"],
            "P/E": num["price_earning_ratio"],
            "P/BV": num["price_book_value"],
            # thaifin's dividend_yield mixes units across years (e.g. PTT: 0.13 in 2010, 3.1 in 2013),
            # so it is not used. Dividend history comes from Yahoo instead (get_dividends_per_year).
        }
    )
    fin[["P/E", "P/BV"]] = fin[["P/E", "P/BV"]].replace(0, np.nan)
    fin.index = [p.year for p in raw.index]
    fin = fin.sort_index().dropna(subset=["Revenue", "Net income"], how="all").astype(float)
    fin.attrs = {"source": "thaifin", "de_definition": "Total liabilities / shareholders' equity"}
    return fin


def _financials_yahoo(symbol: str) -> pd.DataFrame:
    t = yf.Ticker(yahoo_symbol(symbol))
    inc, bal, cf = t.income_stmt, t.balance_sheet, t.cashflow
    if inc.empty:
        return pd.DataFrame(columns=FIN_COLUMNS)

    revenue, net_income = _row(inc, "Total Revenue"), _row(inc, "Net Income")
    equity = _row(bal, "Stockholders Equity").reindex(inc.columns)
    fin = pd.DataFrame(
        {
            "Revenue": revenue,
            "Net income": net_income,
            "EPS": _row(inc, "Diluted EPS").fillna(_row(inc, "Basic EPS")),
            "Gross margin": _row(inc, "Gross Profit") / revenue,
            "Net margin": net_income / revenue,
            "ROE": net_income / equity,
            "D/E": _row(bal, "Total Debt").reindex(inc.columns) / equity,
            "Free cash flow": _row(cf, "Free Cash Flow").reindex(inc.columns),
        }
    )
    fin.index = [c.year for c in fin.index]
    fin = fin.sort_index().dropna(subset=["Revenue", "Net income"], how="all")
    fin["Revenue growth"] = fin["Revenue"].pct_change()
    fin["Net income growth"] = fin["Net income"].pct_change()
    fin = fin.reindex(columns=FIN_COLUMNS).astype(float)  # P/E, P/BV history: not available
    fin.attrs = {"source": "Yahoo Finance", "de_definition": "Interest-bearing debt / shareholders' equity"}
    return fin


def get_dividends_per_year(symbol: str) -> pd.Series:
    """Cash dividend per share summed by calendar year (by XD date)."""
    div = yf.Ticker(yahoo_symbol(symbol)).dividends
    if div.empty:
        return div
    return div.groupby(pd.DatetimeIndex(div.index).year).sum()


def pe_history(prices: pd.DataFrame, financials: pd.DataFrame) -> pd.Series:
    """Approximate year-end P/E: last close of each year / that year's EPS."""
    if financials.empty:
        return pd.Series(dtype=float)
    year_end = prices["Close"].groupby(pd.DatetimeIndex(prices.index).year).last()
    eps = financials["EPS"].where(financials["EPS"] > 0)  # P/E is meaningless with losses
    return (year_end / eps).dropna()


def yield_history(dividends_per_year: pd.Series, close: pd.Series, this_year: int) -> pd.Series:
    """Yearly dividend yield (0.05 = 5%) for complete years: dividends per share with XD dates in year Y
    divided by the **unadjusted** close on the last trading day of Y.

    Runs from the first year with a dividend to last year; a year without a dividend counts as 0.
    Dividend-adjusted prices must not be used: they lower old prices and so inflate old yields.
    """
    if dividends_per_year.empty or close.empty:
        return pd.Series(dtype=float)
    year_end = close.groupby(pd.DatetimeIndex(close.index).year).last()
    years = range(int(dividends_per_year.index.min()), this_year)
    dps = dividends_per_year.reindex(years, fill_value=0.0)
    return (dps / year_end.reindex(years)).dropna()


def sector_medians(snapshots: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Median P/E, P/BV, dividend yield and ROE per sector, for peer comparison."""
    merged = universe.merge(snapshots, on="symbol")
    return pd.DataFrame(merged.groupby("sector")[["pe", "pbv", "div_yield", "roe"]].median())
