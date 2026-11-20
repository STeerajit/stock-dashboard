"""The user's holdings: symbol, shares, average cost. `shares = 0` means the stock is only on the watchlist.

Saved to data/portfolio.csv, which is gitignored: real holdings must never be committed.
"""

from pathlib import Path

import pandas as pd

from src.i18n import text
from src.universe import is_valid_symbol

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


def clean(table: pd.DataFrame, lang: str = "en") -> tuple[pd.DataFrame, list[str]]:
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
            problems.append(text("problem.empty_symbol", lang, n=n))
        elif not is_valid_symbol(symbol):
            problems.append(text("problem.bad_symbol", lang, n=n, symbol=symbol[:20]))
        if pd.isna(shares):
            problems.append(text("problem.empty_shares", lang, n=n))
        elif shares < 0:
            problems.append(text("problem.negative_shares", lang, n=n))
        if pd.notna(avg_cost) and avg_cost < 0:
            problems.append(text("problem.negative_cost", lang, n=n))
        elif pd.isna(avg_cost) and pd.notna(shares) and shares > 0:
            problems.append(text("problem.empty_cost", lang, n=n))
    dupes = sorted(set(df.loc[df["symbol"].duplicated() & (df["symbol"] != ""), "symbol"]))
    if dupes:
        problems.append(text("problem.duplicates", lang, symbols=", ".join(dupes)))
    return df, problems


def save(holdings: pd.DataFrame, path: Path | None = None) -> None:
    """Write holdings that passed `clean` with no problems."""
    path = path or PORTFOLIO_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    holdings[COLUMNS].to_csv(path, index=False)


def last_full_year_dps(dividends_per_year: pd.Series, this_year: int) -> float:
    """Dividend per share of the last complete calendar year (this_year - 1); NaN if none was paid."""
    return float(dividends_per_year.get(this_year - 1, float("nan")))


def positions(holdings: pd.DataFrame, quotes: pd.DataFrame) -> pd.DataFrame:
    """Per-stock numbers. `quotes` has symbol, price, dps (last complete year) and sector for every holding.

    Adds cost, value, pnl, pnl_pct, est_dividend (dps × shares; no dividend = 0), yield_on_cost (dps / avg cost).
    Watchlist rows (0 shares) keep their price but get NaN for all of these. No fees or taxes.
    """
    df = holdings[COLUMNS].merge(quotes[["symbol", "price", "dps", "sector"]], on="symbol", how="left")
    held = df["shares"] > 0
    dps = df["dps"].fillna(0)
    df["cost"] = (df["shares"] * df["avg_cost"]).where(held)
    df["value"] = (df["shares"] * df["price"]).where(held)
    df["pnl"] = df["value"] - df["cost"]
    df["pnl_pct"] = df["pnl"] / df["cost"].where(df["cost"] > 0)
    df["est_dividend"] = (df["shares"] * dps).where(held)
    df["yield_on_cost"] = (dps / df["avg_cost"].where(df["avg_cost"] > 0)).where(held)
    return df


def totals(pos: pd.DataFrame) -> dict[str, float]:
    """Portfolio totals over the held stocks that have a price (a stock without one is left out of every total)."""
    priced = pos[pos["value"].notna()]
    cost, value, dividend = priced["cost"].sum(), priced["value"].sum(), priced["est_dividend"].sum()
    return {
        "cost": cost,
        "value": value,
        "pnl": value - cost,
        "pnl_pct": (value - cost) / cost if cost else float("nan"),
        "est_dividend": dividend,
        "yield_on_cost": dividend / cost if cost else float("nan"),
    }


def allocation(pos: pd.DataFrame) -> pd.Series:
    """Share of the portfolio's market value per sector (sums to 1), largest first."""
    by_sector = pos.groupby("sector")["value"].sum(min_count=1).dropna()
    return (by_sector / by_sector.sum()).sort_values(ascending=False)
