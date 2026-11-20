"""Tests use synthetic prices, so they run offline and give the same result every time."""

import numpy as np
import pandas as pd
import pytest

from src.indicators import add_indicators
from src.model import COST_PER_TRADE, FEATURES, build_dataset, strategy_returns, train_and_backtest


def fake_prices(n: int = 600, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
         "Volume": rng.integers(1_000, 10_000, n).astype(float)},
        index=idx,
    )


def test_features_do_not_use_future_prices():
    """Changing a future price must not change any feature computed on earlier days."""
    df = fake_prices()
    a = build_dataset(add_indicators(df))
    df.iloc[-1, df.columns.get_loc("Close")] *= 2  # tamper with the last day only
    b = build_dataset(add_indicators(df))
    pd.testing.assert_frame_equal(a[FEATURES].iloc[:-1], b[FEATURES].iloc[:-1])


def test_target_is_next_day_direction():
    data = build_dataset(add_indicators(fake_prices()))
    i = 10
    went_up = data["Close"].iloc[i + 1] > data["Close"].iloc[i]
    assert data["Target"].iloc[i] == int(went_up)


def test_backtest_tests_on_the_newest_data():
    df = add_indicators(fake_prices())
    result = train_and_backtest(df)
    assert 0 <= result.accuracy <= 1
    assert 0 <= result.next_day_prob_up <= 1
    # The test windows end at the most recent labeled day (the last day has no answer yet).
    assert result.test.index.max() == df.index[-2]


def test_walk_forward_uses_at_least_4_consecutive_windows():
    result = train_and_backtest(add_indicators(fake_prices(900)))
    w = result.windows
    assert len(w) >= 4
    assert (w["test_start"].iloc[1:].to_numpy() > w["test_end"].iloc[:-1].to_numpy()).all()  # in time order
    assert result.accuracy == pytest.approx((result.test["Prediction"] == result.test["Target"]).mean())


def test_each_window_trains_only_on_data_before_it_with_a_one_day_gap():
    df = add_indicators(fake_prices(900))
    result = train_and_backtest(df)
    days = build_dataset(df).index
    for _, w in result.windows.iterrows():
        # The last training row's target is the next day's close, which must still be before the test window.
        day_after_train = days[days.get_loc(w["train_end"]) + 1]
        assert day_after_train < w["test_start"]


def test_costs_are_charged_on_every_entry_and_exit():
    next_return = pd.Series([0.01, 0.01, 0.01, 0.01])
    position = pd.Series([1, 1, 0, 1])  # enter, hold, exit, enter: 3 trades
    net = strategy_returns(next_return, position, cost_per_trade=0.001)
    assert net.tolist() == pytest.approx([0.01 - 0.001, 0.01, -0.001, 0.01 - 0.001])


def test_a_strategy_that_flips_every_day_ends_lower_with_costs():
    next_return = pd.Series(np.full(250, 0.001))
    position = pd.Series([1, 0] * 125)
    without = (1 + strategy_returns(next_return, position, cost_per_trade=0)).prod()
    with_costs = (1 + strategy_returns(next_return, position, cost_per_trade=COST_PER_TRADE)).prod()
    assert with_costs < without


def test_backtest_reports_strategy_after_costs():
    result = train_and_backtest(add_indicators(fake_prices(900)))
    assert result.cost_per_trade == COST_PER_TRADE
    gross = (1 + result.test["Next_return"] * result.test["Prediction"]).prod()
    assert result.test["Model_strategy"].iloc[-1] <= gross + 1e-12
