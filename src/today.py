"""Rules for the Today page: which held or watched stocks deserve a look today, and why.

Pure functions (no network, no Streamlit), so every rule is unit-tested at its boundary.
"""

from datetime import date

import pandas as pd

from src.indicators import support_resistance

NEAR_SUPPORT = 0.03  # price at most 3% above the nearest support
RSI_LOW, RSI_HIGH = 30, 70  # strictly below / above
EVENT_DAYS = 14  # XD or earnings within 14 days, counting today as day 1
CHEAP_PE = 0.20  # P/E more than 20% below its own median


def price_levels(prices: pd.DataFrame) -> tuple[float, float | None, float | None]:
    """(last close, nearest support today, nearest resistance as of yesterday).

    Resistance comes from the data up to yesterday: by definition every level above today's price is a
    resistance, so only yesterday's levels can show that today's price broke through one.
    """
    price = float(prices["Close"].iloc[-1])
    supports, _ = support_resistance(prices)
    _, resistances = support_resistance(prices.iloc[:-1]) if len(prices) > 1 else ([], [])
    return price, (supports[0] if supports else None), (resistances[0] if resistances else None)


def _event(name: str, when, today: date) -> str | None:
    if when is None or pd.isna(when):
        return None
    day = pd.Timestamp(when).date()
    days = (day - today).days
    if not 0 <= days < EVENT_DAYS:
        return None
    label = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
    return f"{name} {label} ({day.day} {day:%b %Y})"


def reasons(*, today: date, price: float, support: float | None, resistance_before_today: float | None,
            rsi: float, ex_div_date, earnings_date, pe: float, pe_median: float | None) -> list[str]:
    """Why this stock is flagged today; an empty list means it isn't. Missing data never flags a rule."""
    # None -> NaN: every comparison with NaN is False, so a rule with missing data simply doesn't fire.
    price, support, resistance, rsi, pe, pe_median = (
        float("nan") if x is None else float(x)
        for x in (price, support, resistance_before_today, rsi, pe, pe_median))
    out = []
    if 0 < support <= price <= support * (1 + NEAR_SUPPORT):
        out.append(f"Near support: price {price:.2f} is {price / support - 1:.1%} above support {support:.2f}")
    if price > resistance:
        out.append(f"Broke resistance: price {price:.2f} is above yesterday's resistance {resistance:.2f}")
    if rsi < RSI_LOW:
        out.append(f"RSI {rsi:.1f} — oversold (below {RSI_LOW})")
    elif rsi > RSI_HIGH:
        out.append(f"RSI {rsi:.1f} — overbought (above {RSI_HIGH})")
    for name, when in (("XD date", ex_div_date), ("Earnings date", earnings_date)):
        if text := _event(name, when, today):
            out.append(text)
    if 0 < pe < pe_median * (1 - CHEAP_PE):
        out.append(f"Cheap vs. its history: P/E {pe:.1f} is {1 - pe / pe_median:.0%} below its median {pe_median:.1f}")
    return out
