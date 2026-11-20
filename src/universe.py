"""The list of stocks the app covers: SET100 constituents (with a flag for SET50).

SET reviews the index every 6 months (effective 1 Jan and 1 Jul), so the list
lives in a CSV that is easy to update, not in code.
"""

import re
from datetime import date
from pathlib import Path

import pandas as pd

from src.i18n import text

SET100_CSV = Path(__file__).resolve().parent.parent / "data" / "set100.csv"
SET100_PERIOD = "1 Jul – 31 Dec 2026"
SET100_PERIOD_END = date(2026, 12, 31)  # last day the CSV's list is valid; update together with SET100_PERIOD

# Sector shown for a stock that is not in the list. Yahoo's sector names differ from SET's, so they aren't mixed in.
OUTSIDE_SET100 = "Outside SET100"

# The SET sector names (exactly as SET prints them) that SET100 stocks belong to today.
# Deliberately only the sectors in use, so a typo in the CSV fails the test. When an index
# review brings in a stock from a new sector, check SET's spelling and add the name here.
SET_SECTORS = frozenset({
    "Agribusiness", "Banking", "Commerce", "Construction Materials", "Construction Services",
    "Electronic Components", "Energy & Utilities", "Fashion", "Finance & Securities", "Food & Beverage",
    "Health Care Services", "Information & Communication Technology", "Insurance", "Media & Publishing",
    "Packaging", "Personal Products & Pharmaceuticals", "Petrochemicals & Chemicals", "Property Development",
    "Tourism & Leisure", "Transportation & Logistics",
})


def load_set100() -> pd.DataFrame:
    """Columns: symbol, name, sector (sector names as used by SET), in_set50 (bool)."""
    return pd.read_csv(SET100_CSV)


def describe(universe: pd.DataFrame, symbol: str) -> tuple[str, str]:
    """(name, sector) of any symbol. A symbol outside the list gets its own symbol as name and OUTSIDE_SET100."""
    match = universe[universe["symbol"] == symbol]
    if match.empty:
        return symbol, OUTSIDE_SET100
    return str(match["name"].iloc[0]), str(match["sector"].iloc[0])


def is_valid_symbol(symbol: str) -> bool:
    """True for a plausible SET symbol (e.g. PTT, BH, SCB, KTB-R, NER.R). Anything else is rejected before it is
    shown or put into a link: symbols come from the URL and from typing, so they must not carry markdown or URLs."""
    return re.fullmatch(r"[A-Z0-9][A-Z0-9.&-]{0,14}", symbol) is not None


def yahoo_symbol(symbol: str) -> str:
    """SET symbol -> Yahoo Finance ticker, e.g. PTT -> PTT.BK."""
    return f"{symbol}.BK"


def set100_expiry_warning(today: date, period_end: date | None = None, lang: str = "en") -> str | None:
    """A warning to show users once the SET100 list is past its period (None while it is current).

    `period_end` defaults to SET100_PERIOD_END.
    """
    end = period_end or SET100_PERIOD_END
    if today <= end:
        return None
    return text("common.list_expired", lang, end=f"{end:%-d %b %Y}")
