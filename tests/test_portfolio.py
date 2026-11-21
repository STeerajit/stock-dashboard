"""Backlog #19: holdings are checked, saved to a gitignored file, and edited on the Portfolio page."""

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit
from streamlit.testing.v1 import AppTest

from src import cache, portfolio
from src.fundamentals import SNAPSHOT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent


def table(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=portfolio.COLUMNS)


@pytest.fixture
def csv_path(tmp_path, monkeypatch):
    """Point the app at a temporary file, so tests never touch the real data/portfolio.csv."""
    path = tmp_path / "portfolio.csv"
    monkeypatch.setattr(portfolio, "PORTFOLIO_CSV", path)
    return path


# ---------- clean: input checks ----------

def test_clean_accepts_holdings_and_watchlist_rows():
    holdings, problems = portfolio.clean(table([(" ptt ", 1000, 34.5), ("AOT", 0, np.nan)]))
    assert problems == []
    assert holdings["symbol"].tolist() == ["PTT", "AOT"]  # trimmed and upper-cased


def test_clean_drops_rows_that_were_added_but_left_blank():
    holdings, problems = portfolio.clean(table([("PTT", 100, 30.0), (None, np.nan, np.nan)]))
    assert problems == [] and len(holdings) == 1


@pytest.mark.parametrize("row, problem", [
    (("", 100, 30.0), "Row 1: the symbol is empty."),
    (("PTT", -100, 30.0), "Row 1: shares can't be negative."),
    (("PTT", 100, -1.0), "Row 1: average cost can't be negative."),
    (("PTT", np.nan, 30.0), "Row 1: shares is empty (use 0 for a watchlist stock)."),
    (("PTT", 100, np.nan), "Row 1: average cost is empty."),
])
def test_clean_reports_bad_input(row, problem):
    _, problems = portfolio.clean(table([row]))
    assert problems == [problem]


def test_clean_reports_the_same_stock_twice():
    _, problems = portfolio.clean(table([("PTT", 100, 30.0), ("ptt", 50, 31.0)]))
    assert problems == ["Each stock can appear only once: PTT."]


# ---------- load / save ----------

def test_load_without_a_saved_file_is_empty(csv_path):
    df = portfolio.load()
    assert df.empty and list(df.columns) == portfolio.COLUMNS


def test_save_then_load_round_trips(csv_path):
    holdings, _ = portfolio.clean(table([("PTT", 1000, 34.5), ("AOT", 0, np.nan)]))
    portfolio.save(holdings)
    loaded = portfolio.load()
    pd.testing.assert_frame_equal(loaded, holdings, check_dtype=False)


def test_real_portfolio_file_is_gitignored():
    result = subprocess.run(["git", "check-ignore", "-q", "data/portfolio.csv"], cwd=ROOT)
    assert result.returncode == 0, "data/portfolio.csv must be in .gitignore"


# ---------- numbers (hand-computed example) ----------
# PTT:   1,000 sh @ 30  = cost 30,000; price 33  -> value 33,000; P&L +3,000 (+10%); DPS 2.00 -> 2,000; YoC 6.67%
# KBANK:   200 sh @ 150 = cost 30,000; price 135 -> value 27,000; P&L -3,000 (-10%); DPS 6.50 -> 1,300; YoC 4.33%
# AOT:   watchlist (0 shares)
# Total: cost 60,000; value 60,000; P&L 0 (0%); dividend 3,300; YoC 3,300 / 60,000 = 5.5%
# Sectors by value: Energy & Utilities 33,000 / 60,000 = 55%; Banking 27,000 / 60,000 = 45%

def example():
    holdings = table([("PTT", 1000, 30.0), ("KBANK", 200, 150.0), ("AOT", 0, np.nan)])
    quotes = pd.DataFrame({
        "symbol": ["PTT", "KBANK", "AOT"],
        "price": [33.0, 135.0, 60.0],
        "dps": [2.0, 6.5, 1.0],
        "sector": ["Energy & Utilities", "Banking", "Transportation & Logistics"],
    })
    return portfolio.positions(holdings, quotes)


def test_positions_per_stock():
    pos = example().set_index("symbol")
    assert pos.loc["PTT", "value"] == pytest.approx(33_000)
    assert pos.loc["PTT", "pnl"] == pytest.approx(3_000)
    assert pos.loc["PTT", "pnl_pct"] == pytest.approx(0.10)
    assert pos.loc["PTT", "est_dividend"] == pytest.approx(2_000)
    assert pos.loc["PTT", "yield_on_cost"] == pytest.approx(2 / 30)
    assert pos.loc["KBANK", "pnl"] == pytest.approx(-3_000)
    assert pos.loc["KBANK", "pnl_pct"] == pytest.approx(-0.10)
    assert pos.loc["KBANK", "yield_on_cost"] == pytest.approx(6.5 / 150)


def test_watchlist_stock_has_a_price_but_no_position_numbers():
    aot = example().set_index("symbol").loc["AOT"]
    assert aot["price"] == 60.0
    assert aot[["cost", "value", "pnl", "pnl_pct", "est_dividend", "yield_on_cost"]].isna().all()


def test_totals():
    tot = portfolio.totals(example())
    assert tot["cost"] == pytest.approx(60_000)
    assert tot["value"] == pytest.approx(60_000)
    assert tot["pnl"] == pytest.approx(0)
    assert tot["pnl_pct"] == pytest.approx(0)
    assert tot["est_dividend"] == pytest.approx(3_300)
    assert tot["yield_on_cost"] == pytest.approx(0.055)


def test_allocation_by_sector():
    alloc = portfolio.allocation(example())
    assert alloc.to_dict() == pytest.approx({"Energy & Utilities": 0.55, "Banking": 0.45})


def test_stock_without_a_price_is_left_out_of_totals_and_allocation():
    holdings = table([("PTT", 1000, 30.0), ("NOSUCH", 100, 10.0)])
    quotes = pd.DataFrame({"symbol": ["PTT", "NOSUCH"], "price": [33.0, np.nan], "dps": [2.0, np.nan],
                           "sector": ["Energy & Utilities", "Outside SET100"]})
    pos = portfolio.positions(holdings, quotes)
    tot = portfolio.totals(pos)
    assert tot["value"] == pytest.approx(33_000) and tot["cost"] == pytest.approx(30_000)
    assert portfolio.allocation(pos).to_dict() == pytest.approx({"Energy & Utilities": 1.0})


def test_no_dividend_last_year_counts_as_zero():
    quotes = pd.DataFrame({"symbol": ["PTT"], "price": [33.0], "dps": [np.nan], "sector": ["Energy & Utilities"]})
    pos = portfolio.positions(table([("PTT", 1000, 30.0)]), quotes)
    assert pos.loc[0, "est_dividend"] == 0 and pos.loc[0, "yield_on_cost"] == 0


def test_dps_of_last_complete_year():
    div = pd.Series([1.0, 1.5, 0.7], index=[2024, 2025, 2026])  # 2026 is still running
    assert portfolio.last_full_year_dps(div, this_year=2026) == 1.5
    assert np.isnan(portfolio.last_full_year_dps(pd.Series(dtype=float), this_year=2026))


# ---------- concentration: a stock, sector or income source above its cap ----------
# example(): PTT 55% of value and 2,000 / 3,300 = 60.6% of income; KBANK 45% and 39.4%; sectors 55% / 45%.

def spread(n: int, value: float = 10_000, sector=lambda i: f"Sector {i}") -> pd.DataFrame:
    """n held stocks of equal value and dividend, each in its own sector."""
    holdings = table([(f"S{i}", 100, 100.0) for i in range(n)])
    quotes = pd.DataFrame({"symbol": [f"S{i}" for i in range(n)], "price": value / 100, "dps": 1.0,
                           "sector": [sector(i) for i in range(n)]})
    return portfolio.positions(holdings, quotes)


def test_default_caps():
    assert portfolio.DEFAULT_CAPS == {"stock": 0.20, "sector": 0.35, "income": 0.25}


def test_breach_reports_name_share_cap():
    breaches = portfolio.concentration(example())
    assert breaches[0] == portfolio.Breach("stock", "PTT", pytest.approx(0.55), 0.20)
    assert [(b.kind, b.name) for b in breaches] == [
        ("stock", "PTT"), ("stock", "KBANK"), ("sector", "Energy & Utilities"), ("sector", "Banking"),
        ("income", "PTT"), ("income", "KBANK")]
    assert breaches[4].share == pytest.approx(2_000 / 3_300)


def test_at_cap_is_not_a_breach():
    assert portfolio.concentration(spread(5)) == []  # each stock exactly 20% of value and of income
    assert portfolio.concentration(spread(4), {"stock": 0.25, "sector": 0.25, "income": 0.25}) == []
    assert len(portfolio.concentration(spread(4), {"stock": 0.249, "sector": 1, "income": 1})) == 4


def test_watchlist_and_unpriced_excluded():
    holdings = table([("PTT", 1000, 30.0), ("NOSUCH", 100_000, 10.0), ("AOT", 0, np.nan)])
    quotes = pd.DataFrame({"symbol": ["PTT", "NOSUCH", "AOT"], "price": [33.0, np.nan, 60.0],
                           "dps": [2.0, 5.0, 1.0], "sector": ["Energy & Utilities", "Outside SET100", "Transport"]})
    breaches = portfolio.concentration(portfolio.positions(holdings, quotes))
    assert {(b.kind, b.name, b.share) for b in breaches} == {
        ("stock", "PTT", 1.0), ("sector", "Energy & Utilities", 1.0), ("income", "PTT", 1.0)}


def test_outside_set100_left_out_of_the_sector_check():
    pos = spread(5, sector=lambda i: "Outside SET100" if i < 3 else f"Sector {i}")
    assert portfolio.concentration(pos) == []  # 60% "Outside SET100" is not a sector


def test_empty_portfolio_no_breaches():
    assert portfolio.concentration(portfolio.positions(portfolio.empty(), pd.DataFrame(
        columns=["symbol", "price", "dps", "sector"]))) == []


def test_income_share_uses_est_dividend():
    holdings = table([("A", 100, 10.0), ("B", 100, 10.0), ("C", 100, 10.0), ("D", 100, 10.0), ("E", 100, 10.0)])
    quotes = pd.DataFrame({"symbol": list("ABCDE"), "price": 10.0, "dps": [4.0, 1.0, 1.0, 1.0, 1.0],
                           "sector": list("ABCDE")})
    breaches = portfolio.concentration(portfolio.positions(holdings, quotes))
    assert breaches == [portfolio.Breach("income", "A", pytest.approx(0.5), 0.25)]  # values are equal: 20% each


def test_zero_income_no_income_breach():
    holdings = table([("A", 100, 10.0)])
    quotes = pd.DataFrame({"symbol": ["A"], "price": [10.0], "dps": [np.nan], "sector": ["Banking"]})
    kinds = [b.kind for b in portfolio.concentration(portfolio.positions(holdings, quotes))]
    assert kinds == ["stock", "sector"]


def test_breach_text_in_both_languages():
    b = portfolio.Breach("sector", "Banking", 0.452, 0.35)
    assert portfolio.breach_text(b) == "Banking sector: 45.2% of market value (cap 35%)"
    assert "45.2%" in portfolio.breach_text(b, "th") and "35%" in portfolio.breach_text(b, "th")


# ---------- Portfolio page ----------

@pytest.fixture
def fake_market(monkeypatch):
    """Offline prices and dividends for the page: PTT and KBANK are in the (fake) SET100, MAJOR is not."""
    universe = pd.DataFrame({"symbol": ["PTT", "KBANK"], "name": ["PTT", "Kasikornbank"],
                             "sector": ["Energy & Utilities", "Banking"], "in_set50": [True, True]})
    prices = {"PTT": 33.0, "KBANK": 135.0, "MAJOR": 20.0}  # any other symbol: Yahoo has no price

    def snaps(symbols):
        return pd.DataFrame({"symbol": symbols, "price": [prices.get(s, np.nan) for s in symbols]}).reindex(
            columns=SNAPSHOT_COLUMNS)

    monkeypatch.setattr(cache, "set100", lambda: universe)
    monkeypatch.setattr(cache, "snapshots", lambda: snaps(["PTT", "KBANK"]))
    monkeypatch.setattr(cache, "snapshot", lambda symbol: snaps([symbol]))
    monkeypatch.setattr(cache, "dividends", lambda symbol: pd.Series([1.0, 2.0], index=[2020, 2021]))
    monkeypatch.setattr(cache, "dividend_events", lambda symbol: pd.Series(
        1.0, index=pd.to_datetime([f"{y}-04-10" for y in range(2010, 2026)])))
    monkeypatch.setattr(cache, "financials", lambda symbol: pd.DataFrame(
        {"EPS": 2.0, "Free cash flow": 4e9, "Shares": 1e9}, index=[2023, 2024, 2025]))
    monkeypatch.setattr(cache, "quarterly", lambda symbol: pd.DataFrame())

def run_page_with_edits(monkeypatch, edited: pd.DataFrame) -> AppTest:
    """Open the page, make the table editor return `edited` (AppTest can't type into cells), and press Save."""
    monkeypatch.setattr(streamlit, "data_editor", lambda data, **kwargs: edited)
    at = AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run()
    assert not at.exception
    return at.button[0].click().run()


def test_page_opens_with_no_saved_portfolio(csv_path):
    at = AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run()
    assert not at.exception and not at.error
    assert at.title[0].value == "Portfolio"


def test_page_shows_the_numbers_of_a_saved_portfolio(csv_path, fake_market):
    portfolio.save(table([("PTT", 1000, 30.0), ("KBANK", 200, 150.0), ("MAJOR", 0, np.nan)]))
    at = AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run()
    assert not at.exception and not at.error
    assert [w.title for w in at.warning] == ["Too concentrated"]  # 2 stocks: each one is over the 20% cap
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Market value (THB)"] == "60,000"
    assert metrics["Profit / loss (THB)"] == "+0"
    assert set(at.dataframe[0].value["symbol"]) == {"PTT", "KBANK", "MAJOR"}
    assert any("No trading fees" in c.value for c in at.caption)


def test_page_shows_the_dividend_safety_of_held_stocks_only(csv_path, fake_market):
    portfolio.save(table([("PTT", 1000, 30.0), ("KBANK", 200, 150.0), ("MAJOR", 0, np.nan)]))
    at = AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run()
    assert not at.exception
    safety = at.dataframe[0].value.set_index("symbol")["safety"]
    assert safety["PTT"] and safety["KBANK"]  # 16 years paid, no cut, low payout
    assert pd.isna(safety["MAJOR"])  # watchlist row: not graded


def test_page_saves_edited_table(csv_path, fake_market, monkeypatch):
    at = run_page_with_edits(monkeypatch, table([("ptt", 1000, 34.5), ("AOT", 0, np.nan)]))
    assert not at.exception and not at.error
    saved = pd.read_csv(csv_path)
    assert saved["symbol"].tolist() == ["PTT", "AOT"]
    assert saved["shares"].tolist() == [1000, 0]


def test_page_does_not_save_bad_input(csv_path, fake_market, monkeypatch):
    at = run_page_with_edits(monkeypatch, table([("", 1000, 34.5), ("AOT", -5, 10.0)]))
    assert not at.exception
    assert not csv_path.exists()
    assert len(at.error) == 1
    assert "symbol is empty" in at.error[0].value and "can't be negative" in at.error[0].value


def test_clean_rejects_a_symbol_that_is_not_a_set_symbol():
    _, problems = portfolio.clean(table([("PTT](https://evil.example)", 100, 30.0)]))
    assert len(problems) == 1 and "is not a SET symbol" in problems[0]


# ---------- public (deployed) mode: holdings live only in the visitor's session ----------

def test_public_mode_keeps_holdings_in_the_session_not_on_disk(csv_path, fake_market, monkeypatch):
    monkeypatch.setenv("STOCKS_PUBLIC", "1")
    at = run_page_with_edits(monkeypatch, table([("PTT", 100, 30.0)]))
    assert not at.exception and not at.error
    assert not csv_path.exists()
    assert at.session_state["demo_holdings"]["symbol"].tolist() == ["PTT"]
    assert any("this browser tab" in i.value for i in at.info)
    assert not any("this Mac" in c.value for c in at.caption)  # nothing is saved on the visitor's Mac


def test_public_mode_flag():
    import os

    assert portfolio.public_mode({"STOCKS_PUBLIC": "1"}) is True
    assert portfolio.public_mode({}) is False
    assert portfolio.public_mode(dict(os.environ, STOCKS_PUBLIC="0")) is False


# ---------- Portfolio page: concentration warnings ----------

def test_page_warns_about_concentration_with_stock_share_and_cap(csv_path, fake_market):
    portfolio.save(table([("PTT", 1000, 30.0), ("KBANK", 200, 150.0)]))
    at = AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run()
    assert not at.exception
    box = at.warning[0].value
    assert "PTT: 55.0% of market value (cap 20%)" in box
    assert "Energy & Utilities sector: 55.0% of market value (cap 35%)" in box
    assert "dividend income" not in box  # the fake dividends were paid in 2020-21: no income, so no income check


def test_page_cap_change_is_kept_for_other_pages(csv_path, fake_market):
    portfolio.save(table([("PTT", 1000, 30.0), ("KBANK", 200, 150.0)]))
    at = AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run()
    at.number_input(key="cap_stock").set_value(60).run()
    assert not at.exception
    assert at.session_state["conc_caps"] == pytest.approx({"stock": 0.60, "sector": 0.35, "income": 0.25})
    assert "PTT: 55.0%" not in at.warning[0].value
    at.run()
    assert at.session_state["conc_caps"]["stock"] == pytest.approx(0.60)
    assert at.number_input(key="cap_stock").value == 60


# ---------- Portfolio page: dividend income calendar ----------

def open_income_tab(at: AppTest) -> AppTest:
    at.session_state["port_tab"] = next(tab.label for tab in at.tabs if "Income calendar" in tab.label)
    return at.run()


def test_income_calendar_loads_only_when_its_tab_opens(csv_path, fake_market, monkeypatch):
    from src import income

    calls = []
    real = income.monthly
    monkeypatch.setattr(income, "monthly", lambda *a, **k: calls.append(1) or real(*a, **k))
    portfolio.save(table([("PTT", 1000, 30.0), ("KBANK", 200, 150.0), ("MAJOR", 0, np.nan)]))
    at = AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run()
    assert not at.exception and calls == []
    assert not any("expected XD month" in c.value for c in at.caption)
    at = open_income_tab(at)
    assert not at.exception and not at.error and calls
    assert any("expected XD month; payment usually about a month later" in c.value for c in at.caption)


def test_income_calendar_shows_gross_tax_net_and_net_yield(csv_path, fake_market):
    portfolio.save(table([("PTT", 1000, 30.0), ("KBANK", 200, 150.0), ("MAJOR", 0, np.nan)]))
    at = open_income_tab(AppTest.from_file(ROOT / "app_pages/portfolio.py", default_timeout=30).run())
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    # fake_market: 1.00 per share every April, so 1,200 gross, 120 tax, 1,080 net
    assert metrics["Gross dividend, next 12 months (THB)"] == "1,200"
    assert metrics["Withholding tax 10% (THB)"] == "120"
    assert metrics["Net dividend (THB)"] == "1,080"
    per_stock = next(d.value for d in at.dataframe if "net_yield_on_cost" in d.value).set_index("symbol")
    assert "MAJOR" not in per_stock.index  # watchlist row
    assert per_stock.loc["PTT", "net_yield_on_cost"] == pytest.approx(900 / 30_000)
