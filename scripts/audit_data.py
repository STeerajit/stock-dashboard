"""Check the stored data for figures that look wrong and print a Markdown report. Nothing is changed or downloaded.

Run from the repo (after scripts/update_data.py):
    .venv/bin/python scripts/audit_data.py                 # report + 5 random stocks to check on SET's website
    .venv/bin/python scripts/audit_data.py --sample 10     # 10 stocks in the hand-check list
    .venv/bin/python scripts/audit_data.py > audit.md      # save the report
"""

import argparse
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import audit, store  # noqa: E402
from src.set_links import QUOTE  # noqa: E402
from src.universe import load_set100  # noqa: E402


def load(path: Path = store.STORE_PATH) -> dict[str, audit.Stock]:
    symbols = [s for s in load_set100()["symbol"] if store.has(path, s)]
    snaps = store.load_snapshots(path, symbols).set_index("symbol")
    return {s: audit.Stock(store.load_prices(path, s), store.load_close(path, s), store.load_dividends(path, s),
                           store.load_financials(path, s), store.load_quarterly(path, s), snaps.at[s, "ex_div_date"])
            for s in symbols}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", type=int, default=5, help="stocks in the hand-check list (default 5)")
    parser.add_argument("--seed", type=int, default=None, help="pick the same stocks again (default: random)")
    args = parser.parse_args()
    if not store.STORE_PATH.exists():
        print("No data store yet: run scripts/update_data.py first.", file=sys.stderr)
        return 1
    stocks = load()
    today = date.today()
    print(f"# Data check, {today:%Y-%m-%d} (store updated {store.as_of(store.STORE_PATH):%Y-%m-%d %H:%M})\n")
    print(audit.report(audit.audit(stocks, today), len(stocks)))
    picked = sorted(random.Random(args.seed).sample(sorted(stocks), min(args.sample, len(stocks))))
    print("# Check by hand on SET's website\n")
    print("Open each SET page (Factsheet) and compare. Not stored by SET this way: the app's figures may differ "
          "slightly because of rounding or the date used.\n")
    print(audit.checklist(stocks, picked, lambda s: QUOTE.format(symbol=s, page="factsheet")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
