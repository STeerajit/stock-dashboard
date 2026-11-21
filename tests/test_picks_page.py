"""Offline tests for the Dividend picks page: every loader is replaced with in-memory fakes."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src import cache, picks_backtest
from src.fundamentals import SNAPSHOT_COLUMNS, SnapshotError
from tests.test_dividend_picks import dividends, financials, stock

ROOT = Path(__file__).resolve().parent.parent
SYMBOLS = [f"S{i:02d}" for i in range(60)]
DATA = {s: stock(vol=0.005 + i * 0.0003, seed=i, div=dividends(amount=1 + i / 20), fin=financials(eps=(5,) * 5))
        for i, s in enumerate(SYMBOLS)}


@pytest.fixture
def fake_picks(monkeypatch):
    state = {"data": DATA, "results": None}
    monkeypatch.setattr(cache, "picks_data", lambda: state["data"])
    monkeypatch.setattr(cache, "set100", lambda: pd.DataFrame(
        {"symbol": SYMBOLS, "name": [f"Company {s}" for s in SYMBOLS], "sector": "Banking", "in_set50": True}))
    monkeypatch.setattr(cache, "snapshots", lambda: pd.DataFrame({"symbol": SYMBOLS}).reindex(columns=SNAPSHOT_COLUMNS))
    monkeypatch.setattr(cache, "growth", lambda: pd.DataFrame({"symbol": SYMBOLS, "fscore": 7, "fscore_available": 8}))
    monkeypatch.setattr(picks_backtest, "load_results", lambda path=None: state["results"])
    return state


def run(lang: str | None = None) -> AppTest:
    """Run the whole app (st.page_link needs app.py's navigation), then switch to Dividend picks."""
    at = AppTest.from_file(ROOT / "app.py", default_timeout=60)
    if lang:
        at.session_state["lang_choice"] = lang
    at.run()
    at.switch_page("app_pages/dividend_picks.py")
    return at.run()


def test_page_lists_ten_picks_with_their_signals(fake_picks):
    at = run()
    assert not at.exception
    table = at.dataframe[0].value
    assert len(table) == 10 and table["rank"].tolist() == list(range(1, 11))
    heads = [m.value for m in at.markdown if m.value.startswith("#### ")]
    assert len(heads) == 10 and heads[0].startswith(f"#### 1. {table['symbol'].iloc[0]} —")
    assert len(at.columns) == 20  # buy and sell side by side in each card
    assert sum("Buy signals" in m.value for m in at.markdown) == 10
    assert not any("evidence" in m.value for m in at.markdown)  # sources are left out to keep it light


def test_without_a_backtest_the_summary_labels_are_hidden(fake_picks):
    at = run()
    assert any("has not been run yet" in i.value for i in at.info)
    assert not any("Buy now" in m.value or "Sell" in m.value for m in at.markdown if m.value.startswith("#### "))


def test_backtest_results_are_shown_when_saved(fake_picks):
    rule = {"cagr": 0.08, "passed": True}
    fake_picks["results"] = {"start": "2016-11", "end": "2026-10", "base": {"cagr": 0.07},
                             "benchmark": {"cagr": 0.05}, "rules": {"buy_now": rule, "sell_now": rule}}
    at = run()
    assert not at.exception and not any("summary" in i.value.lower() for i in at.info)
    assert len(at.dataframe) == 2 and "7.0%" in " ".join(m.value for m in at.markdown)


def test_page_works_in_thai(fake_picks):
    at = run("th")
    assert not at.exception
    assert at.title[0].value == "หุ้นปันผลน่าถือ"


def test_too_few_stocks_shows_an_error(fake_picks):
    fake_picks["data"] = dict(list(DATA.items())[:10])
    at = run()
    assert at.error and not at.dataframe


def test_snapshot_outage_does_not_break_the_page(fake_picks, monkeypatch):
    def down():
        raise SnapshotError("down")

    monkeypatch.setattr(cache, "snapshots", down)
    assert not run().exception


def test_picks_loader_falls_back_to_yahoo_without_a_store(fake_yahoo):
    d = cache._picks_one("PTT")
    assert d is not None and not d.prices.empty and not d.close.empty
    assert d.dividends.index.tz is None and d.dividends.tolist() == [1.0, 1.2, 1.5]


def test_picks_loader_skips_a_stock_that_fails(fake_yahoo):
    fake_yahoo.failing = {"PTT"}
    assert cache._picks_one("PTT") is None


def test_equal_weight_index_averages_daily_returns():
    from src.dividend_picks import StockData, equal_weight_index

    idx = pd.bdate_range("2026-01-05", periods=3)
    a = pd.DataFrame({"Close": [10.0, 11.0, 11.0]}, index=idx)  # +10%, 0%
    b = pd.DataFrame({"Close": [20.0, 20.0, 18.0]}, index=idx)  # 0%, -10%
    empty = pd.Series(dtype=float)
    index = equal_weight_index({"A": StockData(a, a["Close"], empty, pd.DataFrame()),
                                "B": StockData(b, b["Close"], empty, pd.DataFrame())})
    assert index.tolist() == pytest.approx([100.0, 105.0, 99.75])


def test_each_pick_card_shows_its_dividend_safety(fake_picks):
    at = run()
    assert not at.exception
    lines = [m.value for m in at.markdown if m.value.startswith("**Dividend safety:**")]
    assert len(lines) == 10 and all("-badge[" in v for v in lines)
    assert all("banks" in v for v in lines)  # every fake stock is a bank: FCF payout is skipped, and it says so
