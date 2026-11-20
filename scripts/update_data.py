"""Download today's data for every SET100 stock into data/market.duckdb.

Run from the repo:  .venv/bin/python scripts/update_data.py
Exits 1 (and leaves the store unchanged) if more than 20% of the stocks fail or a price looks wrong.
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import store  # noqa: E402
from src.universe import load_set100  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.ERROR)
    symbols = load_set100()["symbol"].tolist()
    started = time.time()
    try:
        report = store.update_store(store.STORE_PATH, symbols, store.live_fetchers())
    except store.UpdateError as e:
        print(f"Update failed: {e}", file=sys.stderr)
        return 1
    print(f"Updated {len(report.updated)} stocks in {time.time() - started:.0f} s -> {store.STORE_PATH}")
    if report.failed:
        print(f"Skipped (download failed, old data kept): {', '.join(report.failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
