"""Rules for the Today page: which held or watched stocks deserve a look today, and why.

Pure functions (no network, no Streamlit), so every rule is unit-tested at its boundary.
"""

from datetime import date

import pandas as pd

from src.i18n import text
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


def _event(name: str, when, today: date, lang: str) -> str | None:
    if when is None or pd.isna(when):
        return None
    day = pd.Timestamp(when).date()
    days = (day - today).days
    if not 0 <= days < EVENT_DAYS:
        return None
    label = (text("reason.today", lang) if days == 0 else text("reason.tomorrow", lang) if days == 1
             else text("reason.in_days", lang, days=days))
    return text("reason.event", lang, name=name, when=label, date=f"{day.day} {day:%b %Y}")


def reasons(*, today: date, price: float, support: float | None, resistance_before_today: float | None,
            rsi: float, ex_div_date, earnings_date, pe: float, pe_median: float | None, lang: str = "en") -> list[str]:
    """Why this stock is flagged today; an empty list means it isn't. Missing data never flags a rule."""
    # None -> NaN: every comparison with NaN is False, so a rule with missing data simply doesn't fire.
    price, support, resistance, rsi, pe, pe_median = (
        float("nan") if x is None else float(x)
        for x in (price, support, resistance_before_today, rsi, pe, pe_median))
    out = []
    if 0 < support <= price <= support * (1 + NEAR_SUPPORT):
        out.append(text("reason.near_support", lang, price=price, gap=price / support - 1, support=support))
    if price > resistance:
        out.append(text("reason.broke_resistance", lang, price=price, resistance=resistance))
    if rsi < RSI_LOW:
        out.append(text("reason.oversold", lang, rsi=rsi, low=RSI_LOW))
    elif rsi > RSI_HIGH:
        out.append(text("reason.overbought", lang, rsi=rsi, high=RSI_HIGH))
    for name, when in (("reason.xd", ex_div_date), ("reason.earnings", earnings_date)):
        if event := _event(text(name, lang), when, today, lang):
            out.append(event)
    if 0 < pe < pe_median * (1 - CHEAP_PE):
        out.append(text("reason.cheap", lang, pe=pe, gap=1 - pe / pe_median, median=pe_median))
    return out
