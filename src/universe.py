"""The list of stocks the app covers: SET50 constituents.

SET reviews the index every 6 months (effective 1 Jan and 1 Jul), so the list
lives in a CSV that is easy to update, not in code.
"""

from pathlib import Path

import pandas as pd

SET50_CSV = Path(__file__).resolve().parent.parent / "data" / "set50.csv"
SET50_PERIOD = "1 Jul – 31 Dec 2026"

# Sector names exactly as SET prints them in its index-constituent documents.
SET_SECTORS = frozenset({
    "Agribusiness", "Banking", "Commerce", "Construction Materials", "Construction Services",
    "Electronic Components", "Energy & Utilities", "Fashion", "Finance & Securities", "Food & Beverage",
    "Health Care Services", "Information & Communication Technology", "Insurance", "Media & Publishing",
    "Packaging", "Personal Products & Pharmaceuticals", "Petrochemicals & Chemicals", "Professional Services",
    "Property Development", "Tourism & Leisure", "Transportation & Logistics",
})


def load_set50() -> pd.DataFrame:
    """Columns: symbol, name, sector (sector names as used by SET)."""
    return pd.read_csv(SET50_CSV)


def yahoo_symbol(symbol: str) -> str:
    """SET symbol -> Yahoo Finance ticker, e.g. PTT -> PTT.BK."""
    return f"{symbol}.BK"
