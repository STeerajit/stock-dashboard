from datetime import date

import numpy as np
import pandas as pd
import pytest

from src import signals
from src.dividend_picks import StockData

AS_OF = pd.Timestamp("2026-10-31")


def data(close, dividends=None, start="2022-01-03") -> StockData:
    idx = pd.bdate_range(start, periods=len(close))
    c = pd.Series(close, index=idx, dtype=float)
    p = pd.DataFrame({"Open": c, "High": c * 1.001, "Low": c * 0.999, "Close": c, "Volume": 1e6})
    div = dividends if dividends is not None else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    return StockData(p, c, div, pd.DataFrame())


def rising(n=1250):
    return np.linspace(50, 100, n)


def falling(n=1250):
    return np.linspace(100, 50, n)


def compute(d, rank=1, stage="ok", **kw):
    return signals.compute(d, d.prices.index[-1], rank=rank, stage=stage, **kw)


def test_trend_compares_the_month_end_close_with_its_10_month_average():
    up, down = compute(data(rising())), compute(data(falling()))
    assert up["trend"].on and not up["below_trend"].on
    assert not down["trend"].on and down["below_trend"].on


def test_trend_is_off_without_10_months_and_never_signals_a_sale():
    sig = compute(data(rising(150)))
    assert not sig["trend"].on and not sig["below_trend"].on
    assert sig["trend"].label == "Less than 10 months of prices."


def test_market_trend_uses_the_index_when_given():
    d = data(rising())
    index = pd.Series(falling(), index=d.prices.index)
    assert "market_trend" not in compute(d)
    assert not compute(d, market_close=index)["market_trend"].on


def test_rsi_low_and_pullback_fire_after_a_sharp_drop():
    close = np.concatenate([rising(1200), np.linspace(100, 70, 50)])
    sig = compute(data(close))
    assert sig["rsi_low"].on and sig["pullback"].on
    assert not compute(data(rising()))["rsi_low"].on


def test_macd_and_obv_are_up_in_a_steady_rise():
    sig = compute(data(rising()))
    assert sig["macd"].on and sig["obv"].on
    sig = compute(data(np.concatenate([falling(1200), np.linspace(50, 40, 50)])))  # the fall speeds up
    assert not sig["macd"].on and not sig["obv"].on


def test_dividend_month_is_the_month_it_went_xd_a_year_ago():
    d = data(rising(), pd.Series([1.0], index=pd.to_datetime(["2025-10-15"])))
    assert signals.compute(d, AS_OF, rank=1, stage="ok")["dividend_month"].on
    assert not signals.compute(d, pd.Timestamp("2026-09-30"), rank=1, stage="ok")["dividend_month"].on


def test_days_to_xd_is_shown_only_for_a_future_date():
    d = data(rising())
    assert compute(d, ex_div_date=pd.Timestamp("2026-11-10"), today=date(2026, 11, 1))["days_to_xd"].label.startswith(
        "XD in 9 days")
    assert "days_to_xd" not in compute(d, ex_div_date=pd.Timestamp("2026-10-01"), today=date(2026, 11, 1))
    assert "days_to_xd" not in compute(d)


@pytest.mark.parametrize("amounts,cut", [((2.0, 1.5), True), ((2.0, 0.0), True), ((1.5, 2.0), False),
                                         ((0.0, 0.0), False)])
def test_dividend_cut_compares_the_last_two_complete_years(amounts, cut):
    div = pd.Series(list(amounts), index=pd.to_datetime(["2024-04-10", "2025-04-10"]))
    assert signals.dividend_cut(div[div > 0], AS_OF)[0] is cut


def test_rank_out_fires_below_20_or_when_unranked():
    d = data(rising())
    assert not compute(d, rank=20)["rank_out"].on
    assert compute(d, rank=21)["rank_out"].on
    assert compute(d, rank=pd.NA, stage="high_vol")["rank_out"].on


def test_trap_signal_follows_the_screen_stage():
    d = data(rising())
    assert compute(d, stage="payout")["trap"].on and not compute(d, stage="high_vol")["trap"].on


def test_summary_buy_needs_a_pick_in_an_uptrend_with_rsi_low_or_support():
    d = data(rising())
    sig = compute(d)
    sig_support = {**sig, "near_support": sig["near_support"]._replace(on=True)}
    assert signals.buy_now(sig_support, 1)
    assert not signals.buy_now(sig_support, 11)  # not in the 10 picks
    assert not signals.buy_now({**sig, "near_support": sig["near_support"]._replace(on=False),
                                "rsi_low": sig["rsi_low"]._replace(on=False)}, 1)


def test_summary_sell_on_rank_or_trend():
    up, down = data(rising()), data(falling())
    assert not signals.sell_now(compute(up, rank=5))
    assert signals.sell_now(compute(up, rank=25)) and signals.sell_now(compute(down, rank=5))


def test_every_signal_has_metadata_and_thai_labels():
    d = data(rising(), pd.Series([1.0, 1.0], index=pd.to_datetime(["2024-10-10", "2025-10-10"])))
    sig = signals.compute(d, AS_OF, rank=3, stage="ok", market_close=d.close, lang="th")
    assert set(sig) <= set(signals.SIGNALS)
    assert all(s.label for s in sig.values())


def test_signals_ignore_prices_after_the_date():
    close = np.concatenate([rising(1200), np.full(50, 10.0)])  # a crash after the date
    d = data(close)
    before = d.prices.index[1199]
    assert signals.compute(d, before, rank=1, stage="ok")["trend"].on


def test_short_text_says_what_an_on_signal_means_and_names_an_off_one():
    up = compute(data(rising()), rank=30)
    assert up["trend"].short.startswith("Uptrend:") and up["macd"].short.startswith("MACD crossed up")
    assert up["rsi_low"].short.startswith("RSI ") and not up["rsi_low"].on  # off: just its name and value
    assert up["rank_out"].short == "Rank fell to 30"
    assert up["below_trend"].short == "" and up["trap"].short == ""  # sell signals that are off say nothing
    down = compute(data(falling()))
    assert down["trend"].short == "Trend" and down["below_trend"].short.startswith("Below its 10-month average")
