"""Backtest results for Dividend Picks, as saved by scripts/report_dividend_picks.py.

The results file is committed, so the app (and the public demo) can say whether each rule beat the plain picks
without re-running a 10-year backtest on every visit.
"""

import json
from pathlib import Path

RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "dividend_picks_backtest.json"


def load_results(path: Path = RESULTS_PATH) -> dict | None:
    """The saved results, or None if the backtest has not been run yet (or the file is unreadable)."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def rule_passed(results: dict | None, rule: str) -> bool:
    """True only when the saved backtest shows `rule` beat the plain picks after costs."""
    return bool(results and results.get("rules", {}).get(rule, {}).get("passed"))
