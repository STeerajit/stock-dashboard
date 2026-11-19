"""Offline tests for the valuation and support/resistance helpers."""

import pandas as pd

from src.fundamentals import pe_history, sector_medians
from src.indicators import support_resistance


def test_support_resistance_finds_levels_on_both_sides():
    # Price swings between ~90 and ~110, then ends at 100 -> support near 90, resistance near 110.
    wave = [100, 105, 110, 105, 100, 95, 90, 95] * 10 + [100]
    idx = pd.bdate_range("2024-01-01", periods=len(wave))
    df = pd.DataFrame({"High": wave, "Low": wave, "Close": wave}, index=idx, dtype=float)
    supports, resistances = support_resistance(df, window=3)
    assert supports and resistances
    assert all(s < 100 for s in supports) and all(r > 100 for r in resistances)
    assert abs(supports[0] - 90) < 2 and abs(resistances[0] - 110) < 2


def test_pe_history_uses_year_end_price_and_skips_losses():
    idx = pd.to_datetime(["2023-06-30", "2023-12-29", "2024-12-30"])
    prices = pd.DataFrame({"Close": [50.0, 40.0, 30.0]}, index=idx)
    fin = pd.DataFrame({"EPS": [4.0, -1.0]}, index=[2023, 2024])
    pe = pe_history(prices, fin)
    assert pe.to_dict() == {2023: 10.0}  # 40 / 4; 2024 skipped because EPS < 0


def test_sector_medians():
    universe = pd.DataFrame({"symbol": ["A", "B", "C"], "sector": ["Bank", "Bank", "Energy"]})
    snaps = pd.DataFrame({"symbol": ["A", "B", "C"], "pe": [10, 20, 8], "pbv": [1, 2, 1],
                          "div_yield": [0.05, 0.03, 0.04], "roe": [0.1, 0.2, 0.1]})
    med = sector_medians(snaps, universe)
    assert med.loc["Bank", "pe"] == 15 and med.loc["Energy", "pe"] == 8


def test_get_financials_falls_back_to_yahoo_when_thaifin_fails(monkeypatch):
    import src.fundamentals as fd

    def broken(symbol):
        raise ConnectionError("thaifin source down")

    yahoo = pd.DataFrame({"Revenue": [1.0, 2.0]}, index=[2024, 2025])
    monkeypatch.setattr(fd, "_financials_thaifin", broken)
    monkeypatch.setattr(fd, "_financials_yahoo", lambda symbol: yahoo)
    assert fd.get_financials("PTT") is yahoo
