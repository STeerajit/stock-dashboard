"""Backlog #15: 5-year growth and quality figures for the screener."""

import math

import numpy as np
import pandas as pd
import pytest

from src.fundamentals import FIN_COLUMNS, growth_quality


def fin(revenue, net_income, roe, start=2019):
    years = range(start, start + len(revenue))
    df = pd.DataFrame(np.nan, index=list(years), columns=FIN_COLUMNS)
    df["Revenue"], df["Net income"], df["ROE"] = revenue, net_income, roe
    return df


def test_cagr_and_average_roe_hand_computed():
    # Revenue 100 -> 161.051 over 5 years = 10% a year; net income 10 -> 20 = 2^(1/5) - 1 = 14.87%.
    # ROE of the last 5 years: 0.10, 0.12, 0.14, 0.16, 0.18 -> average 0.14 (the first year, 0.50, is left out).
    g = growth_quality(fin([100, 110, 121, 133.1, 146.41, 161.051], [10, 11, 12, 14, 17, 20],
                           [0.50, 0.10, 0.12, 0.14, 0.16, 0.18]))
    assert g["rev_cagr5"] == pytest.approx(0.10)
    assert g["ni_cagr5"] == pytest.approx(2 ** 0.2 - 1)
    assert g["roe_avg5"] == pytest.approx(0.14)


def test_blank_with_fewer_than_5_years():
    g = growth_quality(fin([100, 110, 121, 133, 146], [10, 11, 12, 13, 14], [0.1] * 5))
    assert math.isnan(g["rev_cagr5"]) and math.isnan(g["ni_cagr5"])
    assert g["roe_avg5"] == pytest.approx(0.1)  # 5 years of ROE are enough for the average


def test_blank_when_the_start_value_is_zero_or_negative():
    g = growth_quality(fin([100] * 6, [-5, 1, 2, 3, 4, 5], [0.1] * 6))
    assert math.isnan(g["ni_cagr5"]) and g["rev_cagr5"] == pytest.approx(0.0)


def test_blank_for_empty_financials():
    g = growth_quality(pd.DataFrame(columns=FIN_COLUMNS))
    assert all(math.isnan(v) for v in g.values())


def test_roe_average_needs_5_years():
    assert math.isnan(growth_quality(fin([1, 2, 3], [1, 2, 3], [0.1, 0.1, 0.1]))["roe_avg5"])
