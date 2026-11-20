"""Backlog #13: Piotroski F-score and Magic Formula rank."""

import numpy as np
import pandas as pd

from src.fundamentals import FIN_COLUMNS
from src.scoring import magic_formula_rank, piotroski


def two_years(**last_year) -> pd.DataFrame:
    """A company that passes every available check in 2025 vs. 2024; override 2025 values with keyword args."""
    df = pd.DataFrame(np.nan, index=[2024, 2025], columns=FIN_COLUMNS)
    df.loc[2024, ["Revenue", "Net income", "ROA", "Operating cash flow", "Total assets", "Total debt", "Shares",
                  "Gross margin"]] = [100, 10, 0.05, 12, 200, 100, 50, 0.30]
    df.loc[2025, ["Revenue", "Net income", "ROA", "Operating cash flow", "Total assets", "Total debt", "Shares",
                  "Gross margin"]] = [120, 12, 0.06, 15, 200, 90, 50, 0.32]
    for col, value in last_year.items():
        df.loc[2025, col.replace("_", " ")] = value
    return df


def test_company_passing_every_available_check_gets_the_maximum():
    score = piotroski(two_years())
    assert score.available == 8  # the current ratio has no data
    assert score.points == score.available
    assert score.checks["Higher current ratio"] is None


def test_each_failing_check_costs_one_point():
    assert piotroski(two_years(ROA=-0.01)).points == 6  # ROA negative and ROA did not improve
    assert piotroski(two_years(Shares=60)).points == 7  # new shares issued
    assert piotroski(two_years(Shares=50.4)).points == 8  # within 1%: rounding in the share count, not new shares


def test_missing_data_makes_checks_unavailable_not_failed():
    score = piotroski(two_years(**{"Gross_margin": np.nan}))  # e.g. banks have no gross margin
    assert score.checks["Higher gross margin"] is None
    assert (score.points, score.available) == (7, 7)


def test_one_year_of_data_scores_only_the_checks_without_a_comparison():
    score = piotroski(two_years().iloc[[-1]])
    # positive ROA, positive operating cash flow, cash flow above profit
    assert (score.points, score.available) == (3, 3)


def test_magic_formula_rank_combines_earnings_yield_and_roe():
    df = pd.DataFrame({"pe": [10.0, 5.0, 20.0, -3.0], "roe": [0.20, 0.10, 0.30, 0.50]}, index=list("ABCD"))
    # Earnings yield ranks: B 1, A 2, C 3. ROE ranks: C 1, A 2, B 3. Sums: A 4, B 4, C 4 -> all tie at rank 1.
    # D has a loss (negative P/E) and is left out.
    rank = magic_formula_rank(df)
    assert rank[["A", "B", "C"]].tolist() == [1, 1, 1]
    assert np.isnan(rank["D"])


def test_magic_formula_rank_orders_best_first():
    df = pd.DataFrame({"pe": [5.0, 10.0, 20.0], "roe": [0.30, 0.20, 0.10]}, index=list("XYZ"))
    assert magic_formula_rank(df).tolist() == [1, 2, 3]
