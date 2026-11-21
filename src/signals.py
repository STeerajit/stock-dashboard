"""Buy, info and sell signals for Dividend Picks (see docs/research/dividend-picks.md, sections 3–6).

Each signal is shown on its own, with how strong its evidence is and whether we read the original paper.
The two summary labels ("buy now", "sell") are computed here but only shown when the backtest says they
beat the plain picks (scripts/report_dividend_picks.py).
"""

from datetime import date
from typing import NamedTuple

import pandas as pd

from src.dividend_picks import PICKS, StockData, trailing_dividends
from src.fundamentals import yield_history
from src.i18n import text
from src.indicators import add_indicators, sma_10_month
from src.today import NEAR_SUPPORT, RSI_LOW, price_levels

SELL_RANK = 20  # sell only when the rank falls below 20 (buy/hold spread, Novy-Marx & Velikov 2016)
TRAP_STAGES = ("no_dividend", "payout", "eps_negative", "eps_declining")


class Meta(NamedTuple):
    side: str  # "buy", "info" or "sell"
    evidence: str  # "strong", "medium", "weak" or "none" (no research found)
    checked: str  # "verified", "partial", "unverified" or "none" (no paper to check)
    tested: bool  # part of the backtest
    source: str


SIGNALS: dict[str, Meta] = {
    "trend": Meta("buy", "strong", "verified", True, "Faber (2007)"),
    "market_trend": Meta("buy", "strong", "verified", True, "Faber (2007)"),
    "rsi_low": Meta("buy", "medium", "partial", True, "Tharavanij et al. (2015); Chong & Ng (2008)"),
    "macd": Meta("buy", "medium", "partial", True, "Tharavanij et al. (2015); Chong & Ng (2008)"),
    "obv": Meta("buy", "medium", "partial", True, "Tharavanij et al. (2015)"),
    "near_support": Meta("buy", "none", "none", True, ""),
    "pullback": Meta("buy", "strong", "unverified", True, "Jegadeesh (1990); Lehmann (1990)"),
    "dividend_month": Meta("buy", "strong", "unverified", True, "Hartzmark & Solomon (2013)"),
    "days_to_xd": Meta("info", "none", "none", False, ""),
    "yield_vs_5y": Meta("info", "none", "none", False, ""),
    "dividend_cut": Meta("sell", "strong", "unverified", False, "Michaely, Thaler & Womack (1995)"),
    "trap": Meta("sell", "medium", "verified", False, "SETHD (Nikornpittaya & Wongpriew 2024)"),
    "rank_out": Meta("sell", "strong", "partial", True, "Novy-Marx & Velikov (2016)"),
    "below_trend": Meta("sell", "strong", "verified", True, "Faber (2007)"),
}


class Signal(NamedTuple):
    key: str
    on: bool
    label: str  # what it says today, with its numbers


def _above_10_month(close: pd.Series, as_of: pd.Timestamp) -> tuple[bool | None, float, float]:
    """(close > its 10-month average at the last month end on or before `as_of`, that close, that average).
    None without 10 months of history."""
    monthly = sma_10_month(close[close.index <= as_of])
    monthly = monthly[monthly.index <= as_of].dropna()
    if monthly.empty:
        return None, float("nan"), float("nan")
    last = monthly.iloc[-1]
    return bool(last["Close"] > last["SMA10M"]), float(last["Close"]), float(last["SMA10M"])


def dividend_cut(dividends: pd.Series, as_of: pd.Timestamp) -> tuple[bool, float, float]:
    """(cut, last year's dividends, the year before's): dividends with XD dates in the last complete calendar year
    were lower than the year before (0 = omitted). False when the year before paid nothing either."""
    d = dividends[dividends.index <= as_of]
    per_year = d.groupby(pd.DatetimeIndex(d.index).year).sum()
    last, before = float(per_year.get(as_of.year - 1, 0.0)), float(per_year.get(as_of.year - 2, 0.0))
    return before > 0 and last < before, last, before


def compute(d: StockData, as_of, *, rank, stage: str, market_close: pd.Series | None = None,
            ex_div_date=None, today: date | None = None, lang: str = "en") -> dict[str, Signal]:
    """Every signal for one stock on `as_of`. `rank`/`stage` come from dividend_picks.screen (rank NA = unranked).
    `ex_div_date` (next XD date, from the snapshot) and `today` only feed the days-to-XD info."""
    as_of = pd.Timestamp(as_of)
    prices = d.prices[d.prices.index <= as_of].tail(1250)  # 5 years: enough for every indicator below
    ind = add_indicators(prices)
    last = ind.iloc[-1]
    tx = lambda key, **kw: text(f"sig.{key}", lang, **kw)  # noqa: E731
    out: dict[str, Signal] = {}

    def put(key, on, label):
        out[key] = Signal(key, bool(on), label)

    above, close_m, sma_m = _above_10_month(prices["Close"], as_of)
    put("trend", above, tx("no_trend") if above is None else
        tx("trend_up" if above else "trend_down", close=close_m, sma=sma_m))
    if market_close is not None:
        m_above, m_close, m_sma = _above_10_month(market_close, as_of)
        put("market_trend", m_above, tx("no_trend") if m_above is None else
            tx("market_up" if m_above else "market_down", close=m_close, sma=m_sma))
    put("rsi_low", last["RSI14"] < RSI_LOW, tx("rsi", rsi=last["RSI14"], low=RSI_LOW))
    put("macd", last["MACD"] > last["MACD_signal"], tx("macd_up" if last["MACD"] > last["MACD_signal"] else "macd_down"))
    put("obv", last["OBV"] > last["OBV_SMA20"], tx("obv_up" if last["OBV"] > last["OBV_SMA20"] else "obv_down"))
    price, support, _ = price_levels(prices.tail(250))
    near = support is not None and 0 < support <= price <= support * (1 + NEAR_SUPPORT)
    put("near_support", near, tx("support", support=support, gap=price / support - 1) if support else tx("no_support"))
    month_ago = prices["Close"][prices.index <= as_of - pd.DateOffset(months=1)]
    one_month = float(prices["Close"].iloc[-1] / month_ago.iloc[-1] - 1) if len(month_ago) else float("nan")
    put("pullback", one_month < 0, tx("pullback", ret=one_month))
    xd = d.dividends[d.dividends.index <= as_of]
    paid_months = {(t.year, t.month) for t in pd.DatetimeIndex(xd[xd > 0].index)}
    expected = (as_of.year - 1, as_of.month) in paid_months
    put("dividend_month", expected, tx("div_month" if expected else "no_div_month"))

    if ex_div_date is not None and not pd.isna(ex_div_date) and today is not None:
        days = (pd.Timestamp(ex_div_date).date() - today).days
        if days >= 0:
            put("days_to_xd", True, tx("days_to_xd", days=days, date=f"{pd.Timestamp(ex_div_date):%d %b %Y}"))
    close = d.close[d.close.index <= as_of]
    if len(close) and close.iloc[-1] > 0:
        now = trailing_dividends(d.dividends, as_of) / float(close.iloc[-1])
        per_year = xd.groupby(pd.DatetimeIndex(xd.index).year).sum()
        past = yield_history(per_year, close, as_of.year).tail(5)
        if len(past) == 5:
            avg = float(past.mean())
            put("yield_vs_5y", now > avg, tx("yield_vs_5y", now=now, avg=avg))

    cut, last_dps, before_dps = dividend_cut(d.dividends, as_of)
    put("dividend_cut", cut, tx("cut", last=last_dps, before=before_dps, year=as_of.year - 1) if cut else tx("no_cut"))
    put("trap", stage in TRAP_STAGES, tx(f"trap_{stage}") if stage in TRAP_STAGES else tx("no_trap"))
    out_of_rank = pd.isna(rank) or rank > SELL_RANK
    put("rank_out", out_of_rank, tx("unranked") if pd.isna(rank) else tx("rank", rank=int(rank), limit=SELL_RANK))
    put("below_trend", above is False, out["trend"].label)
    return out


def buy_now(sig: dict[str, Signal], rank) -> bool:
    """Summary buy label: in the 10 picks, above the 10-month average, and RSI below 30 or close to support."""
    in_picks = not pd.isna(rank) and rank <= PICKS
    return in_picks and sig["trend"].on and (sig["rsi_low"].on or sig["near_support"].on)


def sell_now(sig: dict[str, Signal]) -> bool:
    """Summary sell label: rank below 20 (or out of the ranking), or below the 10-month average."""
    return sig["rank_out"].on or sig["below_trend"].on
