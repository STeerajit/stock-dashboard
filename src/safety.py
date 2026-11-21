"""Dividend safety grade: is this dividend likely to keep coming, or is the yield a trap? (backlog #23)

Six checks, each "good", "ok", "bad", "unknown" (data missing: never counted as bad) or "skipped":

| Check | good | ok | bad | Source of the thresholds |
|---|---|---|---|---|
| EPS payout (TTM, as in Dividend picks) | <= 60% | <= 100% | > 100%, or a loss | 100%: SETHD rule 3; 60%: the top of the 40-60% the same paper recommends (Nikornpittaya & Wongpriew 2024, see docs/research/dividend-picks.md). Morningstar's 20-year study: high payout predicts cuts. |
| FCF payout = DPS x Shares / FCF | not bad | - | FCF <= 0 or payout > 100% in 2 of the last 3 years (2 known) | Set by the owner (2026-11-22): thaifin's FCF includes acquisitions, so one bad year is not enough. |
| Years since the last cut | >= 5 or none | 2-4 | 0-1 (a cut in the last 2 complete years) | Set by us; cuts are bad news (Michaely, Thaler & Womack 1995, not checked). |
| Years paid in a row | >= 10 | 3-9 | < 3 | 3: SETHD's "paid for 3 years"; 10: set by us (like the 10 years of Dividend Achiever lists). |
| 5-year DPS growth (CAGR) | >= 2% | 0-2% | < 0 | 2%: the middle of the Bank of Thailand's 1-3% inflation target (keeps up with prices). |
| Special dividend last year | no | yes | - | A year over 1.5x the median of the other years that paid (last 10): set by the owner. |

FCF payout is skipped for banks, finance and insurance: their cash flow mixes in lending and deposits.
Special years still count as paid in the streak, but are left out of the growth rate and of cut detection.

Level (set by us): fewer than 3 known checks -> "not_enough_data"; 2+ bad -> "unsafe"; 1 bad -> "risky";
2+ ok -> "ok"; else "safe". Years are calendar years by XD date; the current year is left out until it ends.
"""

from typing import Literal, NamedTuple, cast

import pandas as pd

from src import dividend_picks as dp
from src.fundamentals import cagr
from src.i18n import text

LEVELS = ("safe", "ok", "risky", "unsafe")
NOT_ENOUGH_DATA = "not_enough_data"
FINANCIAL_SECTORS = {"Banking", "Finance & Securities", "Insurance"}

PAYOUT_GOOD = 0.60
PAYOUT_MAX = dp.MAX_PAYOUT  # 100%
FCF_YEARS, FCF_BAD_YEARS, FCF_MIN_KNOWN = 3, 2, 2
CUT_BAD_YEARS, CUT_GOOD_YEARS = 2, 5
STREAK_OK, STREAK_GOOD = 3, 10
CAGR_YEARS, CAGR_GOOD = 5, 0.02
SPECIAL_FACTOR, HISTORY_YEARS = 1.5, 10
MIN_KNOWN = 3

Status = Literal["good", "ok", "bad", "unknown", "skipped"]
# The reason text of a check is "safety.{key}.{variant}"; every variant each check can give (for the i18n test).
REASONS = {
    "eps_payout": ("good", "ok", "bad", "loss", "no_dividend", "unknown"),
    "fcf_payout": ("good", "bad", "unknown", "skipped"),
    "cut": ("good", "none", "ok", "bad", "unknown"),
    "streak": ("good", "ok", "bad", "unknown"),
    "cagr": ("good", "ok", "bad", "unknown"),
    "special": ("good", "ok", "unknown"),
}
BADGE_COLORS = {"safe": "green", "ok": "blue", "risky": "orange", "unsafe": "red", NOT_ENOUGH_DATA: "gray"}
STATUS_ICONS = {"good": ":green[:material/check_circle:]", "ok": ":blue[:material/info:]",
                "bad": ":red[:material/warning:]", "unknown": ":gray[:material/help:]",
                "skipped": ":gray[:material/remove_circle:]"}


class Check(NamedTuple):
    key: str
    status: Status
    reason: str


class Grade(NamedTuple):
    level: str  # one of LEVELS, or NOT_ENOUGH_DATA
    checks: list[Check]


def per_year(dividends: pd.Series, as_of) -> pd.Series:
    """Dividend per share per complete calendar year (by XD date), from the first year with one to last year.
    A year without a dividend is 0. Empty without any dividend before this year."""
    as_of = pd.Timestamp(as_of)
    d = dividends[dividends.index <= as_of]
    by_year = d.groupby(pd.DatetimeIndex(d.index).year).sum()
    by_year = by_year[by_year.index < as_of.year]
    if by_year.empty:
        return pd.Series(dtype=float)
    return by_year.reindex(range(int(by_year.index.min()), as_of.year), fill_value=0.0).astype(float)


def special_years(per_year: pd.Series, factor: float = SPECIAL_FACTOR) -> set[int]:
    """Years (of the last 10) whose dividend is more than `factor` × the median of the other years that paid one
    (years without a dividend are left out, or a stock that skipped a few years would look special on return)."""
    window = per_year.tail(HISTORY_YEARS)
    out = set()
    for year, dps in window.items():
        others = window.drop(year)
        others = others[others > 0]
        if len(others) >= 2 and others.median() > 0 and dps > factor * others.median():
            out.add(int(cast(int, year)))
    return out


def _regular(per_year: pd.Series) -> pd.Series:
    return per_year.drop(list(special_years(per_year)))


def years_since_cut(per_year: pd.Series) -> float:
    """Complete years since the last cut in the last 10 years (0 = last year was lower than the year before),
    inf without a cut, NaN with fewer than 2 years. Special years are removed first."""
    s = _regular(per_year.tail(HISTORY_YEARS))
    if len(s) < 2:
        return float("nan")
    cuts = s.index[1:][s.to_numpy()[1:] < s.to_numpy()[:-1]]
    return float(per_year.index[-1] - cuts[-1]) if len(cuts) else float("inf")


def paid_streak(per_year: pd.Series) -> int:
    """Complete years in a row, up to last year, with a dividend (special years count as paid)."""
    n = 0
    for dps in reversed(per_year.to_numpy()):
        if dps <= 0:
            break
        n += 1
    return n


def payout_status(payout: float) -> Status:
    return "good" if payout <= PAYOUT_GOOD else "ok" if payout <= PAYOUT_MAX else "bad"


def cut_status(years: float) -> Status:
    return "bad" if years < CUT_BAD_YEARS else "ok" if years < CUT_GOOD_YEARS else "good"


def streak_status(years: int) -> Status:
    return "bad" if years < STREAK_OK else "ok" if years < STREAK_GOOD else "good"


def cagr_status(growth: float) -> Status:
    return "bad" if growth < 0 else "ok" if growth < CAGR_GOOD else "good"


def _fcf_payout(fin: pd.DataFrame, dps: pd.Series) -> tuple[int, int]:
    """(known years, bad years) among the last 3 published years."""
    if "Free cash flow" not in fin or "Shares" not in fin:
        return 0, 0
    known = bad = 0
    for year, row in fin.tail(FCF_YEARS).iterrows():
        fcf, shares = row["Free cash flow"], row["Shares"]
        if pd.isna(fcf) or pd.isna(shares):
            continue
        known += 1
        bad += bool(fcf <= 0 or float(dps.get(year, 0.0)) * shares / fcf > 1)
    return known, bad


def grade(d: dp.StockData, sector: str, as_of, lang: str = "en") -> Grade:
    """The safety grade of one stock's dividend on `as_of`, with one translated reason per check."""
    as_of = pd.Timestamp(as_of)
    checks: list[Check] = []

    def put(key: str, status: Status, variant: str | None = None, **values) -> None:
        checks.append(Check(key, status, text(f"safety.{key}.{variant or status}", lang, **values)))

    dps, eps, payout = dp.ttm_payout(d, as_of)
    if pd.isna(eps):
        put("eps_payout", "unknown")
    elif dps <= 0:
        put("eps_payout", "unknown", "no_dividend")
    elif eps <= 0:
        put("eps_payout", "bad", "loss", eps=eps)
    else:
        put("eps_payout", payout_status(payout), payout=payout)

    years = per_year(d.dividends, as_of)
    if sector in FINANCIAL_SECTORS:
        put("fcf_payout", "skipped")
    else:
        known, bad = _fcf_payout(dp.published_financials(d.financials, as_of), years)
        if known < FCF_MIN_KNOWN:
            put("fcf_payout", "unknown")
        else:
            put("fcf_payout", "bad" if bad >= FCF_BAD_YEARS else "good", bad=bad, known=known)

    since = years_since_cut(years)
    if pd.isna(since):
        put("cut", "unknown")
    elif since == float("inf"):
        put("cut", "good", "none", years=len(years.tail(HISTORY_YEARS)))
    else:
        put("cut", cut_status(since), year=int(years.index[-1] - since))

    if years.empty:
        put("streak", "unknown")
    else:
        streak = paid_streak(years)
        put("streak", streak_status(streak), years=streak)

    growth = cagr(_regular(years), CAGR_YEARS)
    if pd.isna(growth):
        put("cagr", "unknown")
    else:
        put("cagr", cagr_status(growth), growth=growth)

    if len(years.tail(HISTORY_YEARS)) < 3:
        put("special", "unknown")
    elif int(years.index[-1]) in special_years(years):
        put("special", "ok", dps=float(years.iloc[-1]), year=int(years.index[-1]))
    else:
        put("special", "good")

    statuses = [c.status for c in checks]
    if sum(s in ("good", "ok", "bad") for s in statuses) < MIN_KNOWN:
        level = NOT_ENOUGH_DATA
    elif statuses.count("bad") >= 2:
        level = "unsafe"
    elif statuses.count("bad") == 1:
        level = "risky"
    elif statuses.count("ok") >= 2:
        level = "ok"
    else:
        level = "safe"
    return Grade(level, checks)


def badge(level: str, lang: str = "en") -> str:
    """The level as a coloured Streamlit markdown badge."""
    return f":{BADGE_COLORS[level]}-badge[{text(f'safety.level.{level}', lang)}]"


def reason_lines(g: Grade) -> list[str]:
    """One markdown line per check: its status icon and reason."""
    return [f"{STATUS_ICONS[c.status]} {c.reason}" for c in g.checks]
