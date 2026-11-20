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
