"""Backlog #13: fair-value models, checked against hand-computed examples."""

import math

import numpy as np
import pandas as pd
import pytest

from src.valuation import dcf_value, ddm_value, default_ddm_growth, dividend_growth, sensitivity


def test_ddm_gordon_growth():
    assert ddm_value(next_dps=2.00, growth=0.03, required_return=0.08) == pytest.approx(40.00)


@pytest.mark.parametrize("growth", [0.08, 0.09])
def test_ddm_needs_required_return_above_growth(growth):
    with pytest.raises(ValueError, match="required return"):
        ddm_value(next_dps=2.0, growth=growth, required_return=0.08)


def test_dcf_two_years_plus_terminal_value():
    # Year 1: 110 / 1.1 = 100; year 2: 121 / 1.21 = 100; terminal: 121 × 1.02 / (0.10 - 0.02) = 1,542.75,
    # discounted: 1,542.75 / 1.21 = 1,275. Enterprise value 1,475.
    args = dict(fcf=100, growth=0.10, years=2, terminal_growth=0.02, discount_rate=0.10)
    assert dcf_value(**args, net_debt=0, shares=1) == pytest.approx(1475.0)
    assert dcf_value(**args, net_debt=475, shares=10) == pytest.approx(100.0)  # (1,475 - 475) / 10


def test_dcf_rejects_impossible_inputs():
    with pytest.raises(ValueError, match="discount rate"):
        dcf_value(fcf=100, growth=0.1, years=5, terminal_growth=0.09, discount_rate=0.09, net_debt=0, shares=1)
    with pytest.raises(ValueError, match="shares"):
        dcf_value(fcf=100, growth=0.1, years=5, terminal_growth=0.02, discount_rate=0.09, net_debt=0, shares=0)


def test_sensitivity_table_is_3_by_3_and_blank_where_invalid():
    table = sensitivity(lambda r, g: ddm_value(2.0, g, r), rates=[0.07, 0.08, 0.09], growths=[0.02, 0.03, 0.07])
    assert table.shape == (3, 3)
    assert table.loc[0.08, 0.03] == pytest.approx(40.0)
    assert math.isnan(table.loc[0.07, 0.07])  # r = g: no valid value


def test_dividend_growth_is_5_year_cagr_capped_at_10_percent():
    steady = pd.Series([1.0, 1.05, 1.1025, 1.157625, 1.21550625, 1.2762815625, 0.3],
                       index=[2020, 2021, 2022, 2023, 2024, 2025, 2026])  # 5% a year; 2026 is still running
    assert dividend_growth(steady, this_year=2026) == pytest.approx(0.05)
    fast = pd.Series([1.0, 2.0], index=[2020, 2025])  # 14.9% a year
    assert dividend_growth(fast, this_year=2026) == 0.10


def test_dividend_growth_without_enough_history_is_zero():
    assert dividend_growth(pd.Series([1.0, 1.1], index=[2024, 2025]), this_year=2026) == 0.0
    assert dividend_growth(pd.Series(dtype=float), this_year=2026) == 0.0
    assert dividend_growth(pd.Series([0.0, 1.0], index=[2020, 2025]), this_year=2026) == 0.0
    assert not np.isnan(dividend_growth(pd.Series([2.0, 1.0], index=[2020, 2025]), this_year=2026))


def test_default_ddm_growth_stays_below_the_default_required_return():
    fast = pd.Series([1.0, 2.0], index=[2020, 2025])  # 14.9% a year, capped at 10%, then at 8% - 2% = 6%
    assert default_ddm_growth(fast, this_year=2026) == pytest.approx(0.06)
    slow = pd.Series([1.0, 1.1], index=[2020, 2025])
    assert default_ddm_growth(slow, this_year=2026) == pytest.approx(1.1 ** 0.2 - 1)
