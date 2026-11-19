"""Tests use synthetic prices, so they run offline and give the same result every time."""

import numpy as np
import pandas as pd

from src.indicators import add_indicators
from src.model import FEATURES, build_dataset, train_and_backtest


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
    # Test period must be the most recent dates (the last day has no answer yet, so it is excluded).
    assert result.test.index.max() == df.index[-2]
    n_labeled = len(build_dataset(df).dropna(subset=["Next_return"]))
    assert len(result.test) == n_labeled - int(n_labeled * 0.8)
