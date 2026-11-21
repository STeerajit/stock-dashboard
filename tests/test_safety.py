"""Dividend safety grade (backlog #23): each check at its thresholds, missing data, banks, special dividends."""

import numpy as np
import pandas as pd
import pytest

from src import dividend_picks as dp
from src import safety

AS_OF = pd.Timestamp("2026-11-20")  # last complete year: 2025


def divs(per_year: dict[int, float]) -> pd.Series:
    """One XD date (10 April) per year."""
    return pd.Series(list(per_year.values()), index=pd.to_datetime([f"{y}-04-10" for y in per_year]), dtype=float)


def growing(first: int = 2015, last: int = 2026, start: float = 1.0, growth: float = 0.03) -> dict[int, float]:
    return {y: start * (1 + growth) ** (y - first) for y in range(first, last + 1)}


def fin(eps: float = 3.0, fcf=(3e9, 3e9, 3e9), shares: float = 1e9, years=(2023, 2024, 2025)) -> pd.DataFrame:
    return pd.DataFrame({"EPS": eps, "Free cash flow": list(fcf), "Shares": shares}, index=list(years), dtype=float)


def data(div: dict[int, float] | None = None, financials: pd.DataFrame | None = None,
         quarterly: pd.DataFrame | None = None) -> dp.StockData:
    """Only dividends and statements matter to the grade, so prices are left empty."""
    return dp.StockData(pd.DataFrame(), pd.Series(dtype=float), divs(growing() if div is None else div),
                        fin() if financials is None else financials,
                        pd.DataFrame() if quarterly is None else quarterly)


def check(g: safety.Grade, key: str) -> safety.Check:
    return next(c for c in g.checks if c.key == key)


def test_healthy_dividend_payer_is_safe():
    g = safety.grade(data(), "Commerce", AS_OF)
    assert g.level == "safe"
    assert {c.key for c in g.checks} == {"eps_payout", "fcf_payout", "cut", "streak", "cagr", "special"}
    assert all(c.status == "good" for c in g.checks), g.checks
    assert all(c.reason for c in g.checks)


# ---------- thresholds at their boundaries ----------

@pytest.mark.parametrize("payout, status", [
    (0.59, "good"), (0.60, "good"), (0.61, "ok"), (1.0, "ok"), (1.01, "bad")])
def test_payout_at_threshold_boundaries(payout, status):
    assert safety.payout_status(payout) == status


@pytest.mark.parametrize("years, status", [(0, "bad"), (2, "bad"), (3, "ok"), (9, "ok"), (10, "good")])
def test_streak_at_threshold_boundaries(years, status):
    assert safety.streak_status(years) == status


@pytest.mark.parametrize("years, status", [(0, "bad"), (1, "bad"), (2, "ok"), (4, "ok"), (5, "good"),
                                           (float("inf"), "good")])
def test_years_since_cut_at_threshold_boundaries(years, status):
    assert safety.cut_status(years) == status


@pytest.mark.parametrize("growth, status", [(-0.001, "bad"), (0.0, "ok"), (0.019, "ok"), (0.02, "good")])
def test_cagr_at_threshold_boundaries(growth, status):
    assert safety.cagr_status(growth) == status


def test_eps_payout_uses_the_trailing_12_months():
    # 2026 paid 1.0 a share (the last 12 months); 2025 EPS 1.5 -> 67%: ok, not good.
    g = safety.grade(data(div={**growing(last=2025), 2026: 1.0}, financials=fin(eps=1.5)), "Commerce", AS_OF)
    assert check(g, "eps_payout").status == "ok" and "67%" in check(g, "eps_payout").reason


def test_eps_payout_uses_the_same_ttm_eps_as_the_picks_screen():
    from tests.test_quarterly import quarters

    d = data(div={**growing(last=2025), 2026: 1.0}, financials=fin(eps=3.0), quarterly=quarters(4, eps=0.2))
    _, eps, payout = dp.ttm_payout(d, AS_OF)
    assert eps == pytest.approx(0.8) and payout == pytest.approx(1.25)
    assert check(safety.grade(d, "Commerce", AS_OF), "eps_payout").status == "bad"


def test_loss_with_a_dividend_is_a_bad_eps_payout():
    assert check(safety.grade(data(financials=fin(eps=-0.5)), "Commerce", AS_OF), "eps_payout").status == "bad"


# ---------- missing data ----------

def test_missing_check_is_unknown_not_bad():
    no_figures = fin(eps=np.nan, fcf=(np.nan, np.nan, np.nan))
    g = safety.grade(data(financials=no_figures), "Commerce", AS_OF)
    assert check(g, "eps_payout").status == "unknown"
    assert check(g, "fcf_payout").status == "unknown"
    assert g.level == "safe"  # the 4 known checks are all good


def test_cagr_without_5_years_is_unknown_not_zero():
    g = safety.grade(data(div=growing(first=2022)), "Commerce", AS_OF)
    assert check(g, "cagr").status == "unknown"


def test_fewer_than_3_known_is_not_enough_data():
    empty = pd.DataFrame(columns=["EPS", "Free cash flow", "Shares"], dtype=float)
    g = safety.grade(data(div={2025: 1.0}, financials=empty), "Commerce", AS_OF)
    assert sum(c.status in ("good", "ok", "bad") for c in g.checks) < 3
    assert g.level == "not_enough_data"
    # 3 years of the same dividend: streak, cut and special are known -> graded.
    assert safety.grade(data(div={2023: 1.0, 2024: 1.0, 2025: 1.0}, financials=empty), "Commerce",
                        AS_OF).level in safety.LEVELS


def test_no_dividend_history_is_not_enough_data():
    d = data(financials=pd.DataFrame(columns=["EPS", "Free cash flow", "Shares"], dtype=float))._replace(
        dividends=pd.Series(dtype=float, index=pd.DatetimeIndex([])))
    g = safety.grade(d, "Commerce", AS_OF)
    assert g.level == "not_enough_data" and all(c.status in ("unknown", "skipped") for c in g.checks)


# ---------- FCF payout ----------

def test_bank_skips_fcf_and_says_so():
    g = safety.grade(data(financials=fin(fcf=(-1e9, -1e9, -1e9))), "Banking", AS_OF)
    c = check(g, "fcf_payout")
    assert c.status == "skipped" and "bank" in c.reason.lower()
    assert g.level == "safe"
    for sector in ("Finance & Securities", "Insurance"):
        assert check(safety.grade(data(), sector, AS_OF), "fcf_payout").status == "skipped"


def test_fcf_bad_in_one_of_3_years_is_not_bad():
    # Dividends paid ~1.3e9 a year; FCF negative in one year only.
    assert check(safety.grade(data(financials=fin(fcf=(3e9, -1e9, 3e9))), "Commerce", AS_OF),
                 "fcf_payout").status == "good"


def test_fcf_bad_in_2_of_3_is_bad():
    g = safety.grade(data(financials=fin(fcf=(-1e9, 3e9, 1e8))), "Commerce", AS_OF)  # 2025: payout > 100%
    assert check(g, "fcf_payout").status == "bad"
    assert g.level == "risky"


def test_fcf_payout_of_exactly_100_percent_is_not_bad():
    d = data(div={y: 1.0 for y in range(2015, 2027)}, financials=fin(fcf=(1e9, 1e9, 1e9)))
    assert check(safety.grade(d, "Commerce", AS_OF), "fcf_payout").status == "good"


def test_fcf_with_only_one_known_year_is_unknown():
    g = safety.grade(data(financials=fin(fcf=(np.nan, np.nan, -1e9))), "Commerce", AS_OF)
    assert check(g, "fcf_payout").status == "unknown"


# ---------- special dividends ----------

def special(per_year: dict[int, float]) -> set[int]:
    return safety.special_years(pd.Series(per_year))


def test_special_year_is_a_spike_above_1_5x_both_neighbours():
    base = {y: 1.0 for y in range(2016, 2026)}
    assert special({**base, 2020: 1.5}) == set()  # exactly 1.5x: not special
    assert special({**base, 2020: 1.51}) == {2020}
    assert special({2021: 1.0, 2022: 1.0, 2023: 3.0, 2024: 1.0, 2025: 1.0}) == {2023}  # 1, 1, 3, 1
    assert special({2021: 1.0, 2022: 2.0, 2023: 1.4, 2024: 1.4, 2025: 1.4}) == set()  # not 1.5x the next year


def test_previous_paid_year_skips_years_without_a_dividend():
    assert special({2020: 1.0, 2021: 0.0, 2022: 1.4, 2023: 0.9, 2024: 1.0, 2025: 1.0}) == set()
    assert special({2020: 1.0, 2021: 0.0, 2022: 1.6, 2023: 1.0, 2024: 1.0, 2025: 1.0}) == {2022}


def test_latest_year_is_special_above_1_5x_the_median_of_the_3_paid_years_before():
    base = {2021: 5.0, 2022: 1.0, 2023: 1.2, 2024: 1.0}  # median of 2022-2024 and the year before: 1.0
    assert special({**base, 2025: 1.5}) == set()
    assert special({**base, 2025: 1.51}) == {2025}


def test_latest_year_must_also_beat_the_previous_paid_year():
    assert special({2020: 0.19, 2021: 0.0, 2022: 0.0, 2023: 0.36, 2024: 0.79, 2025: 0.81}) == set()  # like AOT
    assert special({2022: 1.0, 2023: 1.0, 2024: 1.0, 2025: 1.51}) == {2025}


def test_steady_grower_is_never_special():
    assert special(growing(first=2016, last=2025, growth=0.10)) == set()


def test_recovery_after_a_low_year_is_not_special():
    assert special({2018: 1.0, 2019: 1.0, 2020: 0.3, 2021: 1.0, 2022: 1.05, 2023: 1.1, 2024: 1.1,
                    2025: 1.2}) == set()


def test_special_year_excluded_from_cagr_and_cut():
    flat = {y: 1.0 for y in range(2015, 2026)}
    # 2022 special: the drop back to 1.0 in 2023 is not a cut.
    g = safety.grade(data(div={**flat, 2022: 3.0, 2026: 1.0}), "Commerce", AS_OF)
    assert check(g, "cut").status == "good"
    assert check(g, "streak").status == "good"  # the special year still counts as paid
    # 2025 special: left out of the 5-year growth, which is then 0% (ok), not +25% a year (good).
    g = safety.grade(data(div={**flat, 2025: 3.0, 2026: 1.0}), "Commerce", AS_OF)
    assert check(g, "cagr").status == "ok"
    assert check(g, "special").status == "ok"


def test_a_real_cut_is_found():
    d = growing(last=2025)
    g = safety.grade(data(div={**d, 2025: d[2024] * 0.8, 2026: 1.0}), "Commerce", AS_OF)
    assert check(g, "cut").status == "bad"
    recovered = divs({2019: 1.0, 2020: 0.5, 2021: 0.6, 2022: 0.7, 2023: 0.8, 2024: 0.9, 2025: 1.0})
    assert safety.years_since_cut(safety.per_year(recovered, AS_OF)) == 5  # cut in 2020
    assert safety.years_since_cut(safety.per_year(divs({2024: 1.0, 2025: 1.0}), AS_OF)) == float("inf")


def test_a_skipped_year_breaks_the_streak():
    d = {y: 1.0 for y in range(2015, 2026) if y != 2021}
    assert safety.paid_streak(safety.per_year(divs(d), AS_OF)) == 4  # 2022-2025


# ---------- levels and text ----------

def test_two_bad_checks_are_unsafe():
    d = growing(last=2025)
    g = safety.grade(data(div={**d, 2025: d[2024] * 0.8, 2026: 1.0}, financials=fin(fcf=(-1, -1, -1))),
                     "Commerce", AS_OF)
    assert g.level == "unsafe"


def test_reasons_in_thai():
    en = safety.grade(data(), "Commerce", AS_OF)
    th = safety.grade(data(), "Commerce", AS_OF, lang="th")
    assert th.level == en.level
    assert all(a.reason != b.reason for a, b in zip(en.checks, th.checks))
    assert all(any("฀" <= ch <= "๿" for ch in c.reason) for c in th.checks)


# ---------- review fixes ----------

def test_per_year_has_no_float_noise():
    """0.70 + 0.60 sums to 1.2999999999999998 in floats: that must not look like a cut from 1.30 (BEM 2017)."""
    ev = pd.Series([1.30, 0.70, 0.60], index=pd.to_datetime(["2024-04-10", "2025-04-10", "2025-09-10"]))
    years = safety.per_year(ev, AS_OF)
    assert years[2025] == 1.30
    assert safety.years_since_cut(years) == float("inf")


def test_no_cut_with_a_short_history_is_ok_not_good():
    c = check(safety.grade(data(div={y: 1.0 for y in range(2022, 2026)}), "Commerce", AS_OF), "cut")
    assert c.status == "ok" and "4 years" in c.reason


def test_no_cut_over_5_years_is_good():
    c = check(safety.grade(data(div={y: 1.0 for y in range(2021, 2026)}), "Commerce", AS_OF), "cut")
    assert c.status == "good"


def test_fcf_reason_with_one_bad_year_of_two():
    c = check(safety.grade(data(financials=fin(fcf=(np.nan, -1e9, 3e9))), "Commerce", AS_OF), "fcf_payout")
    assert c.status == "good"
    assert c.reason == "Free cash flow covered the dividend in 1 of the last 2 years (one bad year is allowed)"


def test_fcf_reason_when_every_year_is_covered():
    c = check(safety.grade(data(), "Commerce", AS_OF), "fcf_payout")
    assert c.reason == "Free cash flow covered the dividend in each of the last 3 years"


def test_unknown_sector_makes_fcf_unknown():
    """A stock outside SET100 has no sector: it may be a bank, so the FCF check can't be trusted either way."""
    g = safety.grade(data(financials=fin(fcf=(-1e9, -1e9, -1e9))), "Outside SET100", AS_OF)
    c = check(g, "fcf_payout")
    assert c.status == "unknown" and "sector" in c.reason.lower()
    assert g.level == "safe"  # not graded
