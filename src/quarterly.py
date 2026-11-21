"""Quarterly statements (thaifin) and the trailing-twelve-month (TTM) EPS built from them.

thaifin's quarterly figures are for that quarter alone, not year to date. Checked 2026-11-21 against the yearly
figures (99 SET100 stocks, 2015-2025): the 4 quarters' EPS add up to the year's in every case (912 of 912), but
net income (89%), revenue (93%) and operating cash flow (82%) often do not (e.g. TIDLOR Q2-Q3 2025 show zero
profit). So only EPS is used (for payout); the F-score stays on yearly statements. The other columns are stored
so the data can be checked.

Publication dates follow SET / SEC rules: reviewed Q1-Q3 statements are due 45 days after the quarter ends,
Q4 comes with the audited yearly statements, at most 3 months after the year ends.
"""

import logging

import pandas as pd

log = logging.getLogger(__name__)

QUARTER_COLUMNS = ["Revenue", "Net income", "EPS", "Gross profit", "Operating cash flow", "Total assets",
                   "Total debt", "Shares"]
Q1_Q3_LAG = pd.Timedelta(days=45)
Q4_LAG = pd.DateOffset(months=3)


def get_quarterly(symbol: str) -> pd.DataFrame:
    """Quarterly figures (QUARTER_COLUMNS), index = quarter end (Timestamp), oldest first.
    Empty when thaifin has none or is down: quarterly data is an extra, never a reason to fail."""
    try:
        from thaifin import Stock  # imported lazily: optional, heavier dependency

        raw = Stock(symbol).quarter_dataframe
    except Exception:
        log.warning("thaifin quarterly statements failed for %s", symbol, exc_info=True)
        return pd.DataFrame(columns=QUARTER_COLUMNS)
    num = raw.apply(pd.to_numeric, errors="coerce")  # some cells are None or text
    q = pd.DataFrame({
        "Revenue": num["revenue"],
        "Net income": num["net_profit"],
        "EPS": num["earning_per_share"],
        "Gross profit": num["gross_profit"],
        "Operating cash flow": num["operating_activities"],
        "Total assets": num["asset"],
        "Total debt": num["total_debt"],
        "Shares": num["mkt_cap"] / num["close"],  # quarter-end market cap = shares × close
    })
    q.index = pd.PeriodIndex(raw.index, freq="Q").end_time.normalize()
    # thaifin lists the current quarter before its statements are out (only price and market cap filled).
    return q.sort_index().dropna(subset=["Revenue", "Net income"], how="all").astype(float)


def published(quarterly: pd.DataFrame, as_of) -> pd.DataFrame:
    """Only the quarters whose statements were out on `as_of`."""
    if quarterly.empty:
        return quarterly
    as_of = pd.Timestamp(as_of)
    out = [end + (Q4_LAG if end.month == 12 else Q1_Q3_LAG) <= as_of for end in pd.DatetimeIndex(quarterly.index)]
    return quarterly[out]


def ttm_eps(quarterly: pd.DataFrame) -> tuple[pd.Timestamp, float] | None:
    """(end of the last quarter, EPS of the last 4 quarters), or None without 4 quarters in a row.
    The EPS is NaN when one of the 4 quarters has none."""
    if len(quarterly) < 4:
        return None
    last4 = quarterly.iloc[-4:]
    periods = pd.DatetimeIndex(last4.index).to_period("Q")
    if (periods[-1] - periods[0]).n != 3:  # a quarter is missing
        return None
    return pd.Timestamp(last4.index[-1]), float(last4["EPS"].sum(min_count=4))


def latest_eps(yearly_eps: pd.Series, quarterly: pd.DataFrame) -> float:
    """The newest EPS: of the last 4 quarters when they end after the last year with an EPS (index = year),
    else that year's. Both inputs must already be limited to what was published (see `published`)."""
    yearly_eps = yearly_eps.dropna()
    t = ttm_eps(quarterly)
    if t is not None and (yearly_eps.empty or t[0] > pd.Timestamp(int(yearly_eps.index[-1]), 12, 31)):
        return t[1]
    return float(yearly_eps.iloc[-1]) if len(yearly_eps) else float("nan")
