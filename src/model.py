"""Predict whether tomorrow's close will be higher than today's — and test it honestly.

Approach:
- Target: 1 if next day's Close > today's Close, else 0 (classification).
- Features: indicators from src/indicators.py, made scale-free (ratios, %)
  so a $10 stock and a $1000 stock look the same to the model.
- Walk-forward by TIME: the newest 40% is split into 4 test windows; each window's model is trained only on
  the data before it, with a 1-day gap so no training answer falls inside the test window.
  (A random split would let the model learn from the future = leakage.)
- Compare against a naive baseline: "always guess the most common answer".
- The trading strategy pays COST_PER_TRADE each time it buys or sells.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

COST_PER_TRADE = 0.0017  # per side: roughly a Thai online broker's commission + VAT
WINDOWS = 4
TEST_FRACTION = 0.4

FEATURES = ["Return", "Volatility20", "RSI14", "Volume_change", "Close_vs_SMA20", "Close_vs_SMA50", "SMA20_vs_SMA50"]


@dataclass
class BacktestResult:
    accuracy: float  # model accuracy over all test windows
    baseline_accuracy: float  # accuracy of always guessing each window's training majority class
    test: pd.DataFrame  # test rows with Prediction, Prob_up, and equity curves (strategy after costs)
    feature_importance: pd.Series
    next_day_prob_up: float  # model's probability that the NEXT trading day closes higher
    windows: pd.DataFrame  # one row per walk-forward window: train_end, test_start, test_end, accuracy, baseline
    cost_per_trade: float


def strategy_returns(next_return: pd.Series, position: pd.Series, cost_per_trade: float) -> pd.Series:
    """Daily return of holding `position` (1 = in the stock, 0 = cash) minus `cost_per_trade` for every
    buy or sell. The first day counts as a buy when the position is 1 (starting from cash)."""
    trades = position.diff().abs().fillna(position.abs())
    return next_return * position - trades * cost_per_trade


def _model() -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=20, random_state=42)


def build_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Add model features + target to a DataFrame that already has indicators."""
    data = df.copy()
    data["Close_vs_SMA20"] = data["Close"] / data["SMA20"] - 1
    data["Close_vs_SMA50"] = data["Close"] / data["SMA50"] - 1
    data["SMA20_vs_SMA50"] = data["SMA20"] / data["SMA50"] - 1
    data["Next_return"] = data["Close"].pct_change().shift(-1)  # tomorrow's return (the answer)
    data["Target"] = (data["Next_return"] > 0).astype(int)
    data = data.replace([np.inf, -np.inf], np.nan)
    return data.dropna(subset=FEATURES)


def train_and_backtest(df: pd.DataFrame, windows: int = WINDOWS, test_fraction: float = TEST_FRACTION,
                       cost_per_trade: float = COST_PER_TRADE) -> BacktestResult:
    """Walk-forward evaluation over `windows` consecutive test windows covering the newest `test_fraction`."""
    data = build_dataset(df)
    latest = data.iloc[[-1]]  # today: features known, answer (tomorrow) not yet known
    labeled = data.dropna(subset=["Next_return"])
    n = len(labeled)
    if n < 200:
        raise ValueError("Not enough history to train (need ~1 year+). Choose a longer period.")

    bounds = np.linspace(int(n * (1 - test_fraction)), n, windows + 1).astype(int)
    parts, rows, model = [], [], _model()
    for start, end in zip(bounds[:-1], bounds[1:]):
        # Gap: drop the row just before the window. Its target is the first test day's close.
        train, test = labeled.iloc[: start - 1], labeled.iloc[start:end].copy()
        model = _model().fit(train[FEATURES], train["Target"])
        test["Prob_up"] = model.predict_proba(test[FEATURES])[:, 1]
        test["Prediction"] = (test["Prob_up"] > 0.5).astype(int)
        test["Baseline"] = int(train["Target"].mean() >= 0.5)
        parts.append(test)
        rows.append({"train_end": train.index[-1], "test_start": test.index[0], "test_end": test.index[-1],
                     "accuracy": accuracy_score(test["Target"], test["Prediction"]),
                     "baseline": accuracy_score(test["Target"], test["Baseline"])})
    test = pd.concat(parts)

    # Strategy: hold the stock tomorrow only when the model predicts "up"; otherwise hold cash.
    test["Buy_and_hold"] = (1 + test["Next_return"]).cumprod()
    test["Model_before_costs"] = (1 + test["Next_return"] * test["Prediction"]).cumprod()
    test["Model_strategy"] = (1 + strategy_returns(test["Next_return"], test["Prediction"], cost_per_trade)).cumprod()

    final = _model().fit(labeled[FEATURES], labeled["Target"])  # all known answers, for tomorrow's guess
    return BacktestResult(
        accuracy=accuracy_score(test["Target"], test["Prediction"]),
        baseline_accuracy=accuracy_score(test["Target"], test["Baseline"]),
        test=test,
        feature_importance=pd.Series(model.feature_importances_, index=FEATURES).sort_values(),
        next_day_prob_up=float(final.predict_proba(latest[FEATURES])[0, 1]),
        windows=pd.DataFrame(rows),
        cost_per_trade=cost_per_trade,
    )
