"""Backlog #5: offline smoke tests for both pages.

All `src.cache` loaders are replaced with small in-memory fixtures, so the pages run
without Yahoo Finance, thaifin, or the network.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src import cache
from src.fundamentals import FIN_COLUMNS, SNAPSHOT_COLUMNS
from src.indicators import add_indicators
from src.model import train_and_backtest
from tests.fakes import fake_prices

ROOT = Path(__file__).resolve().parent.parent

UNIVERSE = pd.DataFrame({
    "symbol": ["PTT", "PTTEP", "KBANK", "SCB", "CPALL", "AOT"],
    "name": ["PTT", "PTT Exploration", "Kasikornbank", "SCB X", "CP All", "Airports of Thailand"],
    "sector": ["Energy & Utilities", "Energy & Utilities", "Banking", "Banking", "Commerce",
               "Transportation & Logistics"],
    "in_set50": [True, True, True, True, True, False],
})


def snapshots(symbols: list[str] | None = None) -> pd.DataFrame:
    """Shaped exactly like the real loader: indexing by SNAPSHOT_COLUMNS raises if a column is missing."""
    symbols = UNIVERSE["symbol"].tolist() if symbols is None else symbols
    n = len(symbols)
    return pd.DataFrame({
        "symbol": symbols, "price": np.linspace(30, 80, n), "change_pct": 0.01,
        "volume": 2e6, "avg_volume": 1e6, "value_traded": 1e8, "bid": 29.9, "ask": 30.1,
        "high_52w": 90.0, "low_52w": 20.0, "pos_52w": 0.5, "market_cap": np.linspace(1e12, 1e11, n),
        "pe": np.linspace(8, 20, n), "pbv": 1.2, "div_yield": 0.05, "roe": 0.1, "de": 0.8, "net_margin": 0.08,
        "ex_div_date": pd.Timestamp("2026-08-19"), "earnings_date": pd.NaT, "free_float": 0.4,
    })[SNAPSHOT_COLUMNS]


def financials(years: int = 6) -> pd.DataFrame:
    idx = list(range(2026 - years, 2026))
    fin = pd.DataFrame({c: np.linspace(1, 2, years) for c in FIN_COLUMNS}, index=idx)
    fin["Revenue"] *= 1e11
    fin["Net income"] *= 1e10
    fin["Free cash flow"] *= 1e9
    fin["P/E"] = np.linspace(8, 12, years)
    fin.attrs = {"source": "test fixture", "de_definition": "Total liabilities / shareholders' equity"}
    return fin


PRICES = add_indicators(fake_prices(n=700))


@pytest.fixture
def fake_cache(monkeypatch):
    """Replace every cache loader the pages call. Returns a dict to tweak per test."""
    state = {"financials": financials(), "snapshot": snapshots}
    monkeypatch.setattr(cache, "set100", lambda: UNIVERSE.copy())
    monkeypatch.setattr(cache, "snapshots", snapshots)
    monkeypatch.setattr(cache, "growth", lambda: pd.DataFrame({
        "symbol": UNIVERSE["symbol"], "rev_cagr5": np.linspace(0.02, 0.12, len(UNIVERSE)),
        "ni_cagr5": np.nan, "roe_avg5": 0.1}))
    monkeypatch.setattr(cache, "snapshot", lambda symbol: state["snapshot"]([symbol]))
    monkeypatch.setattr(cache, "prices", lambda symbol, period="5y": PRICES)
    monkeypatch.setattr(cache, "financials", lambda symbol: state["financials"])
    monkeypatch.setattr(cache, "dividends", lambda symbol: pd.Series([1.0, 1.2, 1.4], index=[2023, 2024, 2025]))
    monkeypatch.setattr(cache, "backtest", lambda symbol: train_and_backtest(PRICES))
    monkeypatch.setattr(cache, "unadjusted_close", lambda symbol: pd.Series(
        [20.0, 30.0, 35.0], index=pd.to_datetime(["2023-12-29", "2024-12-30", "2025-12-30"])))
    return state


def open_stock(symbol: str, tab: str | None = None) -> AppTest:
    """Run the stock page, opened on the tab with the full label `tab` (see tab_label)."""
    at = AppTest.from_file(ROOT / "app_pages/stock.py", default_timeout=60)
    at.query_params["symbol"] = symbol
    if tab:
        at.session_state["tab"] = tab
    return at.run()


def tab_label(word: str) -> str:
    """The full label of the stock page tab containing `word`, read from the page itself."""
    return next(label for label in stock_tab_labels() if word in label)


def stock_tab_labels() -> list[str]:
    return [t.label for t in open_stock("PTT").tabs]


def test_screener_renders_all_rows(fake_cache):
    at = AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    assert not at.exception and not at.error
    assert len(at.dataframe[0].value) == len(UNIVERSE)


def test_screener_sector_filter_reduces_rows(fake_cache):
    at = AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    at.multiselect(key="sectors").select("Banking").run()
    assert not at.exception
    assert set(at.dataframe[0].value["symbol"]) == {"KBANK", "SCB"}


def test_every_stock_tab_renders(fake_cache):
    labels = stock_tab_labels()
    assert len(labels) == 7
    for label in labels:
        at = open_stock("PTT", label)
        assert not at.exception, (label, at.exception)
        assert at.title[0].value == "PTT · PTT"
        assert not at.error and not at.warning, label


def test_tab_content_is_the_selected_tab(fake_cache):
    labels = {m.label for m in open_stock("PTT", tab_label("Financials")).metric}
    assert "Revenue" in labels and "Bid / Offer" not in labels


def test_financials_tab_with_no_data_shows_warning(fake_cache):
    fake_cache["financials"] = pd.DataFrame(columns=FIN_COLUMNS)
    at = open_stock("PTT", tab_label("Financials"))
    assert not at.exception
    assert any("no financial statements" in w.value.lower() for w in at.warning)


def test_financials_tab_warns_when_figures_come_from_the_fallback_source(fake_cache):
    fin = financials(years=3)
    fin.attrs["fallback_note"] = "thaifin is unavailable right now, so these figures come from Yahoo Finance"
    fake_cache["financials"] = fin
    at = open_stock("PTT", tab_label("Financials"))
    assert not at.exception
    assert [w.value for w in at.warning] == [fin.attrs["fallback_note"]]


def test_valuation_tab_with_no_history_shows_info(fake_cache):
    fake_cache["financials"] = financials(years=1)
    at = open_stock("PTT", tab_label("Valuation"))
    assert not at.exception
    assert any("not enough" in i.value.lower() for i in at.info)


@pytest.mark.parametrize("page", ["screener", "stock"])
def test_both_pages_warn_only_when_the_set100_list_has_expired(fake_cache, monkeypatch, page):
    import datetime

    import src.universe

    def expiry_warnings():
        at = AppTest.from_file(ROOT / f"app_pages/{page}.py", default_timeout=60)
        at.query_params["symbol"] = "PTT"
        at.run()
        assert not at.exception
        return [w for w in at.warning if "set100.csv" in w.value]

    assert expiry_warnings() == []  # the fixture keeps the list current
    monkeypatch.setattr(src.universe, "SET100_PERIOD_END", datetime.date(2000, 1, 1))
    assert len(expiry_warnings()) == 1


def test_stock_outside_set100_opens_on_every_tab(fake_cache):
    for label in stock_tab_labels():
        at = open_stock("MAJOR", label)
        assert not at.exception, (label, at.exception)
        assert at.title[0].value == "MAJOR · MAJOR"
        assert at.caption[0].value == "Outside SET100"
        assert not at.error and not at.warning, label


def test_symbol_typed_in_lowercase_is_upper_cased(fake_cache):
    at = open_stock("major")
    assert not at.exception
    assert at.title[0].value == "MAJOR · MAJOR"


def test_stock_unknown_to_yahoo_warns_instead_of_failing(fake_cache):
    def no_data(symbols):
        df = snapshots(symbols)
        df["price"] = np.nan  # what get_snapshots returns when Yahoo has nothing for the symbol
        return df

    fake_cache["snapshot"] = no_data
    at = open_stock("NOSUCH", tab_label("Trading"))
    assert not at.exception and not at.error
    assert any("NOSUCH" in w.value for w in at.warning)


def test_valuation_tab_compares_dividend_yield_in_percentage_points(fake_cache):
    at = open_stock("PTT", tab_label("Valuation"))
    at.segmented_control(key="val_metric").set_value("Dividend yield").run()
    assert not at.exception and not at.info
    # Yields 1.0/20 = 5.0%, 1.2/30 = 4.0%, 1.4/35 = 4.0% -> median 4.0%; current 5.0% (fixture) -> +1.0 pp
    text = " ".join(m.value for m in at.markdown)
    assert "**+1.0 pp**" in text and "median of 4.0%" in text and "cheaper than usual" in text


def test_stock_page_links_to_the_set_website_and_shows_free_float(fake_cache):
    at = open_stock("PTT", tab_label("Trading"))
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "https://www.set.or.th/en/market/product/stock/quote/PTT/major-shareholders" in text
    assert {m.label: m.value for m in at.metric}["Free float (Yahoo estimate)"] == "40%"


def test_symbol_with_markdown_in_the_url_is_rejected(fake_cache):
    at = open_stock("PTT)[Click me](https://evil.example")
    assert not at.exception
    assert at.error[0].value.startswith("A SET symbol has only")
    assert not at.title and "evil.example" not in " ".join(m.value for m in at.markdown)


def test_screener_has_growth_columns_and_sorts_by_them(fake_cache):
    at = AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    assert not at.exception
    table = at.dataframe[0].value
    assert {"rev_cagr5", "ni_cagr5", "roe_avg5"} <= set(table.columns)
    assert table.sort_values("rev_cagr5", ascending=False)["symbol"].iloc[0] == "AOT"  # highest fake CAGR


def test_fair_value_tab_shows_ddm_dcf_and_f_score(fake_cache):
    at = open_stock("PTT", tab_label("Fair value"))
    assert not at.exception and not at.error
    labels = {m.label for m in at.metric}
    assert {"Fair value (DDM)", "Fair value (DCF)", "Margin of safety", "F-score"} <= labels
    assert len(at.dataframe) == 2  # one 3×3 sensitivity table per model
    assert all(df.value.shape == (3, 3) for df in at.dataframe)
    assert any("not investment advice" in i.value for i in at.info)


def test_fair_value_tab_skips_dcf_for_banks(fake_cache):
    at = open_stock("KBANK", tab_label("Fair value"))
    assert not at.exception
    labels = {m.label for m in at.metric}
    assert "Fair value (DDM)" in labels and "Fair value (DCF)" not in labels
    assert any("banks" in i.value for i in at.info)


def test_prediction_tab_shows_each_walk_forward_period(fake_cache):
    at = open_stock("PTT", tab_label("Prediction"))
    assert not at.exception
    periods = at.dataframe[0].value
    assert len(periods) == 4 and list(periods.columns) == ["Period", "Model", "Baseline", "Model − baseline"]
    assert any("per buy or sell" in c.value for c in at.caption)
