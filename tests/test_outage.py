"""Backlog #2: the app survives Yahoo Finance outages."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src import cache
from src import fundamentals as fd

SYMBOLS = ["PTT", "KBANK", "AOT", "CPALL", "SCB"]
ROOT = Path(__file__).resolve().parent.parent


def test_all_columns_present_when_every_fetch_fails(fake_yahoo):
    fake_yahoo.down = True
    df = fd.get_snapshots(SYMBOLS)
    assert list(df.columns) == fd.SNAPSHOT_COLUMNS
    assert df["symbol"].tolist() == SYMBOLS
    assert df.drop(columns="symbol").isna().all().all()


def test_one_failing_symbol_does_not_affect_the_others(fake_yahoo):
    fake_yahoo.failing = {"AOT"}
    df = fd.get_snapshots(SYMBOLS).set_index("symbol")
    assert pd.isna(df.loc["AOT", "price"])
    assert df.drop(index="AOT")["price"].notna().all()


def test_coverage_check_raises_above_20_percent_failed():
    ok = pd.DataFrame({"symbol": list("ABCDE"), "price": [1.0, 1.0, 1.0, 1.0, None]})  # 20% failed
    assert fd.check_snapshot_coverage(ok) is ok
    bad = pd.DataFrame({"symbol": list("ABCDE"), "price": [1.0, 1.0, 1.0, None, None]})  # 40% failed
    with pytest.raises(fd.SnapshotError, match="try again"):
        fd.check_snapshot_coverage(bad)


def test_outage_is_not_cached(fake_yahoo):
    fake_yahoo.down = True
    with pytest.raises(fd.SnapshotError):
        cache.snapshots()
    fake_yahoo.down = False  # Yahoo is back: the very next call must fetch again, not reuse the failure
    snaps = cache.snapshots()
    assert snaps["price"].notna().all() and len(snaps) == 50


def test_screener_shows_error_not_traceback_when_yahoo_is_down(fake_yahoo):
    fake_yahoo.down = True
    at = AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    assert not at.exception
    assert len(at.error) == 1 and "try again" in at.error[0].value.lower()
    assert len(at.dataframe) == 0


def test_screener_renders_49_rows_when_one_symbol_fails(fake_yahoo):
    fake_yahoo.failing = {"PTT"}
    at = AppTest.from_file(ROOT / "app_pages/screener.py", default_timeout=30).run()
    assert not at.exception and not at.error
    table = at.dataframe[0].value
    assert len(table) == 50 and table["price"].notna().sum() == 49


def test_stock_page_trading_tab_warns_when_yahoo_is_down(fake_yahoo):
    fake_yahoo.down = True
    at = AppTest.from_file(ROOT / "app_pages/stock.py", default_timeout=30)
    at.query_params["symbol"] = "PTT"
    at.run()
    assert not at.exception
    assert at.title[0].value.startswith("PTT")
    assert any("market data" in w.value.lower() or "try again" in w.value.lower() for w in at.warning)
