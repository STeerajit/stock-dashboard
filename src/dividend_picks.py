"""Dividend Picks: 10 dividend stocks worth holding, from SET100 (see docs/research/dividend-picks.md).

Steps, each from the research notes:
1. Keep the 50 stocks with the lowest volatility of weekly returns over 156 weeks (Conservative Formula).
2. Drop dividend traps: no dividend in any of the last 5 calendar years, payout above 100% (SETHD rules),
   EPS negative or down 3 years in a row.
3. Rank the rest by the average of their net-payout-yield rank and 12-1 month momentum rank; keep the top 10.

Pure functions with an `as_of` date: only data known on that date is used, so the same code serves today's
list, yesterday's list (what entered or left) and every month of the backtest.
"""

from typing import NamedTuple

import numpy as np
import pandas as pd

LOW_VOL_KEEP = 50
VOL_WEEKS = 156
DIVIDEND_YEARS = 5
MAX_PAYOUT = 1.0
EPS_DECLINE_YEARS = 3
PICKS = 10
# Buybacks are left out of net payout yield for now: our only share count (thaifin's year-end market cap / close)
# jumps by 10-25% between years when no shares changed (PTT, PRM), which would swamp the dividend yield.
USE_BUYBACKS = False
REPORT_LAG = pd.DateOffset(months=3)  # a year's statements count as published 3 months after the year ends

# Why a stock is not ranked. "ok" = it passed every step and has a rank.
STAGES = ("ok", "no_data", "high_vol", "no_dividend", "payout", "eps_negative", "eps_declining")


class StockData(NamedTuple):
    prices: pd.DataFrame  # daily OHLCV adjusted for dividends (src.store.load_prices)
    close: pd.Series  # daily close as traded, not adjusted (for yields)
    dividends: pd.Series  # cash dividend per share, one row per XD date, as traded
    financials: pd.DataFrame  # yearly figures (src.fundamentals.FIN_COLUMNS), index = year


def _until(s, as_of: pd.Timestamp):
    return s[s.index <= as_of]


def published_financials(fin: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Only the years whose statements were out on `as_of` (year end + 3 months)."""
    if fin.empty:
        return fin
    known = [y for y in fin.index if pd.Timestamp(int(y), 12, 31) + REPORT_LAG <= as_of]
    return fin.loc[known]


def weekly_volatility(prices: pd.DataFrame, as_of: pd.Timestamp) -> float:
    """Standard deviation of the last 156 weekly returns; NaN with less history."""
    weekly = _until(prices["Close"], as_of).resample("W-FRI").last().dropna().pct_change().dropna()
    return float(weekly.tail(VOL_WEEKS).std()) if len(weekly) >= VOL_WEEKS else float("nan")


def _price_on(series: pd.Series, day: pd.Timestamp) -> float:
    before = series[series.index <= day]
    return float(before.iloc[-1]) if len(before) else float("nan")


def momentum_12_1(prices: pd.DataFrame, as_of: pd.Timestamp) -> float:
    """Return from 12 months ago to 1 month ago (the latest month is left out)."""
    close = _until(prices["Close"], as_of)
    if close.empty or close.index[0] > as_of - pd.DateOffset(months=12):
        return float("nan")
    return _price_on(close, as_of - pd.DateOffset(months=1)) / _price_on(close, as_of - pd.DateOffset(months=12)) - 1


def trailing_dividends(dividends: pd.Series, as_of: pd.Timestamp) -> float:
    """Dividends per share with an XD date in the 12 months up to `as_of`."""
    d = _until(dividends, as_of)
    return float(d[d.index > as_of - pd.DateOffset(months=12)].sum())


def paid_every_year(dividends: pd.Series, as_of: pd.Timestamp, years: int = DIVIDEND_YEARS) -> bool:
    """A dividend went XD in each of the last `years` complete calendar years."""
    d = _until(dividends, as_of)
    paid = set(pd.DatetimeIndex(d[d > 0].index).year)
    return all(y in paid for y in range(as_of.year - years, as_of.year))


def buyback_yield(fin: pd.DataFrame) -> float:
    """Share count change over the last published year, as a yield: fewer shares (a buyback) = positive.
    0 when the share count is not known for two years (no buyback assumed)."""
    shares = fin["Shares"].dropna() if "Shares" in fin else pd.Series(dtype=float)
    if len(shares) < 2 or shares.iloc[-2] <= 0:
        return 0.0
    return float(-(shares.iloc[-1] / shares.iloc[-2] - 1))


def _eps_declining(eps: pd.Series) -> bool:
    last = eps.dropna().tail(EPS_DECLINE_YEARS + 1)
    return len(last) == EPS_DECLINE_YEARS + 1 and bool((last.diff().dropna() < 0).all())


def screen(data: dict[str, StockData], as_of) -> pd.DataFrame:
    """Every symbol with its figures on `as_of`, the step it stopped at (`stage`, see STAGES) and,
    if it passed every step, its `rank` (1 = best). Sorted by rank, unranked last."""
    as_of = pd.Timestamp(as_of)
    rows = []
    for symbol, d in data.items():
        fin = published_financials(d.financials, as_of)
        eps = fin["EPS"].dropna() if "EPS" in fin else pd.Series(dtype=float)
        price = _price_on(d.close, as_of)
        dps = trailing_dividends(d.dividends, as_of)
        div_yield = dps / price if price > 0 else float("nan")
        latest_eps = float(eps.iloc[-1]) if len(eps) else float("nan")
        rows.append({
            "symbol": symbol,
            "volatility": weekly_volatility(d.prices, as_of),
            "div_yield": div_yield,
            "buyback_yield": buyback_yield(fin),
            "momentum": momentum_12_1(d.prices, as_of),
            "payout": dps / latest_eps if latest_eps > 0 else float("nan"),
            "eps": latest_eps,
            "paid_5y": paid_every_year(d.dividends, as_of),
            "eps_declining": _eps_declining(eps),
        })
    df = pd.DataFrame(rows, columns=["symbol", "volatility", "div_yield", "buyback_yield", "momentum", "payout",
                                     "eps", "paid_5y", "eps_declining"])
    df["net_payout_yield"] = df["div_yield"] + (df["buyback_yield"] if USE_BUYBACKS else 0.0)

    df["stage"] = "ok"
    df.loc[df[["volatility", "net_payout_yield", "momentum"]].isna().any(axis=1), "stage"] = "no_data"
    has_vol = df["stage"] == "ok"
    low_vol = df[has_vol].nsmallest(LOW_VOL_KEEP, "volatility").index
    df.loc[has_vol & ~df.index.isin(low_vol), "stage"] = "high_vol"
    # Traps, in the order shown to users; a stock gets the first rule it fails.
    for stage, fails in (("no_dividend", ~df["paid_5y"]),
                         ("eps_negative", ~(df["eps"] > 0)),
                         ("payout", df["payout"] > MAX_PAYOUT),
                         ("eps_declining", df["eps_declining"])):
        df.loc[(df["stage"] == "ok") & fails, "stage"] = stage

    ok = df["stage"] == "ok"
    score = (df.loc[ok, "net_payout_yield"].rank(ascending=False) + df.loc[ok, "momentum"].rank(ascending=False)) / 2
    df["score"] = score
    # Ties in the average rank go to the higher net payout yield (the income investor's main figure).
    order = df[ok].assign(score=score).sort_values(["score", "net_payout_yield"], ascending=[True, False]).index
    df["rank"] = pd.Series(np.arange(1, len(order) + 1), index=order).astype("Int64")
    return df.sort_values("rank", na_position="last").reset_index(drop=True)


def picks(screened: pd.DataFrame, n: int = PICKS) -> list[str]:
    """The top `n` ranked symbols, best first."""
    return screened.dropna(subset=["rank"]).nsmallest(n, "rank")["symbol"].tolist()


def changes(today: list[str], yesterday: list[str]) -> tuple[list[str], list[str]]:
    """(entered, left): symbols new in today's list, and symbols in yesterday's list but not today's."""
    return [s for s in today if s not in yesterday], [s for s in yesterday if s not in today]


def equal_weight_index(data: dict[str, StockData]) -> pd.Series:
    """An equal-weighted SET100 index (start = 100) from the stocks' dividend-adjusted closes.

    Stands in for the SET index, whose history Yahoo Finance does not provide (only today's value,
    checked 2026-11-21). Each day is the average daily return of the stocks that traded that day.
    """
    closes = pd.DataFrame({s: d.prices["Close"] for s, d in data.items()})
    returns = closes.pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0.0)
    return 100 * (1 + returns).cumprod()
