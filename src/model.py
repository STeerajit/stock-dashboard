"""Predict whether tomorrow's close will be higher than today's — and test it honestly.

Approach:
- Target: 1 if next day's Close > today's Close, else 0 (classification).
- Features: indicators from src/indicators.py, made scale-free (ratios, %)
  so a $10 stock and a $1000 stock look the same to the model.
- Split by TIME: train on the older 80%, test on the newest 20%.
  (A random split would let the model learn from the future = leakage.)
- Compare against a naive baseline: "always guess the most common answer".
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

FEATURES = ["Return", "Volatility20", "RSI14", "Volume_change", "Close_vs_SMA20", "Close_vs_SMA50", "SMA20_vs_SMA50"]


@dataclass
class BacktestResult:
    accuracy: float  # model accuracy on the test period
    baseline_accuracy: float  # accuracy of always guessing the majority class
    test: pd.DataFrame  # test rows with Prediction, Prob_up, and equity curves
    feature_importance: pd.Series
    next_day_prob_up: float  # model's probability that the NEXT trading day closes higher


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


def train_and_backtest(df: pd.DataFrame, test_size: float = 0.2) -> BacktestResult:
    """Train on older data, evaluate on the newest `test_size` fraction."""
    data = build_dataset(df)
    latest = data.iloc[[-1]]  # today: features known, answer (tomorrow) not yet known
    labeled = data.dropna(subset=["Next_return"])
    if len(labeled) < 200:
        raise ValueError("Not enough history to train (need ~1 year+). Choose a longer period.")

    split = int(len(labeled) * (1 - test_size))
    train, test = labeled.iloc[:split], labeled.iloc[split:].copy()

    model = RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=20, random_state=42)
    model.fit(train[FEATURES], train["Target"])

    test["Prob_up"] = model.predict_proba(test[FEATURES])[:, 1]
    test["Prediction"] = (test["Prob_up"] > 0.5).astype(int)

    # Strategy: hold the stock tomorrow only when the model predicts "up"; otherwise hold cash.
    test["Buy_and_hold"] = (1 + test["Next_return"]).cumprod()
    test["Model_strategy"] = (1 + test["Next_return"] * test["Prediction"]).cumprod()

    majority = int(train["Target"].mean() >= 0.5)
    return BacktestResult(
        accuracy=accuracy_score(test["Target"], test["Prediction"]),
        baseline_accuracy=accuracy_score(test["Target"], np.full(len(test), majority)),
        test=test,
        feature_importance=pd.Series(model.feature_importances_, index=FEATURES).sort_values(),
        next_day_prob_up=float(model.predict_proba(latest[FEATURES])[0, 1]),
    )
