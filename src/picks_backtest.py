"""Backtest for Dividend Picks (docs/research/dividend-picks.md, section 7), and its saved results.

Every month end the screen is run with only the data known then; the portfolio holds the picks equally weighted
(1/10 each; a slot with nothing to hold is cash at 0%) until the next month end. Returns come from
dividend-adjusted closes, so dividends are included. Each change of weight costs 0.17% (one buy or sell).

The plain picks are the base. Each rule is a variant of it:
- a buy rule lets a new pick in only when its signal is on (stocks already held are kept while they stay picks);
- "rank_out" keeps a held stock until its rank falls below 20, filling free slots with the best new picks;
- "below_trend" holds the picks minus those below their 10-month average.
A rule passes when its yearly return after costs beats the plain picks' by at least MIN_MARGIN (0.5 percentage
points, set by the project owner on 2026-11-22: a smaller lead can flip with a small change in the data).

The results file is committed, so the app (and the public demo) can say whether each rule beat the plain picks
without re-running a 10-year backtest on every visit.
"""

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from src import dividend_picks as dp
from src import signals as sg

RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "dividend_picks_backtest.json"
COST_PER_TRADE = 0.0017  # Thai online broker commission + VAT, per buy or per sell (as in docs/article.md)
YEARS = 10
MIN_MARGIN = 0.005  # a rule must beat the plain picks by 0.5 percentage points a year (owner-set)
BUY_RULES = ("trend", "market_trend", "rsi_low", "macd", "obv", "near_support", "pullback", "dividend_month")


def load_results(path: Path = RESULTS_PATH) -> dict | None:
    """The saved results, or None if the backtest has not been run yet (or the file is unreadable)."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def rule_passed(results: dict | None, rule: str) -> bool:
    """True only when the saved backtest shows `rule` beat the plain picks after costs."""
    return bool(results and results.get("rules", {}).get(rule, {}).get("passed"))


def month_ends(last_day: pd.Timestamp, years: int = YEARS) -> list[pd.Timestamp]:
    """Calendar month ends from `years` before the last complete month up to it (years * 12 + 1 dates)."""
    last = (pd.Timestamp(last_day) + pd.offsets.MonthEnd(0)).normalize()
    if last > pd.Timestamp(last_day):  # the month of last_day is not complete yet
        last = (last - pd.offsets.MonthEnd(1)).normalize()
    return list(pd.date_range(end=last, periods=years * 12 + 1, freq="ME"))


def _close_on(d: dp.StockData, day: pd.Timestamp) -> float:
    c = d.prices["Close"]
    before = c[c.index <= day]
    return float(before.iloc[-1]) if len(before) and before.index[-1] > day - pd.Timedelta(days=10) else float("nan")


def stats(returns: pd.Series, turnover: pd.Series) -> dict:
    """Yearly return (CAGR), yearly volatility, worst drawdown and yearly turnover of monthly returns."""
    growth = (1 + returns).cumprod()
    years = len(returns) / 12
    return {
        "cagr": float(growth.iloc[-1] ** (1 / years) - 1),
        "volatility": float(returns.std() * np.sqrt(12)),
        "max_drawdown": float((growth / growth.cummax().clip(lower=1) - 1).min()),
        "turnover": float(turnover.sum() / years),
    }


def simulate(dates: list[pd.Timestamp], data: dict[str, dp.StockData],
             choose: Callable[[pd.Timestamp, list[str]], list[str]], slots: int | None = dp.PICKS,
             cost: float = COST_PER_TRADE) -> tuple[pd.Series, pd.Series]:
    """Monthly returns after costs and turnover of holding `choose(date, held)` from each date to the next.

    Each held stock weighs 1/slots (cash fills the rest); slots=None weighs every chosen stock equally.
    Turnover = sum of |new weight − weight after last month's price moves|; cost = turnover × cost.
    """
    held: list[str] = []
    drifted: dict[str, float] = {}
    rets, turns = [], []
    for start, end in zip(dates[:-1], dates[1:]):
        held = choose(start, held)
        size = slots or max(len(held), 1)
        weights = {s: 1 / size for s in held}
        turnover = sum(abs(weights.get(s, 0.0) - drifted.get(s, 0.0)) for s in set(weights) | set(drifted))
        moves = {s: _close_on(data[s], end) / _close_on(data[s], start) - 1 for s in held}
        moves = {s: (0.0 if np.isnan(m) else m) for s, m in moves.items()}  # no price (suspended): flat
        gross = sum(weights[s] * moves[s] for s in held)
        total = 1 + gross
        drifted = {s: weights[s] * (1 + moves[s]) / total for s in held} if total > 0 else {}
        rets.append(gross - turnover * cost)
        turns.append(turnover)
    index = pd.DatetimeIndex(dates[1:])
    return pd.Series(rets, index=index), pd.Series(turns, index=index)


def run(data: dict[str, dp.StockData], dates: list[pd.Timestamp]) -> dict:
    """Base, benchmark and every rule over `dates` (month ends). Returns the results dict that is saved."""
    market = dp.equal_weight_index(data)
    screens = {day: dp.screen(data, day).set_index("symbol") for day in dates[:-1]}
    cache: dict[tuple, dict] = {}

    def sig(day, symbol) -> dict[str, sg.Signal]:
        if (day, symbol) not in cache:
            row = screens[day].loc[symbol]
            cache[(day, symbol)] = sg.compute(data[symbol], day, rank=row["rank"], stage=str(row["stage"]),
                                              market_close=market)
        return cache[(day, symbol)]

    def top(day, n=dp.PICKS):
        return dp.picks(screens[day].reset_index(), n)

    def gated(test: Callable[[pd.Timestamp, str], bool]):
        def choose(day, held):
            return [s for s in top(day) if s in held or test(day, s)]
        return choose

    def buffered(day, held):
        ranks = screens[day]["rank"]
        keep = [s for s in held if not pd.isna(ranks.get(s)) and ranks[s] <= sg.SELL_RANK]
        return keep + [s for s in top(day, len(screens[day])) if s not in keep][:dp.PICKS - len(keep)]

    def trend_ok(day, s):
        return sig(day, s)["trend"].on

    variants: dict[str, Callable] = {"base": lambda day, held: top(day)}
    for rule in BUY_RULES:
        variants[rule] = gated(lambda day, s, rule=rule: sig(day, s)[rule].on)
    variants["rank_out"] = buffered
    variants["below_trend"] = lambda day, held: [s for s in top(day) if trend_ok(day, s)]
    variants["buy_now"] = gated(lambda day, s: sg.buy_now(sig(day, s), screens[day].at[s, "rank"]))
    variants["sell_now"] = lambda day, held: [s for s in buffered(day, held) if trend_ok(day, s)]

    out = {name: stats(*simulate(dates, data, choose)) for name, choose in variants.items()}
    everyone = lambda day, held: [s for s, d in data.items() if not np.isnan(_close_on(d, day))]  # noqa: E731
    benchmark = stats(*simulate(dates, data, everyone, slots=None))
    base = out.pop("base")
    return {
        "start": f"{dates[0]:%Y-%m}", "end": f"{dates[-1]:%Y-%m}", "months": len(dates) - 1,
        "cost_per_trade": COST_PER_TRADE, "stocks": len(data),
        "base": base, "benchmark": benchmark,
        "rules": {name: {**r, "passed": r["cagr"] >= base["cagr"] + MIN_MARGIN} for name, r in out.items()},
    }
