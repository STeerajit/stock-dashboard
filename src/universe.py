"""The list of stocks the app covers: SET50 constituents.

SET reviews the index every 6 months (effective 1 Jan and 1 Jul), so the list
lives in a CSV that is easy to update, not in code.
"""

from datetime import date
from pathlib import Path

import pandas as pd

SET50_CSV = Path(__file__).resolve().parent.parent / "data" / "set50.csv"
SET50_PERIOD = "1 Jul – 31 Dec 2026"
SET50_PERIOD_END = date(2026, 12, 31)  # last day the CSV's list is valid; update together with SET50_PERIOD

# The SET sector names (exactly as SET prints them) that SET50 stocks belong to today.
# Deliberately only the sectors in use, so a typo in the CSV fails the test. When an index
# review brings in a stock from a new sector, check SET's spelling and add the name here.
SET_SECTORS = frozenset({
    "Banking", "Commerce", "Construction Materials", "Electronic Components", "Energy & Utilities",
    "Finance & Securities", "Food & Beverage", "Health Care Services", "Information & Communication Technology",
    "Insurance", "Packaging", "Petrochemicals & Chemicals", "Property Development", "Tourism & Leisure",
    "Transportation & Logistics",
})


def load_set50() -> pd.DataFrame:
    """Columns: symbol, name, sector (sector names as used by SET)."""
    return pd.read_csv(SET50_CSV)


def yahoo_symbol(symbol: str) -> str:
    """SET symbol -> Yahoo Finance ticker, e.g. PTT -> PTT.BK."""
    return f"{symbol}.BK"


def set50_expiry_warning(today: date, period_end: date | None = None) -> str | None:
    """A warning to show users once the SET50 list is past its period (None while it is current).

    `period_end` defaults to SET50_PERIOD_END.
    """
    end = period_end or SET50_PERIOD_END
    if today <= end:
        return None
    return (
        f"This SET50 list was valid until {end:%-d %b %Y}. SET has likely published a new list, "
        "so some stocks may be missing or no longer in SET50. Update data/set50.csv (see README)."
    )
