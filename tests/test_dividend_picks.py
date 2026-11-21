import numpy as np
import pandas as pd
import pytest

from src import dividend_picks as dp

AS_OF = pd.Timestamp("2026-11-20")


def prices(vol: float = 0.01, drift: float = 0.0, seed: int = 0, start: str = "2019-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start, AS_OF)
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + drift + rng.normal(0, vol, len(idx)))
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": 1e6}, index=idx)


def financials(eps=(1.0, 1.1, 1.2, 1.3, 1.4), shares=(1e9, 1e9), last_year: int = 2025) -> pd.DataFrame:
    years = range(last_year - len(eps) + 1, last_year + 1)
    fin = pd.DataFrame({"EPS": list(eps)}, index=list(years))
    fin["Shares"] = np.nan
    fin.loc[list(years)[-len(shares):], "Shares"] = list(shares)
    return fin


def dividends(years=range(2019, 2027), amount: float = 1.0, month: int = 4) -> pd.Series:
    return pd.Series(amount, index=pd.to_datetime([f"{y}-{month:02d}-10" for y in years]), dtype=float)


def stock(vol=0.01, drift=0.0, seed=0, fin=None, div=None) -> dp.StockData:
    """Adjusted prices are a random walk; the traded close stays at 100, so yields depend only on dividends."""
    p = prices(vol, drift, seed)
    flat = pd.Series(100.0, index=p.index)
    return dp.StockData(p, flat, dividends() if div is None else div, financials() if fin is None else fin)


def row(df: pd.DataFrame, symbol: str) -> pd.Series:
    return df.set_index("symbol").loc[symbol]


def test_published_financials_waits_three_months_after_year_end():
    fin = financials(last_year=2025)
    assert dp.published_financials(fin, pd.Timestamp("2026-03-30")).index.max() == 2024
    assert dp.published_financials(fin, pd.Timestamp("2026-03-31")).index.max() == 2025


def test_weekly_volatility_needs_156_weeks():
    assert np.isnan(dp.weekly_volatility(prices(start="2024-01-01"), AS_OF))
    low, high = dp.weekly_volatility(prices(0.005), AS_OF), dp.weekly_volatility(prices(0.02), AS_OF)
    assert 0 < low < high


def test_momentum_skips_the_latest_month():
    idx = pd.bdate_range("2025-01-01", AS_OF)
    close = pd.Series(100.0, index=idx)
    close[close.index > AS_OF - pd.DateOffset(months=1)] = 500.0  # a jump inside the last month is ignored
    close[close.index <= AS_OF - pd.DateOffset(months=12)] = 80.0
    assert dp.momentum_12_1(pd.DataFrame({"Close": close}), AS_OF) == pytest.approx(100 / 80 - 1)


def test_trailing_dividends_use_the_last_12_months_only():
    div = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2025-11-20", "2025-11-21", "2026-11-21"]))
    assert dp.trailing_dividends(div, AS_OF) == 2.0  # one year back is out, the future one too


def test_paid_every_year_counts_the_last_five_complete_years():
    assert dp.paid_every_year(dividends(range(2021, 2026)), AS_OF)
    assert not dp.paid_every_year(dividends([2021, 2022, 2024, 2025]), AS_OF)  # 2023 skipped
    assert not dp.paid_every_year(dividends(range(2022, 2026)), AS_OF)  # only 4 years


def test_buyback_yield_is_positive_when_shares_fall():
    assert dp.buyback_yield(financials(shares=(1e9, 0.98e9))) == pytest.approx(0.02)
    assert dp.buyback_yield(financials(shares=(1e9, 1.05e9))) == pytest.approx(-0.05)
    assert dp.buyback_yield(financials(shares=(1e9,))) == 0.0


def test_low_volatility_keeps_50_of_more():
    data = {f"S{i:03d}": stock(vol=0.005 + i * 0.0002, seed=i) for i in range(60)}
    df = dp.screen(data, AS_OF)
    assert (df["stage"] != "high_vol").sum() == dp.LOW_VOL_KEEP
    assert row(df, "S059")["stage"] == "high_vol" and row(df, "S000")["stage"] == "ok"


@pytest.mark.parametrize("fin,div,stage", [
    (None, dividends([2021, 2022, 2024, 2025, 2026]), "no_dividend"),
    (financials(eps=(1.0, 1.1, 1.2, 1.3, -0.5)), None, "eps_negative"),
    (financials(eps=(1.0, 1.1, 1.2, 1.3, 0.9)), dividends(amount=1.0), "payout"),  # 1.0 / 0.9 > 100%
    (financials(eps=(2.0, 1.9, 1.8, 1.7)), None, "eps_declining"),
])
def test_dividend_traps_are_dropped(fin, div, stage):
    df = dp.screen({"TRAP": stock(fin=fin, div=div), "GOOD": stock(seed=1)}, AS_OF)
    assert row(df, "TRAP")["stage"] == stage and pd.isna(row(df, "TRAP")["rank"])
    assert row(df, "GOOD")["rank"] == 1


def test_payout_of_exactly_100_percent_passes():
    df = dp.screen({"X": stock(fin=financials(eps=(1.0, 1.1, 1.2, 1.3, 1.0)), div=dividends(amount=1.0))}, AS_OF)
    assert row(df, "X")["payout"] == pytest.approx(1.0) and row(df, "X")["stage"] == "ok"


def test_two_eps_declines_are_not_three():
    df = dp.screen({"X": stock(fin=financials(eps=(1.0, 2.0, 1.9, 1.8)))}, AS_OF)
    assert row(df, "X")["stage"] == "ok"


def test_rank_averages_payout_yield_and_momentum_ranks():
    data = {
        "HIGHYIELD": stock(seed=1, div=dividends(amount=6.0), fin=financials(eps=(7, 7, 7, 7, 7))),
        "MOMENTUM": stock(seed=1, drift=0.002, div=dividends(amount=2.0), fin=financials(eps=(7, 7, 7, 7, 7))),
        "BOTH": stock(seed=1, drift=0.002, div=dividends(amount=5.0), fin=financials(eps=(7, 7, 7, 7, 7))),
    }
    df = dp.screen(data, AS_OF)
    assert dp.picks(df)[0] == "BOTH"
    assert row(df, "BOTH")["net_payout_yield"] == pytest.approx(row(df, "BOTH")["div_yield"])  # no buyback


def test_buybacks_count_only_when_enabled(monkeypatch):
    data = {"X": stock(fin=financials(eps=(5,) * 5, shares=(1e9, 0.9e9)))}
    assert row(dp.screen(data, AS_OF), "X")["net_payout_yield"] == pytest.approx(0.01)  # 1 baht / 100
    monkeypatch.setattr(dp, "USE_BUYBACKS", True)
    assert row(dp.screen(data, AS_OF), "X")["net_payout_yield"] == pytest.approx(0.11)


def test_picks_returns_at_most_ten_best_first():
    data = {f"S{i:02d}": stock(seed=0, div=dividends(amount=1 + i / 10), fin=financials(eps=(5,) * 5))
            for i in range(15)}
    top = dp.picks(dp.screen(data, AS_OF))
    assert len(top) == dp.PICKS and top[0] == "S14"


def test_screen_uses_only_data_known_on_the_date():
    future = stock(div=pd.concat([dividends(range(2019, 2026)), pd.Series([50.0], index=[AS_OF + pd.Timedelta(days=5)])]))
    df = dp.screen({"X": future}, AS_OF)
    assert row(df, "X")["div_yield"] < 0.1  # the 50-baht dividend after AS_OF is not counted


def test_missing_history_is_not_ranked():
    p = prices(start="2025-06-01")
    df = dp.screen({"NEW": dp.StockData(p, p["Close"], dividends(), financials())}, AS_OF)
    assert row(df, "NEW")["stage"] == "no_data"


def test_changes_lists_entered_and_left():
    assert dp.changes(["A", "B", "C"], ["B", "C", "D"]) == (["A"], ["D"])


def test_payout_uses_the_last_four_published_quarters_when_newer_than_the_year():
    # Yearly EPS 2025 = 1.4 (payout 1.0 / 1.4 = 71%), but the 4 quarters to Sep 2026 earned only 0.8 a share.
    from tests.test_quarterly import quarters

    d = stock()._replace(quarterly=quarters(4, eps=0.2))
    df = dp.screen({"A": d}, AS_OF)
    assert row(df, "A")["eps"] == pytest.approx(0.8)
    assert row(df, "A")["payout"] == pytest.approx(1.0 / 0.8)
    assert row(df, "A")["stage"] == "payout"
    # Before Q3 2026 is out (45 days) only 3 quarters are published: the yearly EPS is used.
    assert row(dp.screen({"A": d}, pd.Timestamp("2026-11-13")), "A")["eps"] == pytest.approx(1.4)


def test_payout_falls_back_to_the_yearly_eps_without_quarters():
    assert row(dp.screen({"A": stock()}, AS_OF), "A")["payout"] == pytest.approx(1.0 / 1.4)
