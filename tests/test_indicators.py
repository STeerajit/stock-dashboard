import numpy as np
import pandas as pd
import pytest

from src.charts import EXTRAS, price_chart
from src.indicators import add_indicators, sma_10_month
from tests.fakes import fake_prices


def frame(close, volume=1000.0) -> pd.DataFrame:
    close = pd.Series(close, dtype=float, index=pd.bdate_range("2024-01-01", periods=len(close)))
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": volume})


def test_flat_price_gives_zero_macd_and_closed_bollinger_bands():
    df = add_indicators(frame([50.0] * 60))
    assert df["MACD"].abs().max() == 0 and df["MACD_signal"].abs().max() == 0
    last = df.iloc[-1]
    assert last["BB_upper"] == last["BB_lower"] == last["SMA20"] == 50.0


def test_bollinger_bands_are_two_population_standard_deviations():
    df = add_indicators(frame([1, 3] * 10))  # 20 days alternating 1 and 3: mean 2, population std 1
    assert df["BB_upper"].iloc[-1] == pytest.approx(4.0) and df["BB_lower"].iloc[-1] == pytest.approx(0.0)


def test_rising_price_has_positive_macd():
    df = add_indicators(frame(np.linspace(10, 20, 60)))
    assert df["MACD"].iloc[-1] > 0 and df["MACD_hist"].iloc[-1] > 0


def test_obv_adds_volume_on_up_days_and_subtracts_on_down_days():
    df = add_indicators(frame([10, 11, 11, 9, 12], volume=[100.0, 200.0, 300.0, 400.0, 500.0]))
    assert df["OBV"].tolist() == [0, 200, 200, -200, 300]


def test_sma200_needs_200_days():
    df = add_indicators(fake_prices(250))
    assert df["SMA200"].iloc[198:].isna().tolist()[0] and df["SMA200"].iloc[199:].notna().all()
    assert df["SMA200"].iloc[-1] == pytest.approx(df["Close"].tail(200).mean())


def test_sma_10_month_uses_month_end_closes():
    idx = pd.bdate_range("2025-01-01", "2025-12-15")
    close = pd.Series(np.arange(len(idx), dtype=float), index=idx)
    monthly = sma_10_month(close)
    assert len(monthly) == 12 and monthly.index[0] == pd.Timestamp("2025-01-31")
    assert monthly["Close"].iloc[-1] == close.iloc[-1]  # the unfinished month counts with its latest close
    assert monthly["SMA10M"].iloc[:9].isna().all() and monthly["SMA10M"].iloc[9:].notna().all()
    assert monthly["SMA10M"].iloc[-1] == pytest.approx(monthly["Close"].tail(10).mean())


@pytest.mark.parametrize("extras,panels", [(set(), 3), ({"macd"}, 4), ({"macd", "obv"}, 5)])
def test_chart_adds_a_panel_per_oscillator(extras, panels):
    fig = price_chart(add_indicators(fake_prices(300)), "PTT", [], [], extras=extras)
    yaxes = [k for k in fig.layout.to_plotly_json() if k.startswith("yaxis")]
    assert len(yaxes) == panels


def test_chart_draws_sma200_and_bollinger_only_when_switched_on():
    df = add_indicators(fake_prices(300))
    names = lambda fig: {tr.name for tr in fig.data}  # noqa: E731
    assert "SMA200" not in names(price_chart(df, "PTT", [], [])) and "SMA20" in names(price_chart(df, "PTT", [], []))
    on = names(price_chart(df, "PTT", [], [], extras=set(EXTRAS)))
    assert {"SMA200", "Bollinger upper", "Bollinger lower", "MACD", "OBV"} <= on
