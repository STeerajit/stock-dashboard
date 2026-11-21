"""Run the 10-year Dividend Picks backtest, save the results the app reads, and print them as a Markdown table.

Uses the local store (run scripts/update_data.py first), so the numbers are reproducible for the dates printed.

    .venv/bin/python scripts/report_dividend_picks.py            # writes data/dividend_picks_backtest.json
    .venv/bin/python scripts/report_dividend_picks.py --no-save  # print only
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import dividend_picks as dp  # noqa: E402
from src import picks_backtest as bt  # noqa: E402
from src import store  # noqa: E402
from src.universe import load_set100  # noqa: E402


def load(path: Path = store.STORE_PATH) -> dict[str, dp.StockData]:
    return {s: dp.StockData(store.load_prices(path, s), store.load_close(path, s), store.load_dividends(path, s),
                            store.load_financials(path, s))
            for s in load_set100()["symbol"] if store.has(path, s)}


def table(results: dict) -> str:
    base = results["base"]
    lines = ["| Strategy | Return a year | Volatility a year | Worst drawdown | Turnover a year | Beat the picks |",
             "|---|---|---|---|---|---|"]

    def line(name, r, passed=""):
        lines.append(f"| {name} | {r['cagr']:+.1%} | {r['volatility']:.1%} | {r['max_drawdown']:.1%} "
                     f"| {r['turnover']:.0%} | {passed} |")

    line("SET100 equal weight (benchmark)", results["benchmark"])
    line("10 dividend picks (base)", base)
    for name, r in results["rules"].items():
        line(name, r, "yes" if r["passed"] else "no")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-save", action="store_true", help="print the table without writing the results file")
    args = parser.parse_args()

    data = load()
    if not data:
        sys.exit("No local store: run scripts/update_data.py first.")
    last = max(d.close.index[-1] for d in data.values())
    dates = bt.month_ends(last)
    started = time.monotonic()
    results = {"data_as_of": f"{last:%Y-%m-%d}", **bt.run(data, dates)}
    print(f"Data as of {results['data_as_of']}; {results['stocks']} stocks; month ends {results['start']} to "
          f"{results['end']} ({results['months']} months); {bt.COST_PER_TRADE:.2%} per buy or sell; "
          f"ran in {time.monotonic() - started:.0f} s.\n")
    print(table(results))
    if not args.no_save:
        bt.RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nSaved {bt.RESULTS_PATH.relative_to(Path.cwd()) if bt.RESULTS_PATH.is_relative_to(Path.cwd()) else bt.RESULTS_PATH}")


if __name__ == "__main__":
    main()
