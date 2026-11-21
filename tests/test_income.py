"""Investor feature 3: the dividend income calendar, by expected XD month, net of the 10% withholding tax."""

import numpy as np
import pandas as pd
import pytest

from src import income, portfolio


def events(*pairs: tuple[str, float]) -> pd.Series:
    """Cash dividends per share, one row per XD date: events(("2025-04-10", 1.0), ...)."""
    return pd.Series([a for _, a in pairs], index=pd.to_datetime([d for d, _ in pairs]), dtype=float)


# PTT pays 1.00 in April and 0.80 in September 2025; KBANK pays 2.50 in April and 2.00 (+0.50 special) in May 2025.
EVENTS = {
    "PTT": events(("2024-04-12", 0.9), ("2024-09-01", 0.7), ("2025-04-10", 1.0), ("2025-09-02", 0.8),
                  ("2026-04-09", 1.1)),
    "KBANK": events(("2024-04-20", 2.0), ("2024-08-10", 1.5), ("2025-04-18", 2.5), ("2025-05-05", 2.0),
                    ("2025-05-20", 0.5)),
}
SHARES = {"PTT": 1000, "KBANK": 200}


def test_bins_by_xd_month():
    cal = income.monthly(EVENTS, SHARES, this_year=2026)
    assert list(cal.index) == list(range(1, 13))
    assert cal.loc[4, "PTT"] == pytest.approx(1_000)
    assert cal.loc[9, "PTT"] == pytest.approx(800)
    assert cal.loc[4, "KBANK"] == pytest.approx(500)
    assert cal["PTT"].drop([4, 9]).eq(0).all()  # 2024 and 2026 dividends are not counted


def test_two_payments_same_month_sum():
    cal = income.monthly(EVENTS, SHARES, this_year=2026)
    assert cal.loc[5, "KBANK"] == pytest.approx(200 * (2.0 + 0.5))


def test_months_sum_to_yearly_gross():
    """The yearly gross equals est_dividend in positions() (dps of the last complete year × shares)."""
    cal = income.monthly(EVENTS, SHARES, this_year=2026)
    for sym, ev in EVENTS.items():
        dps = portfolio.last_full_year_dps(ev.groupby(ev.index.year).sum(), 2026)
        assert cal[sym].sum() == pytest.approx(dps * SHARES[sym])
    assert income.by_month(cal)["gross"].sum() == pytest.approx(1_800 + 1_000)


def test_tax_is_10_percent_net_is_90():
    assert income.TAX == 0.10
    months = income.by_month(income.monthly(EVENTS, SHARES, this_year=2026))
    assert list(months.columns) == ["gross", "tax", "net"]
    assert months.loc[4, "gross"] == pytest.approx(1_500)
    assert months.loc[4, "tax"] == pytest.approx(150)
    assert months.loc[4, "net"] == pytest.approx(1_350)


def holdings_pos() -> pd.DataFrame:
    holdings = pd.DataFrame([("PTT", 1000, 30.0), ("KBANK", 200, 150.0), ("AOT", 0, np.nan)],
                            columns=portfolio.COLUMNS)
    quotes = pd.DataFrame({"symbol": ["PTT", "KBANK", "AOT"], "price": [33.0, 135.0, 60.0],
                           "dps": [1.8, 5.0, 1.0], "sector": ["Energy & Utilities", "Banking", "Transportation"]})
    return portfolio.positions(holdings, quotes)


def test_no_dividend_last_year_is_zero_and_listed():
    ev = {**EVENTS, "PTT": events(("2023-04-10", 1.0), ("2026-04-10", 1.0))}  # nothing in 2025
    cal = income.monthly(ev, SHARES, this_year=2026)
    assert cal["PTT"].sum() == 0
    s = income.summary(holdings_pos(), cal, ev, this_year=2026).set_index("symbol")
    assert s.loc["PTT", "no_recent"] and not s.loc["KBANK", "no_recent"]
    assert s.loc["PTT", "gross"] == 0


def test_stock_without_any_dividend_events_is_zero():
    cal = income.monthly({"PTT": pd.Series(dtype=float)}, {"PTT": 1000}, this_year=2026)
    assert list(cal.index) == list(range(1, 13)) and cal["PTT"].sum() == 0


def test_net_yield_on_cost():
    s = income.summary(holdings_pos(), income.monthly(EVENTS, SHARES, 2026), EVENTS, this_year=2026)
    s = s.set_index("symbol")
    assert s.loc["PTT", "gross"] == pytest.approx(1_800)
    assert s.loc["PTT", "net"] == pytest.approx(1_620)
    assert s.loc["PTT", "net_yield_on_cost"] == pytest.approx(1_620 / 30_000)
    assert s.loc["KBANK", "net_yield_on_cost"] == pytest.approx(900 / 30_000)


def test_watchlist_rows_ignored():
    cal = income.monthly({**EVENTS, "AOT": events(("2025-02-01", 1.0))}, {**SHARES, "AOT": 0}, this_year=2026)
    assert "AOT" not in cal.columns
    s = income.summary(holdings_pos(), cal, EVENTS, this_year=2026)
    assert "AOT" not in set(s["symbol"])


def test_xd_month_may_shift_when_the_year_before_used_other_months():
    s = income.summary(holdings_pos(), income.monthly(EVENTS, SHARES, 2026), EVENTS, this_year=2026)
    s = s.set_index("symbol")
    assert not s.loc["PTT", "may_shift"]  # April + September both years
    assert s.loc["KBANK", "may_shift"]  # April + August in 2024, April + May in 2025


def test_no_shift_flag_without_dividends_the_year_before():
    assert not income.may_shift(events(("2025-04-10", 1.0)), this_year=2026)
