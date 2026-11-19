"""Backlog #6: unit conversions from thaifin and Yahoo Finance are correct."""

import math

import pandas as pd
import pytest
import thaifin

import src.fundamentals as fd
from tests.fakes import fake_info

THAIFIN_COLS = ["revenue", "net_profit", "earning_per_share", "revenue_yoy", "net_profit_yoy", "gpm", "npm", "roe",
                "debt_to_equity", "operating_activities", "investing_activities", "price_earning_ratio",
                "price_book_value", "dividend_yield"]


def thaifin_frame(rows: dict[int, dict]) -> pd.DataFrame:
    """A fake thaifin `yearly_dataframe`: Period index, ratios in percent, some None cells."""
    base = dict.fromkeys(THAIFIN_COLS, 1.0)
    df = pd.DataFrame([{**base, **r} for r in rows.values()], index=pd.PeriodIndex([str(y) for y in rows], freq="Y"))
    return df.astype(object)


class FakeStock:
    frame = pd.DataFrame()

    def __init__(self, symbol):
        self.yearly_dataframe = FakeStock.frame


@pytest.fixture
def fake_thaifin(monkeypatch):
    monkeypatch.setattr(thaifin, "Stock", FakeStock)
    return FakeStock


# ---------- thaifin ----------

def test_thaifin_percent_ratios_become_fractions(fake_thaifin):
    fake_thaifin.frame = thaifin_frame({2024: {"gpm": 50, "npm": 12.5, "roe": 8, "revenue_yoy": -10},
                                        2025: {"gpm": 40, "npm": 10, "roe": 9, "revenue_yoy": 20}})
    fin = fd._financials_thaifin("PTT")
    assert fin.loc[2024, "Gross margin"] == 0.5
    assert fin.loc[2024, "Net margin"] == 0.125
    assert fin.loc[2025, "ROE"] == 0.09
    assert fin.loc[2024, "Revenue growth"] == -0.1


def test_thaifin_zero_pe_and_pbv_mean_missing(fake_thaifin):
    fake_thaifin.frame = thaifin_frame({2024: {"price_earning_ratio": 0, "price_book_value": 0},
                                        2025: {"price_earning_ratio": 9.5, "price_book_value": 0.8}})
    fin = fd._financials_thaifin("PTT")
    assert math.isnan(fin.loc[2024, "P/E"]) and math.isnan(fin.loc[2024, "P/BV"])
    assert fin.loc[2025, "P/E"] == 9.5


def test_thaifin_none_cells_become_nan_without_error(fake_thaifin):
    fake_thaifin.frame = thaifin_frame({2024: {"investing_activities": None, "earning_per_share": None},
                                        2025: {"operating_activities": 5.0, "investing_activities": -2.0}})
    fin = fd._financials_thaifin("PTT")
    assert math.isnan(fin.loc[2024, "EPS"]) and math.isnan(fin.loc[2024, "Free cash flow"])
    assert fin.loc[2025, "Free cash flow"] == 3.0  # operating + investing


def test_thaifin_metadata_and_shape(fake_thaifin):
    fake_thaifin.frame = thaifin_frame({2025: {}, 2023: {}, 2024: {}})
    fin = fd._financials_thaifin("PTT")
    assert fin.attrs["source"] == "thaifin"
    assert "liabilities" in fin.attrs["de_definition"].lower()
    assert list(fin.index) == [2023, 2024, 2025]  # oldest first
    assert list(fin.columns) == fd.FIN_COLUMNS
    assert "Dividend yield" not in fin.columns  # thaifin's yield has inconsistent units


def test_falls_back_to_yahoo_when_thaifin_has_under_2_years(fake_thaifin, monkeypatch):
    fake_thaifin.frame = thaifin_frame({2025: {}})
    yahoo = pd.DataFrame({"Revenue": [1.0, 2.0]}, index=[2024, 2025])
    monkeypatch.setattr(fd, "_financials_yahoo", lambda symbol: yahoo)
    assert fd.get_financials("MRDIYT") is yahoo


def test_uses_thaifin_when_it_has_2_or_more_years(fake_thaifin, monkeypatch):
    fake_thaifin.frame = thaifin_frame({2024: {}, 2025: {}})
    monkeypatch.setattr(fd, "_financials_yahoo", lambda symbol: pytest.fail("should not fall back"))
    assert fd.get_financials("PTT").attrs["source"] == "thaifin"


# ---------- Yahoo snapshot ----------

@pytest.fixture
def snapshot_with(fake_yahoo, monkeypatch):
    """Call get_snapshot with a custom `info` dict."""

    def run(**overrides):
        info = {**fake_info(), **overrides}
        monkeypatch.setattr(type(fake_yahoo("X")), "info", property(lambda self: info))
        return fd.get_snapshot("PTT")

    return run


def test_dividend_yield_percent_becomes_fraction(snapshot_with):
    assert snapshot_with(dividendYield=4.78)["div_yield"] == pytest.approx(0.0478)


def test_debt_to_equity_x100_becomes_ratio(snapshot_with):
    assert snapshot_with(debtToEquity=57.4)["de"] == pytest.approx(0.574)


def test_missing_yield_and_de_are_nan(snapshot_with):
    snap = snapshot_with(dividendYield=None, debtToEquity=None)
    assert math.isnan(snap["div_yield"]) and math.isnan(snap["de"])


@pytest.mark.parametrize("price,expected", [(20.0, 0.0), (30.0, 0.5), (40.0, 1.0)])
def test_position_in_52_week_range(snapshot_with, price, expected):
    snap = snapshot_with(currentPrice=price, fiftyTwoWeekLow=20.0, fiftyTwoWeekHigh=40.0)
    assert snap["pos_52w"] == pytest.approx(expected)


def test_change_and_value_traded(snapshot_with):
    snap = snapshot_with(currentPrice=110.0, previousClose=100.0, volume=1000)
    assert snap["change_pct"] == pytest.approx(0.10)
    assert snap["value_traded"] == 110_000.0
