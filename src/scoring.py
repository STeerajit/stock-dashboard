"""Well-known stock scores: Piotroski F-score and Joel Greenblatt's Magic Formula rank.

Uses only free yearly data, so some checks can be unavailable; scores are shown as "points / available".
"""

from typing import NamedTuple

import pandas as pd


class FScore(NamedTuple):
    points: int
    available: int
    checks: dict[str, bool | None]  # None = no data for this check


def piotroski(financials: pd.DataFrame) -> FScore:
    """The 9 Piotroski checks on the last year vs. the year before. A check without data counts as unavailable."""
    if financials.empty:
        return FScore(0, 0, {})
    now = financials.iloc[-1]
    before = financials.iloc[-2] if len(financials) > 1 else pd.Series(dtype=float)

    def get(row: pd.Series, col: str) -> float:
        return float(row.get(col, float("nan")))

    def check(a: float, b: float, test) -> bool | None:
        return None if pd.isna(a) or pd.isna(b) else bool(test(a, b))

    def ratio(row: pd.Series, top: str, bottom: str) -> float:
        b = get(row, bottom)
        return get(row, top) / b if b else float("nan")

    checks: dict[str, bool | None] = {
        # Profitability
        "Positive ROA": check(get(now, "ROA"), 0, lambda a, b: a > b),
        "Positive operating cash flow": check(get(now, "Operating cash flow"), 0, lambda a, b: a > b),
        "ROA improved": check(get(now, "ROA"), get(before, "ROA"), lambda a, b: a > b),
        "Cash flow above profit": check(get(now, "Operating cash flow"), get(now, "Net income"), lambda a, b: a > b),
        # Leverage and liquidity
        "Lower debt / assets": check(ratio(now, "Total debt", "Total assets"),
                                     ratio(before, "Total debt", "Total assets"), lambda a, b: a < b),
        "Higher current ratio": None,  # no free current-asset / current-liability data
        # Share count from market cap / price is approximate, so allow 1% before calling it new shares.
        "No new shares": check(get(now, "Shares"), get(before, "Shares"), lambda a, b: a <= b * 1.01),
        # Efficiency
        "Higher gross margin": check(get(now, "Gross margin"), get(before, "Gross margin"), lambda a, b: a > b),
        "Higher asset turnover": check(ratio(now, "Revenue", "Total assets"),
                                       ratio(before, "Revenue", "Total assets"), lambda a, b: a > b),
    }
    known = [v for v in checks.values() if v is not None]
    return FScore(sum(known), len(known), checks)


def magic_formula_rank(df: pd.DataFrame) -> pd.Series:
    """Rank (1 = best) by earnings yield (1 / P/E) plus ROE, each ranked across the stocks given.

    ROE stands in for Greenblatt's return on capital (no free data for it). Stocks with a loss (P/E <= 0) or
    missing figures get NaN.
    """
    ok = (df["pe"] > 0) & df["roe"].notna()
    ey_rank = (1 / df.loc[ok, "pe"]).rank(ascending=False, method="min")
    roe_rank = df.loc[ok, "roe"].rank(ascending=False, method="min")
    return (ey_rank + roe_rank).rank(method="min").reindex(df.index)
