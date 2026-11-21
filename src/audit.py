"""Data checks on the local store: find figures that look wrong, so they can be checked by hand. Nothing is changed.

Thresholds were set by the project owner on 2026-11-21:
- a close that moves more than 30% in a day is suspect (SET's daily ceiling / floor is ±30%);
- two figures that should be equal count as different when they are more than 5% apart.
"""

from typing import NamedTuple

import pandas as pd

from src import quarterly as qt

MAX_DAILY_MOVE = 0.30
TOLERANCE = qt.MATCH_TOLERANCE  # 5%
SUMMED = ["EPS", "Net income", "Revenue", "Operating cash flow"]  # quarterly figures that add up to the year's


class Finding(NamedTuple):
    symbol: str
    check: str  # a short name, the same for every finding of this kind
    detail: str


class Stock(NamedTuple):
    prices: pd.DataFrame  # OHLC (store.load_prices)
    close: pd.Series  # close as traded (store.load_close)
    dividends: pd.Series  # per XD date, as traded
    yearly: pd.DataFrame  # store.load_financials
    quarterly: pd.DataFrame  # store.load_quarterly
    ex_div_date: pd.Timestamp | None  # from the latest snapshot; NaT/None when Yahoo has none


def _close_enough(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE * abs(b)


def check_prices(symbol: str, s: Stock, market_days: pd.DatetimeIndex) -> list[Finding]:
    out = []
    p = s.prices
    if p.empty:
        return [Finding(symbol, "no prices", "no price history stored")]
    bad = p[(p["High"] < p["Low"]) | (p["Close"] > p["High"]) | (p["Close"] < p["Low"])]
    if len(bad):
        out.append(Finding(symbol, "close outside high-low", f"{len(bad)} days, first {bad.index[0]:%Y-%m-%d}"))
    move = s.close.pct_change(fill_method=None).dropna()
    jumps = move[move.abs() > MAX_DAILY_MOVE + 1e-9]  # a move of exactly 30% (the daily limit) is allowed
    for day, m in zip(pd.DatetimeIndex(jumps.index), jumps):
        out.append(Finding(symbol, "daily move over 30%", f"{day:%Y-%m-%d}: {m:+.0%}"))
    days = pd.DatetimeIndex(p.index)
    expected = market_days[market_days >= days[0]]
    missing = expected.difference(days)
    if len(missing):
        out.append(Finding(symbol, "missing trading days",
                           f"{len(missing)} days other stocks traded, last {missing[-1]:%Y-%m-%d}"))
    if days[-1] < market_days[-1]:
        out.append(Finding(symbol, "prices not up to date", f"last price {days[-1]:%Y-%m-%d}"))
    return out


def check_dividends(symbol: str, s: Stock) -> list[Finding]:
    out = []
    for day, amount in zip(pd.DatetimeIndex(s.dividends.index), s.dividends):
        before = s.close[s.close.index < day]
        if amount <= 0:
            out.append(Finding(symbol, "dividend zero or negative", f"{day:%Y-%m-%d}: {amount}"))
        elif len(before) and amount >= before.iloc[-1]:
            out.append(Finding(symbol, "dividend at or above the price",
                               f"{day:%Y-%m-%d}: {amount:.2f} vs close {before.iloc[-1]:.2f}"))
    return out


def check_quarters_vs_year(symbol: str, s: Stock) -> list[Finding]:
    """Do the 4 quarters of each fiscal year add up to that year's figure (within 5%)? A fiscal year that does not
    end in December is reported too, since its statements come out on a different timetable."""
    if s.quarterly.empty or s.yearly.empty:
        return []
    month = qt.fiscal_year_end(s.yearly, s.quarterly)
    if month is None:
        return [Finding(symbol, "quarters never match the year", "no fiscal year whose 4 quarters' net income adds up")]
    out = [] if month == 12 else [Finding(symbol, "fiscal year not calendar", f"ends in month {month}")]
    for col in SUMMED:
        years = []
        for year, value in zip(s.yearly.index.astype(int), s.yearly[col]):
            # thaifin's yearly EPS is the calendar year for every company (see quarterly.fiscal_year_end).
            end = qt.fiscal_year_end_date(year, 12 if col == "EPS" else month)
            q = s.quarterly[col][(s.quarterly.index > end - pd.DateOffset(years=1)) & (s.quarterly.index <= end)]
            if len(q) == 4 and q.notna().all() and pd.notna(value) and not _close_enough(q.sum(), value):
                years.append(f"{year} ({q.sum():,.4g} vs {value:,.4g})")
        if years:
            out.append(Finding(symbol, f"quarters ≠ year: {col}", "; ".join(years)))
    return out


def check_freshness(symbol: str, s: Stock, today: pd.Timestamp) -> list[Finding]:
    out = []
    month = qt.fiscal_year_end(s.yearly, s.quarterly) or 12
    last_year = int(s.yearly.index.max()) if len(s.yearly) else None
    due_year = max(y for y in range(today.year - 2, today.year + 1)
                   if qt.fiscal_year_end_date(y, month) + qt.Q4_LAG <= today)
    if last_year is None or last_year < due_year:
        out.append(Finding(symbol, "yearly statements behind", f"latest {last_year}, {due_year} should be out"))
    ends = pd.period_range(end=today.to_period("Q"), periods=6, freq="Q").end_time.normalize()
    due = qt.published(pd.DataFrame(index=ends), today, month).index
    if s.quarterly.empty:
        out.append(Finding(symbol, "no quarterly statements", ""))
    elif len(due) and s.quarterly.index.max() < due[-1]:
        out.append(Finding(symbol, "quarterly statements behind",
                           f"latest {s.quarterly.index.max():%Y-%m}, {due[-1]:%Y-%m} should be out"))
    ex = s.ex_div_date
    if ex is None or pd.isna(ex):
        out.append(Finding(symbol, "no XD date from Yahoo", ""))
    elif ex < today:
        out.append(Finding(symbol, "XD date is a past one", f"{ex:%Y-%m-%d}"))
    return out


def audit(stocks: dict[str, Stock], today) -> list[Finding]:
    """Every check on every stock, in symbol order."""
    today = pd.Timestamp(today).normalize()
    market_days = pd.DatetimeIndex(sorted({d for s in stocks.values() for d in s.prices.index}))
    out = []
    for symbol in sorted(stocks):
        s = stocks[symbol]
        out += check_prices(symbol, s, market_days)
        out += check_dividends(symbol, s)
        out += check_quarters_vs_year(symbol, s)
        out += check_freshness(symbol, s, today)
    return out


def report(findings: list[Finding], checked: int) -> str:
    """Markdown: a count per check, then the details grouped by check."""
    if not findings:
        return f"Checked {checked} stocks: nothing suspect found.\n"
    df = pd.DataFrame(findings)
    lines = [f"Checked {checked} stocks. Suspect data, by check:", "", "| Check | Stocks |", "|---|---|"]
    order = df.groupby("check", sort=False)["symbol"].nunique().sort_values(ascending=False)
    lines += [f"| {check} | {n} |" for check, n in order.items()]
    for check in order.index:
        lines += ["", f"## {check}", ""]
        rows = df[df["check"] == check]
        lines += [f"- **{r.symbol}**" + (f": {r.detail}" if r.detail else "") for r in rows.itertuples()]
    return "\n".join(lines) + "\n"


def checklist(stocks: dict[str, Stock], symbols: list[str], url) -> str:
    """Markdown table of the app's figures for a few stocks, to compare by hand with SET's factsheet (`url(symbol)`)."""
    lines = ["| Stock | Last close | Dividends per share by XD year | Latest yearly EPS | EPS last 4 quarters | SET page |",
             "|---|---|---|---|---|---|"]
    for symbol in symbols:
        s = stocks[symbol]
        close = f"{s.close.iloc[-1]:.2f} ({s.close.index[-1]:%Y-%m-%d})" if len(s.close) else "-"
        div = s.dividends.groupby(pd.DatetimeIndex(s.dividends.index).year).sum().tail(3)
        divs = ", ".join(f"{y}: {v:.2f}" for y, v in div.items()) or "-"
        eps = s.yearly["EPS"].dropna() if "EPS" in s.yearly else pd.Series(dtype=float)
        year_eps = f"{eps.iloc[-1]:.2f} ({eps.index[-1]})" if len(eps) else "-"
        ttm = qt.ttm_eps(s.quarterly)
        ttm_eps = f"{ttm[1]:.2f} (to {ttm[0]:%Y-%m})" if ttm else "-"
        lines.append(f"| {symbol} | {close} | {divs} | {year_eps} | {ttm_eps} | {url(symbol)} |")
    return "\n".join(lines) + "\n"
