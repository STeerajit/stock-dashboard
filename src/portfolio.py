"""The user's holdings: symbol, shares, average cost. `shares = 0` means the stock is only on the watchlist.

Saved to data/portfolio.csv, which is gitignored: real holdings must never be committed.
"""

from pathlib import Path

import pandas as pd

PORTFOLIO_CSV = Path(__file__).resolve().parent.parent / "data" / "portfolio.csv"
COLUMNS = ["symbol", "shares", "avg_cost"]


def empty() -> pd.DataFrame:
    return pd.DataFrame({"symbol": pd.Series(dtype=str), "shares": pd.Series(dtype=float),
                         "avg_cost": pd.Series(dtype=float)})


def load(path: Path | None = None) -> pd.DataFrame:
    """The saved holdings (columns: COLUMNS), or an empty table if nothing is saved yet."""
    path = path or PORTFOLIO_CSV
    if not path.exists():
        return empty()
    return pd.read_csv(path, dtype={"symbol": str, "shares": float, "avg_cost": float})[COLUMNS]


def clean(table: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Check an edited table. Returns (holdings ready to save, problems to show the user).

    Symbols are trimmed and upper-cased; fully blank rows (e.g. a row added but never filled) are dropped.
    Only save when the list of problems is empty.
    """
    df = table[COLUMNS].copy()
    df["symbol"] = df["symbol"].fillna("").astype(str).str.strip().str.upper()
    df = df[(df["symbol"] != "") | df["shares"].notna() | df["avg_cost"].notna()].reset_index(drop=True)

    problems = []
    for n, (symbol, shares, avg_cost) in enumerate(df.itertuples(index=False), start=1):
        if symbol == "":
            problems.append(f"Row {n}: the symbol is empty.")
        if pd.isna(shares):
            problems.append(f"Row {n}: shares is empty (use 0 for a watchlist stock).")
        elif shares < 0:
            problems.append(f"Row {n}: shares can't be negative.")
        if pd.notna(avg_cost) and avg_cost < 0:
            problems.append(f"Row {n}: average cost can't be negative.")
        elif pd.isna(avg_cost) and pd.notna(shares) and shares > 0:
            problems.append(f"Row {n}: average cost is empty.")
    dupes = sorted(set(df.loc[df["symbol"].duplicated() & (df["symbol"] != ""), "symbol"]))
    if dupes:
        problems.append(f"Each stock can appear only once: {', '.join(dupes)}.")
    return df, problems


def save(holdings: pd.DataFrame, path: Path | None = None) -> None:
    """Write holdings that passed `clean` with no problems."""
    path = path or PORTFOLIO_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    holdings[COLUMNS].to_csv(path, index=False)
