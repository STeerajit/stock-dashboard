"""Backlog #4: screener row -> stock page.

Clicking a dataframe row can't be simulated in AppTest, so this tests the two halves:
which symbol a selected row maps to, and that the stock page opens that symbol.
"""

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.screener import selected_symbol

ROOT = Path(__file__).resolve().parent.parent


def table():
    return pd.DataFrame({
        "symbol": ["PTT", "KBANK", "AOT", "SCB", "KTB", "CPALL"],
        "sector": ["Energy & Utilities", "Banking", "Transportation & Logistics", "Banking", "Banking", "Commerce"],
        "market_cap": [10, 9, 8, 7, 6, 5],
    })


def test_no_selection():
    assert selected_symbol(table(), []) is None


def test_row_position_maps_to_the_row_shown():
    shown = table().sort_values("market_cap", ascending=False)
    assert selected_symbol(shown, [0]) == "PTT"


def test_filtered_table_third_row_is_third_visible_bank():
    df = table()
    shown = df[df["sector"] == "Banking"].sort_values("market_cap", ascending=False)  # KBANK, SCB, KTB
    assert selected_symbol(shown, [2]) == "KTB"  # not "AOT", the 3rd stock overall


def test_selecting_a_row_opens_the_stock_page_with_the_symbol_in_the_url(fake_yahoo, monkeypatch):
    # Regression (found in a real browser): the screener used to pass the symbol through
    # session_state only, so the URL stayed /stock and a reload or bookmark opened ADVANC.
    import streamlit as st

    import src.screener

    calls = []

    def fake_switch_page(page, **kwargs):
        calls.append((page, kwargs))
        st.stop()

    monkeypatch.setattr(src.screener, "selected_symbol", lambda shown, rows: "KBANK")  # a row was clicked
    monkeypatch.setattr(st, "switch_page", fake_switch_page)
    AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    assert calls == [("app_pages/stock.py", {"query_params": {"symbol": "KBANK"}})]


def test_stock_page_opens_symbol_from_url(fake_yahoo):
    at = AppTest.from_file(ROOT / "app_pages/stock.py", default_timeout=30)
    at.query_params["symbol"] = "SCB"
    at.run()
    assert not at.exception and at.title[0].value.startswith("SCB")
