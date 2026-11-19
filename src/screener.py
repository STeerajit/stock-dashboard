"""Pure helpers for the screener page (kept out of the page so they can be unit-tested)."""

import pandas as pd


def selected_symbol(shown: pd.DataFrame, rows: list[int]) -> str | None:
    """Symbol of the selected row. `rows` are positions in `shown`, the table exactly as displayed
    (after the sector filter and sorting) — not positions in the full SET50 list."""
    if not rows:
        return None
    return str(shown.iloc[rows[0]]["symbol"])
