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
from src.fundamentals import FIN_COLUMNS
from src.indicators import add_indicators
from src.model import train_and_backtest
from tests.fakes import fake_prices

ROOT = Path(__file__).resolve().parent.parent
TABS = [":material/swap_vert: Trading", ":material/candlestick_chart: Chart", ":material/account_balance: Financials",
        ":material/sell: Valuation", ":material/event: Dividends & calendar",
        ":material/online_prediction: Prediction"]

UNIVERSE = pd.DataFrame({
    "symbol": ["PTT", "PTTEP", "KBANK", "SCB", "CPALL", "AOT"],
    "name": ["PTT", "PTT Exploration", "Kasikornbank", "SCB X", "CP All", "Airports of Thailand"],
    "sector": ["Energy & Utilities", "Energy & Utilities", "Banking", "Banking", "Commerce",
               "Transportation & Logistics"],
})


def snapshots() -> pd.DataFrame:
    n = len(UNIVERSE)
    return pd.DataFrame({
        "symbol": UNIVERSE["symbol"], "price": np.linspace(30, 80, n), "change_pct": 0.01,
        "volume": 2e6, "avg_volume": 1e6, "value_traded": 1e8, "bid": 29.9, "ask": 30.1,
        "high_52w": 90.0, "low_52w": 20.0, "pos_52w": 0.5, "market_cap": np.linspace(1e12, 1e11, n),
        "pe": np.linspace(8, 20, n), "pbv": 1.2, "div_yield": 0.05, "roe": 0.1, "de": 0.8, "net_margin": 0.08,
        "ex_div_date": pd.Timestamp("2026-08-19"), "earnings_date": pd.NaT,
    })


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
    state = {"financials": financials()}
    monkeypatch.setattr(cache, "set50", lambda: UNIVERSE.copy())
    monkeypatch.setattr(cache, "snapshots", snapshots)
    monkeypatch.setattr(cache, "prices", lambda symbol, period="5y": PRICES)
    monkeypatch.setattr(cache, "financials", lambda symbol: state["financials"])
    monkeypatch.setattr(cache, "dividends", lambda symbol: pd.Series([1.0, 1.2, 1.4], index=[2023, 2024, 2025]))
    monkeypatch.setattr(cache, "backtest", lambda symbol: train_and_backtest(PRICES))
    return state


def open_stock(symbol: str, tab: str | None = None) -> AppTest:
    at = AppTest.from_file(ROOT / "app_pages/stock.py", default_timeout=60)
    at.query_params["symbol"] = symbol
    if tab:
        at.session_state["tab"] = tab
    return at.run()


def test_screener_renders_all_rows(fake_cache):
    at = AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    assert not at.exception and not at.error
    assert len(at.dataframe[0].value) == len(UNIVERSE)


def test_screener_sector_filter_reduces_rows(fake_cache):
    at = AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    at.multiselect(key="sectors").select("Banking").run()
    assert not at.exception
    assert set(at.dataframe[0].value["symbol"]) == {"KBANK", "SCB"}


@pytest.mark.parametrize("tab", TABS)
def test_every_stock_tab_renders(fake_cache, tab):
    at = open_stock("PTT", tab)
    assert not at.exception, at.exception
    assert at.title[0].value == "PTT · PTT"
    assert not at.error and not at.warning


def test_tab_content_is_the_selected_tab(fake_cache):
    labels = {m.label for m in open_stock("PTT", TABS[2]).metric}  # Financials
    assert "Revenue" in labels and "Bid / Offer" not in labels


def test_financials_tab_with_no_data_shows_warning(fake_cache):
    fake_cache["financials"] = pd.DataFrame(columns=FIN_COLUMNS)
    at = open_stock("PTT", TABS[2])
    assert not at.exception
    assert any("no financial statements" in w.value.lower() for w in at.warning)


def test_valuation_tab_with_no_history_shows_info(fake_cache):
    fake_cache["financials"] = financials(years=1)
    at = open_stock("PTT", TABS[3])
    assert not at.exception
    assert any("not enough" in i.value.lower() for i in at.info)
