"""Quarterly statements: when each quarter counts as published, and the trailing-twelve-month figures."""

import numpy as np
import pandas as pd
import pytest

from src import quarterly as qt


def quarters(n: int, end: str = "2026-09-30", eps: float = 1.0, **overrides) -> pd.DataFrame:
    """`n` quarters in a row ending at `end`: each with revenue 100, net income 10, EPS `eps`, gross profit 40,
    operating cash flow 12; quarter-end assets 1,000, debt 400 and 50 shares."""
    index = pd.period_range(end=pd.Period(end, "Q"), periods=n, freq="Q").end_time.normalize()
    q = pd.DataFrame({"Revenue": 100.0, "Net income": 10.0, "EPS": eps, "Gross profit": 40.0,
                      "Operating cash flow": 12.0, "Total assets": 1000.0, "Total debt": 400.0, "Shares": 50.0},
                     index=index)
    for col, values in overrides.items():
        q[col] = values
    return q


def test_q1_to_q3_count_as_published_45_days_after_the_quarter_ends():
    q = quarters(2)  # Q2 and Q3 2026
    assert qt.published(q, "2026-11-13").index[-1] == pd.Timestamp("2026-06-30")  # Q3 + 44 days: not out yet
    assert qt.published(q, "2026-11-14").index[-1] == pd.Timestamp("2026-09-30")  # Q3 + 45 days


def test_q4_counts_as_published_3_months_after_the_year_ends():
    q = quarters(2, end="2025-12-31")  # Q3 and Q4 2025
    assert qt.published(q, "2026-03-30").index[-1] == pd.Timestamp("2025-09-30")
    assert qt.published(q, "2026-03-31").index[-1] == pd.Timestamp("2025-12-31")


def test_ttm_eps_adds_up_the_last_four_quarters():
    assert qt.ttm_eps(quarters(8, eps=[0.5] * 4 + [1.0] * 4)) == (pd.Timestamp("2026-09-30"), 4.0)


def test_ttm_eps_needs_four_quarters_in_a_row():
    assert qt.ttm_eps(quarters(5).drop(pd.Timestamp("2026-06-30"))) is None  # Q2 2026 missing
    assert qt.ttm_eps(quarters(3)) is None


def test_ttm_eps_is_blank_when_a_quarter_lacks_it():
    t = qt.ttm_eps(quarters(4, eps=[1.0, 1.0, 1.0, np.nan]))
    assert t is not None and np.isnan(t[1])


YEARLY = pd.Series([3.0, 3.0], index=[2024, 2025])


def test_latest_eps_prefers_quarters_newer_than_the_last_year():
    assert qt.latest_eps(YEARLY, quarters(4)) == 4.0


def test_latest_eps_keeps_the_year_when_quarters_are_not_newer():
    assert qt.latest_eps(YEARLY, quarters(4, end="2025-12-31", eps=2.0)) == 3.0  # same period: the audited year
    assert qt.latest_eps(YEARLY, quarters(3)) == 3.0  # not 4 quarters
    assert qt.latest_eps(YEARLY, pd.DataFrame()) == 3.0
    assert np.isnan(qt.latest_eps(pd.Series(dtype=float), pd.DataFrame()))


class FakeStock:
    def __init__(self, symbol):
        index = pd.PeriodIndex(["2026Q2", "2026Q3", "2026Q4"], freq="Q")
        self.quarter_dataframe = pd.DataFrame({
            "revenue": ["100", 110, None], "net_profit": [10, 11, None], "earning_per_share": [1.0, 1.1, None],
            "gross_profit": [40, 44, None], "operating_activities": [12, 13, None], "asset": [1000, 1000, None],
            "total_debt": [400, 400, None], "mkt_cap": [500, 600, 700], "close": [10, 12, 14]}, index=index)


def test_get_quarterly_reads_thaifin_and_drops_the_quarter_not_reported_yet(monkeypatch):
    import thaifin

    monkeypatch.setattr(thaifin, "Stock", FakeStock)
    q = qt.get_quarterly("PTT")
    assert q.index.tolist() == [pd.Timestamp("2026-06-30"), pd.Timestamp("2026-09-30")]
    assert q["Revenue"].tolist() == [100.0, 110.0]  # text turned into numbers
    assert q["Shares"].tolist() == [50.0, 50.0]  # market cap / close


def test_get_quarterly_is_empty_when_thaifin_fails(monkeypatch, caplog):
    import thaifin

    def down(symbol):
        raise ConnectionError("thaifin down")

    monkeypatch.setattr(thaifin, "Stock", down)
    assert qt.get_quarterly("PTT").empty
    assert "thaifin down" in caplog.text
