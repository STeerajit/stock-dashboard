"""Dividend income calendar: how many baht arrive in which month, before and after the 10% withholding tax.

Each month holds last complete year's dividends with an XD date in that month × shares held now, so the yearly
gross equals `est_dividend` in portfolio.positions(). The free data has XD dates only: payment usually follows
about a month later, and no payment date is invented here.
"""

import pandas as pd

TAX = 0.10  # Thai withholding tax on cash dividends
MONTHS = range(1, 13)


def _in_year(ev: pd.Series, year: int) -> pd.Series:
    return ev[pd.DatetimeIndex(ev.index).year == year]


def monthly(events: dict[str, pd.Series], shares: dict[str, float], this_year: int) -> pd.DataFrame:
    """Gross dividend in baht per expected XD month (rows 1-12), one column per held stock (shares > 0).
    Amounts come from the last complete year (this_year - 1) only; a stock that paid nothing then is all 0."""
    cal = {}
    for sym, n in shares.items():
        if n > 0:
            last = _in_year(events.get(sym, pd.Series(dtype=float)), this_year - 1)
            cal[sym] = (last.groupby(pd.DatetimeIndex(last.index).month).sum() * n).reindex(MONTHS, fill_value=0.0)
    return pd.DataFrame(cal, index=pd.Index(MONTHS, name="month"), dtype=float)


def by_month(calendar: pd.DataFrame) -> pd.DataFrame:
    """Portfolio gross, tax and net per month (rows 1-12)."""
    gross = calendar.sum(axis=1)
    return pd.DataFrame({"gross": gross, "tax": gross * TAX, "net": gross * (1 - TAX)})


def may_shift(ev: pd.Series, this_year: int) -> bool:
    """True if the year before last paid in other XD months than last year (both years must have paid)."""
    months = [set(pd.DatetimeIndex(_in_year(ev, y).index).month) for y in (this_year - 2, this_year - 1)]
    return all(months) and months[0] != months[1]


def summary(pos: pd.DataFrame, calendar: pd.DataFrame, events: dict[str, pd.Series], this_year: int) -> pd.DataFrame:
    """One row per stock in the calendar (watchlist rows are not): yearly gross and net, net yield on cost
    (net / cost), `no_recent` (paid nothing last complete year) and `may_shift` (XD months changed)."""
    held = pos[pos["symbol"].isin(calendar.columns)]
    gross = calendar.sum().reindex(held["symbol"]).to_numpy()
    net = gross * (1 - TAX)
    return pd.DataFrame({
        "symbol": held["symbol"].to_numpy(),
        "gross": gross,
        "net": net,
        "net_yield_on_cost": net / held["cost"].where(held["cost"] > 0).to_numpy(),
        "no_recent": gross == 0,
        "may_shift": [may_shift(events.get(s, pd.Series(dtype=float)), this_year) for s in held["symbol"]],
    })
