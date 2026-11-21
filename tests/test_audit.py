"""Data checks (src/audit.py): each check at its boundary, on small hand-made stocks."""

import pandas as pd

from src import audit
from tests.test_quarterly import quarters

TODAY = pd.Timestamp("2026-11-21")
DAYS = pd.bdate_range("2026-11-02", "2026-11-20")


def prices(days=DAYS, close=10.0) -> pd.DataFrame:
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1.0},
                        index=days)


def yearly(net_income=(40.0, 40.0), eps=(4.0, 4.0), last_year=2025) -> pd.DataFrame:
    return pd.DataFrame({"EPS": list(eps), "Net income": list(net_income), "Revenue": 400.0,
                         "Operating cash flow": 48.0}, index=range(last_year - len(eps) + 1, last_year + 1))


def stock(**kw) -> audit.Stock:
    p = kw.pop("prices", prices())
    base = dict(prices=p, close=p["Close"], dividends=pd.Series(dtype=float), yearly=yearly(),
                quarterly=quarters(12), ex_div_date=pd.Timestamp("2026-12-01"))
    return audit.Stock(**{**base, **kw})


def checks(findings) -> set[str]:
    return {f.check for f in findings}


def test_clean_stock_has_no_findings():
    assert audit.audit({"A": stock()}, TODAY) == []


def test_a_daily_move_over_30_percent_is_reported_and_30_percent_is_not():
    p = prices()
    p.loc[p.index[-2]:, ["Close", "High"]] = 13.0  # +30% exactly
    assert "daily move over 30%" not in checks(audit.audit({"A": stock(prices=p)}, TODAY))
    p.loc[p.index[-1]:, ["Close", "High"]] = 17.0  # 13 -> 17: +31%
    found = [f for f in audit.audit({"A": stock(prices=p)}, TODAY) if f.check == "daily move over 30%"]
    assert len(found) == 1 and "2026-11-20" in found[0].detail


def test_close_outside_high_low_is_reported():
    p = prices()
    p.loc[p.index[3], "Close"] = 12.0  # high is 11
    assert "close outside high-low" in checks(audit.audit({"A": stock(prices=p)}, TODAY))


def test_days_other_stocks_traded_are_missing_and_the_last_price_is_old():
    late = stock(prices=prices(DAYS[:-3]))
    found = checks(audit.audit({"A": stock(), "B": late}, TODAY))
    assert {"missing trading days", "prices not up to date"} <= found


def test_a_dividend_at_or_above_the_price_is_reported():
    div = pd.Series([10.0], index=[DAYS[5]])  # the close before is 10
    assert "dividend at or above the price" in checks(audit.audit({"A": stock(dividends=div)}, TODAY))
    ok = pd.Series([0.5], index=[DAYS[5]])
    assert audit.audit({"A": stock(dividends=ok)}, TODAY) == []


def test_quarters_that_do_not_add_up_to_the_year_within_5_percent_are_reported():
    # Each quarter earns 10, so 2025's 4 quarters make 40. 41.9 is within 5%; 42.2 is not.
    assert audit.audit({"A": stock(yearly=yearly(net_income=(40.0, 41.9)))}, TODAY) == []
    found = [f for f in audit.audit({"A": stock(yearly=yearly(net_income=(40.0, 42.2)))}, TODAY)
             if f.check == "quarters ≠ year: Net income"]
    assert len(found) == 1 and found[0].detail.startswith("2025")


def test_a_fiscal_year_ending_in_september_is_found_and_reported():
    # Net income 10 a quarter, but 20 in Dec 2024: only the years to September add up to 40.
    q = quarters(12)
    q.loc[pd.Timestamp("2024-12-31"), "Net income"] = 20.0
    y = yearly(net_income=(50.0, 40.0), last_year=2026)  # fiscal years to Sep 2025 and Sep 2026
    found = checks(audit.audit({"A": stock(quarterly=q, yearly=y)}, TODAY))
    assert "fiscal year not calendar" in found


def test_statements_and_xd_dates_that_are_late_or_missing_are_reported():
    old = quarters(8, end="2026-06-30")  # Q3 2026 was due on 14 Nov
    found = checks(audit.audit({"A": stock(quarterly=old, yearly=yearly(last_year=2024),
                                           ex_div_date=pd.Timestamp("2026-08-01"))}, TODAY))
    assert {"quarterly statements behind", "yearly statements behind", "XD date is a past one"} <= found
    assert "no XD date from Yahoo" in checks(audit.audit({"A": stock(ex_div_date=pd.NaT)}, TODAY))


def test_report_counts_stocks_per_check():
    text = audit.report([audit.Finding("A", "x", "1"), audit.Finding("A", "x", "2"), audit.Finding("B", "x", "")], 3)
    assert "| x | 2 |" in text and "- **A**: 1" in text and "- **B**\n" in text
    assert "nothing suspect" in audit.report([], 3)


def test_checklist_lists_the_figures_and_the_set_page():
    text = audit.checklist({"A": stock(dividends=pd.Series([0.5, 0.7], index=pd.to_datetime(["2025-04-10",
                                                                                              "2026-04-10"])))},
                           ["A"], lambda s: f"https://example/{s}")
    assert "| A | 10.00 (2026-11-20) | 2025: 0.50, 2026: 0.70 | 4.00 (2025) | 4.00 (to 2026-09) | https://example/A |" \
        in text
