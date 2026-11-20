"""Backlog #19: holdings are checked, saved to a gitignored file, and edited on the Portfolio page."""

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit
from streamlit.testing.v1 import AppTest

from src import portfolio

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


# ---------- Portfolio page ----------

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


def test_page_saves_edited_table(csv_path, monkeypatch):
    at = run_page_with_edits(monkeypatch, table([("ptt", 1000, 34.5), ("AOT", 0, np.nan)]))
    assert not at.exception and not at.error
    saved = pd.read_csv(csv_path)
    assert saved["symbol"].tolist() == ["PTT", "AOT"]
    assert saved["shares"].tolist() == [1000, 0]


def test_page_does_not_save_bad_input(csv_path, monkeypatch):
    at = run_page_with_edits(monkeypatch, table([("", 1000, 34.5), ("AOT", -5, 10.0)]))
    assert not at.exception
    assert not csv_path.exists()
    assert len(at.error) == 1
    assert "symbol is empty" in at.error[0].value and "can't be negative" in at.error[0].value
