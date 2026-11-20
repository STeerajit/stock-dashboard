"""Backlog #20: the rules that flag a stock on the Today page."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from src.today import price_levels, reasons

TODAY = date(2026, 11, 23)


def check(**changes) -> list[str]:
    """reasons() for a stock that matches no rule, with `changes` applied."""
    quiet = dict(today=TODAY, price=100.0, support=90.0, resistance_before_today=110.0, rsi=50.0,
                 ex_div_date=None, earnings_date=None, pe=10.0, pe_median=10.0)
    return reasons(**{**quiet, **changes})


def test_a_quiet_stock_has_no_reasons():
    assert check() == []


# ---------- near support: price at most 3% above it ----------

def test_price_exactly_3_percent_above_support_is_flagged():
    assert check(price=103.0, support=100.0) == ["Near support: price 103.00 is 3.0% above support 100.00"]


def test_price_more_than_3_percent_above_support_is_not_flagged():
    assert check(price=103.1, support=100.0) == []


# ---------- broke resistance ----------

def test_price_above_yesterdays_resistance_is_flagged():
    assert check(price=110.5, resistance_before_today=110.0) == [
        "Broke resistance: price 110.50 is above yesterday's resistance 110.00"]


def test_price_exactly_at_resistance_is_not_flagged():
    assert check(price=110.0, resistance_before_today=110.0) == []


# ---------- RSI ----------

@pytest.mark.parametrize("rsi, expected", [
    (29.9, ["RSI 29.9 — oversold (below 30)"]),
    (30.0, []),
    (70.0, []),
    (70.1, ["RSI 70.1 — overbought (above 70)"]),
])
def test_rsi_boundaries(rsi, expected):
    assert check(rsi=rsi) == expected


# ---------- XD and earnings within 14 days, counting today as day 1 ----------

def test_xd_today_is_flagged():
    assert check(ex_div_date=pd.Timestamp(TODAY)) == ["XD date today (23 Nov 2026)"]


def test_xd_on_day_14_is_flagged_and_day_15_is_not():
    day14 = TODAY + timedelta(days=13)
    assert check(ex_div_date=pd.Timestamp(day14)) == ["XD date in 13 days (6 Dec 2026)"]
    assert check(ex_div_date=pd.Timestamp(TODAY + timedelta(days=14))) == []


def test_past_xd_date_is_not_flagged():
    assert check(ex_div_date=pd.Timestamp(TODAY - timedelta(days=1))) == []


def test_earnings_tomorrow_is_flagged():
    assert check(earnings_date=pd.Timestamp(TODAY + timedelta(days=1))) == ["Earnings date tomorrow (24 Nov 2026)"]


# ---------- P/E vs its own history ----------

def test_pe_exactly_20_percent_below_median_is_not_flagged():
    assert check(pe=8.0, pe_median=10.0) == []


def test_pe_more_than_20_percent_below_median_is_flagged():
    assert check(pe=7.5, pe_median=10.0) == ["Cheap vs. its history: P/E 7.5 is 25% below its median 10.0"]


def test_negative_pe_is_not_flagged():
    assert check(pe=-5.0, pe_median=10.0) == []


# ---------- missing data never flags and never fails ----------

def test_missing_data_is_ignored():
    assert check(price=np.nan, support=None, resistance_before_today=None, rsi=np.nan,
                 ex_div_date=pd.NaT, earnings_date=None, pe=np.nan, pe_median=np.nan) == []
    assert check(support=None, resistance_before_today=None, pe_median=None) == []


def test_several_rules_at_once_are_all_listed():
    assert len(check(rsi=20.0, pe=5.0, ex_div_date=pd.Timestamp(TODAY))) == 3


# ---------- price_levels: support today, resistance as of yesterday ----------

def test_price_levels_use_yesterdays_resistance():
    # A swing high of 120 in the middle, then the price climbs above it on the last day.
    close = [100.0] * 15 + [120.0] + [100.0] * 15 + [121.0]
    df = pd.DataFrame({"Close": close, "High": close, "Low": close})
    price, support, resistance = price_levels(df)
    assert price == 121.0
    assert resistance == 120.0  # still a resistance yesterday, so today's 121 is a breakout


def test_price_levels_with_too_little_data():
    df = pd.DataFrame({"Close": [10.0], "High": [10.0], "Low": [10.0]})
    assert price_levels(df) == (10.0, None, None)


# ---------- Today page ----------

from pathlib import Path  # noqa: E402

from streamlit.testing.v1 import AppTest  # noqa: E402

from src import cache, portfolio  # noqa: E402
from src.fundamentals import SnapshotError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def flat_prices(price: float = 100.0, rsi: float = 50.0) -> pd.DataFrame:
    """A flat price history: no support or resistance levels, a chosen RSI."""
    idx = pd.bdate_range(end="2026-11-20", periods=60)
    return pd.DataFrame({"Open": price, "High": price, "Low": price, "Close": price, "Volume": 1e6,
                         "RSI14": rsi}, index=idx)


@pytest.fixture
def today_page(tmp_path, monkeypatch):
    """Offline Today page over a temporary portfolio. Returns a dict to tweak per symbol."""
    monkeypatch.setattr(portfolio, "PORTFOLIO_CSV", tmp_path / "portfolio.csv")
    market = {"rsi": {}, "xd": {}, "down": set()}

    def snapshot_of(symbol):
        if symbol in market["down"]:
            raise SnapshotError(f"Could not load current market data for {symbol}.")
        return pd.Series({"price": 100.0, "pe": 10.0, "ex_div_date": market["xd"].get(symbol, pd.NaT),
                          "earnings_date": pd.NaT})

    monkeypatch.setattr(cache, "snapshot_of", snapshot_of)
    monkeypatch.setattr(cache, "prices", lambda symbol, period="5y": flat_prices(rsi=market["rsi"].get(symbol, 50.0)))
    monkeypatch.setattr(cache, "financials", lambda symbol: pd.DataFrame({"P/E": [10.0, 10.0, 10.0]}))

    def run(rows):
        if rows:
            portfolio.save(pd.DataFrame(rows, columns=portfolio.COLUMNS))
        # Run the whole app (Today is its default page): st.page_link needs the navigation that app.py sets up.
        at = AppTest.from_file(ROOT / "app.py", default_timeout=30).run()
        assert not at.exception, at.exception
        return at

    market["run"] = run
    return market


def test_page_with_empty_portfolio_explains_how_to_add_stocks(today_page):
    at = today_page["run"]([])
    assert "portfolio is empty" in at.info[0].value.lower()


def test_page_lists_only_flagged_stocks_with_reasons(today_page):
    today_page["rsi"]["PTT"] = 25.0
    today_page["xd"]["AOT"] = pd.Timestamp(date.today())
    at = today_page["run"]([("PTT", 100, 30.0), ("AOT", 0, np.nan), ("KBANK", 50, 120.0)])
    text = " ".join(m.value for m in at.markdown)
    assert at.subheader[0].value == "2 of 3 stocks to look at"
    assert "**PTT**" in text and "RSI 25.0 — oversold" in text
    assert "**AOT**" in text and "XD date today" in text
    assert "**KBANK**" not in text
    assert not at.warning and not at.error


def test_page_says_so_when_nothing_matches(today_page):
    at = today_page["run"]([("PTT", 100, 30.0), ("KBANK", 50, 120.0)])
    assert "None of your 2 stocks" in at.success[0].value
    assert not at.subheader


def test_page_warns_per_stock_when_yahoo_fails_and_shows_the_rest(today_page):
    today_page["down"].update({"KBANK"})
    today_page["rsi"]["PTT"] = 80.0
    at = today_page["run"]([("PTT", 100, 30.0), ("KBANK", 50, 120.0)])
    assert "KBANK" in at.warning[0].value
    assert at.subheader[0].value == "1 of 1 stocks to look at"


def test_page_when_yahoo_is_down_for_everything(today_page):
    today_page["down"].update({"PTT", "KBANK"})
    at = today_page["run"]([("PTT", 100, 30.0), ("KBANK", 50, 120.0)])
    assert "PTT, KBANK" in at.warning[0].value
    assert not at.subheader and not at.success
