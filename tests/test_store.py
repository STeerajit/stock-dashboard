"""Backlog #10: the daily data store (DuckDB): update safely and incrementally, read back what the app needs."""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from src import store
from src.fundamentals import FIN_COLUMNS, SNAPSHOT_COLUMNS

DAYS = pd.bdate_range("2026-11-02", "2026-11-13")  # 10 trading days


def raw_prices(days=DAYS, close=10.0) -> pd.DataFrame:
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000.0},
                        index=days)


class FakeSources:
    """Offline fetchers that record what was asked for."""

    def __init__(self, failing=(), bad_price=False):
        self.failing, self.bad_price = set(failing), bad_price
        self.price_requests: list[tuple[str, date | None]] = []
        self.today_days = DAYS

    def prices(self, symbol, start):
        self.price_requests.append((symbol, start))
        if symbol in self.failing:
            raise ConnectionError("down")
        days = self.today_days if start is None else self.today_days[self.today_days >= pd.Timestamp(start)]
        df = raw_prices(days)
        if self.bad_price:
            df.iloc[-1, df.columns.get_loc("Close")] = 0.0
        return df

    def dividends(self, symbol):
        return pd.Series([1.0], index=pd.to_datetime(["2026-11-09"]))

    def snapshot(self, symbol):
        if symbol in self.failing:
            raise ConnectionError("down")
        return {"symbol": symbol, "price": 10.0, "pe": 12.0, "ex_div_date": pd.Timestamp("2026-11-09")}

    def financials(self, symbol):
        fin = pd.DataFrame({c: [1.0, 2.0] for c in FIN_COLUMNS}, index=[2024, 2025])
        fin.attrs = {"source": "thaifin"}
        return fin

    def fetchers(self) -> store.Fetchers:
        return store.Fetchers(self.prices, self.dividends, self.snapshot, self.financials)


SYMBOLS = ["PTT", "AOT", "KBANK", "SCB", "CPALL"]
NOW = datetime(2026, 11, 13, 18, 30)


@pytest.fixture
def db(tmp_path):
    return tmp_path / "market.duckdb"


def counts(db) -> dict[str, int]:
    with store.connect(db) as con:
        return {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("prices", "dividends", "snapshots", "financials")}


# ---------- dividend adjustment (computed when reading, so incremental updates stay correct) ----------

def test_prices_before_an_xd_date_are_scaled_down_by_the_dividend():
    raw = raw_prices(pd.bdate_range("2026-11-02", periods=4))
    raw["Close"] = [10.0, 10.0, 9.0, 9.0]
    dividends = pd.Series([1.0], index=pd.to_datetime(["2026-11-04"]))  # XD on the 3rd day
    adj = store.adjust_for_dividends(raw, dividends)
    # factor before the XD date = 1 - 1.00 / 10.00 (the close the day before) = 0.9
    assert adj["Close"].tolist() == pytest.approx([9.0, 9.0, 9.0, 9.0])
    assert adj["High"].iloc[0] == pytest.approx(11.0 * 0.9)
    assert adj["Volume"].iloc[0] == 1000.0  # volume is not scaled


def test_without_dividends_prices_are_unchanged():
    raw = raw_prices()
    pd.testing.assert_frame_equal(store.adjust_for_dividends(raw, pd.Series(dtype=float)), raw)


# ---------- update ----------

def test_update_writes_every_table(db):
    report = store.update_store(db, SYMBOLS, FakeSources().fetchers(), now=NOW)
    assert report.failed == []
    assert counts(db) == {"prices": 50, "dividends": 5, "snapshots": 5, "financials": 10}


def test_running_twice_on_the_same_day_changes_nothing(db):
    src = FakeSources()
    store.update_store(db, SYMBOLS, src.fetchers(), now=NOW)
    before = counts(db)
    store.update_store(db, SYMBOLS, src.fetchers(), now=NOW)
    assert counts(db) == before


def test_second_run_asks_only_for_days_after_the_last_stored_one(db):
    src = FakeSources()
    src.today_days = DAYS[:5]  # first run: data up to Fri 6 Nov
    store.update_store(db, SYMBOLS, src.fetchers(), now=NOW)
    assert all(start is None for _, start in src.price_requests)

    src.price_requests.clear()
    src.today_days = DAYS  # a week later
    store.update_store(db, SYMBOLS, src.fetchers(), now=NOW)
    assert {start for _, start in src.price_requests} == {date(2026, 11, 7)}
    assert counts(db)["prices"] == 50


def test_too_many_failures_leave_the_store_untouched(db):
    store.update_store(db, SYMBOLS, FakeSources().fetchers(), now=NOW)
    before = counts(db)
    with pytest.raises(store.UpdateError, match="2 of 5"):
        store.update_store(db, SYMBOLS, FakeSources(failing={"PTT", "AOT"}).fetchers(), now=datetime(2026, 11, 14))
    assert counts(db) == before
    assert store.as_of(db) == NOW


def test_one_failure_is_skipped_and_the_rest_is_saved(db):
    report = store.update_store(db, SYMBOLS, FakeSources(failing={"PTT"}).fetchers(), now=NOW)  # 20%: allowed
    assert report.failed == ["PTT"]
    assert counts(db)["snapshots"] == 4


def test_a_zero_price_aborts_the_update(db):
    with pytest.raises(store.UpdateError, match="price"):
        store.update_store(db, SYMBOLS, FakeSources(bad_price=True).fetchers(), now=NOW)
    assert not db.exists() or counts(db)["prices"] == 0


# ---------- reading back ----------

def test_read_back_what_the_app_needs(db):
    store.update_store(db, SYMBOLS, FakeSources().fetchers(), now=NOW)
    assert store.has(db, "PTT") and not store.has(db, "MAJOR")
    assert store.as_of(db) == NOW

    prices = store.load_prices(db, "PTT")
    assert list(prices.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(prices) == 10 and isinstance(prices.index, pd.DatetimeIndex)
    assert prices["Close"].iloc[0] == pytest.approx(9.0)  # before the 9 Nov XD date: 10 × (1 - 1/10)
    assert store.load_close(db, "PTT").iloc[0] == 10.0  # as traded

    assert store.load_dividends_per_year(db, "PTT").to_dict() == {2026: 1.0}

    fin = store.load_financials(db, "PTT")
    assert list(fin.columns) == FIN_COLUMNS and list(fin.index) == [2024, 2025]
    assert fin.attrs["source"] == "thaifin" and "liabilities" in fin.attrs["de_definition"].lower()

    snaps = store.load_snapshots(db, ["PTT", "MAJOR"])
    assert list(snaps.columns) == SNAPSHOT_COLUMNS
    assert snaps.set_index("symbol").loc["PTT", "pe"] == 12.0
    assert np.isnan(snaps.set_index("symbol").loc["MAJOR", "price"])  # not stored: counts as failed


def test_no_store_file_means_nothing_stored(db):
    assert store.as_of(db) is None and not store.has(db, "PTT")


# ---------- the app reads the store, with the network blocked (conftest) ----------

from pathlib import Path  # noqa: E402

from streamlit.testing.v1 import AppTest  # noqa: E402

from src import cache  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def offline_app(db, monkeypatch):
    """A filled store, the app pointed at it, and a 5-stock SET100; every network call fails (conftest)."""
    src = FakeSources()
    src.today_days = pd.bdate_range("2024-01-02", "2026-11-13")  # enough history for the chart and the model
    store.update_store(db, SYMBOLS, src.fetchers(), now=NOW)
    monkeypatch.setattr(store, "STORE_PATH", db)
    monkeypatch.setattr(cache, "set100", lambda: pd.DataFrame({
        "symbol": SYMBOLS, "name": SYMBOLS, "sector": ["Energy & Utilities", "Transportation & Logistics",
                                                       "Banking", "Banking", "Commerce"], "in_set50": True}))


def test_screener_renders_from_the_store_offline_and_says_as_of_when(offline_app):
    at = AppTest.from_file(ROOT / "app.py", default_timeout=60).run()
    at.switch_page("app_pages/screener.py").run()
    assert not at.exception and not at.error
    assert len(at.dataframe[0].value) == 5
    assert any("Data as of **13 Nov 2026 18:30**" in c.value for c in at.sidebar.caption)


def test_stock_page_renders_from_the_store_offline(offline_app):
    at = AppTest.from_file(ROOT / "app_pages/stock.py", default_timeout=60)
    at.query_params["symbol"] = "PTT"
    for tab in [None, "Chart", "Financials", "Valuation", "Dividends"]:
        if tab:
            at.session_state["tab"] = next(t.label for t in at.tabs if tab in t.label)
        at.run()
        assert not at.exception, (tab, at.exception)
        assert not at.error and not any("No price data" in w.value for w in at.warning), tab


def test_a_download_that_fails_once_is_retried(db):
    src = FakeSources()
    calls = {"n": 0}
    real = src.snapshot

    def flaky(symbol):
        if symbol == "PTT" and calls["n"] == 0:
            calls["n"] += 1
            raise ConnectionError("Invalid Crumb")
        return real(symbol)

    src.snapshot = flaky
    assert store.update_store(db, SYMBOLS, src.fetchers(), now=NOW).failed == []
