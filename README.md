# SET50 Dashboard

[![CI](https://github.com/STeerajit/stock-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/STeerajit/stock-dashboard/actions/workflows/ci.yml)

Interactive dashboard for the 50 largest Thai stocks (SET50): a screener to compare all of them,
and a detail page per stock covering trading activity, chart, financials, valuation vs. peers,
dividends — plus an honestly-evaluated price prediction model.

## How to run

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # app + test tools (use requirements.txt for the app only)
streamlit run app.py
```

Dependencies are pinned to exact versions: `requirements.txt` holds what the app needs at runtime,
`requirements-dev.txt` adds the test tools.

Then open http://localhost:8501 in your browser. Share a stock directly with `http://localhost:8501/stock?symbol=PTT`.

Run all checks — tests (offline, including a data-leakage check) and the type checker.
CI runs this same script on every push and pull request:

```bash
scripts/check.sh
```

## What each part answers

| Section | Shows | Question it answers |
|---|---|---|
| Screener | All SET50: price, 52-week position, value traded, P/E (vs. sector), P/BV, yield, ROE, D/E | Which stocks deserve a closer look? |
| Trading | Price, volume vs. average, value traded, bid/offer, 52-week range, market cap | How much attention is the market paying? |
| Chart | Adjusted candlesticks, SMA20/50, support/resistance, volume, RSI | Where is the trend; where might price react? |
| Financials | Up to 16 years: revenue & profit growth, margins, ROE, D/E, free cash flow | Is the business good and strong? |
| Valuation | P/E, P/BV, yield vs. sector median; P/E and P/BV vs. their own 16-year median | Is the price expensive or cheap? |
| Dividends & calendar | Dividend per share by year, XD date, earnings date | What events may move the price? |
| Prediction | Random Forest next-day direction, time-based split, baseline & backtest | Can a simple model beat guessing? (Usually not.) |

## Data sources and limits

- **Prices, trading snapshot, current valuation, dividends:** Yahoo Finance via `yfinance` — delayed ~15 min.
- **Financial history (2010 onward) and yearly P/E, P/BV:** [`thaifin`](https://pypi.org/project/thaifin/).
  Falls back to Yahoo (~4 years) if thaifin is unavailable; the app shows which source was used.
  - thaifin's D/E is *total liabilities* / equity; Yahoo's is *interest-bearing debt* / equity.
  - thaifin's yearly dividend yield is not used: its units are inconsistent across years.
  - Recently listed stocks (e.g. MRDIYT) have only 1–2 years of history.
- **SET50 list:** `data/set50.csv`, for 1 Jul – 31 Dec 2026. Built from SET's official H1/2026 constituent list
  with the H2/2026 changes (+BCP, MRDIYT, TFG, THAI; −BTS, CBG, CENTEL, SAWAD) as reported by Kaohoon.
  SET reviews the index every 6 months — update the CSV in January and July.
- **Not included yet** (no free official API): investor-type flows, NVDR, short sales, top-10 shareholders,
  Form 59, C-sign / cash balance / turnover list, SET news.

## Project structure

```
app.py                         # entry point + navigation
app_pages/screener.py          # SET50 table
app_pages/stock.py             # one-stock detail page (6 tabs)
src/__init__.py
src/universe.py                # SET50 list + official SET sector names
src/data.py                    # daily prices
src/fundamentals.py            # snapshot, financials, dividends, P/E history, sector medians
src/indicators.py              # SMA, RSI, volatility, support/resistance
src/charts.py                  # Plotly price chart
src/model.py                   # prediction model + backtest
src/screener.py                # screener helpers (selected row -> symbol)
src/cache.py                   # Streamlit caching of all loaders
data/set50.csv                 # SET50 constituents
scripts/check.sh               # all checks (pytest + ty); CI runs the same script
.github/workflows/ci.yml       # GitHub Actions CI
tests/conftest.py              # blocks network access; fake Yahoo fixture
tests/fakes.py                 # offline fakes for yfinance
tests/test_model.py            # features, target, leakage, backtest split
tests/test_fundamentals.py     # S/R levels, P/E history, sector medians, thaifin fallback
tests/test_normalization.py    # unit conversions from thaifin and Yahoo
tests/test_outage.py           # behaviour when Yahoo is down
tests/test_pages.py            # AppTest smoke tests for both pages
tests/test_navigation.py       # screener row -> stock page
tests/test_universe.py         # SET50 CSV format
tests/test_requirements.py     # pinned dependencies
tests/test_ci.py               # CI workflow and check script
tests/test_docs.py             # README and in-app text stay in sync with the code
```

## Results of the prediction model (honest)

On the stocks tested, test accuracy is about the same as a naive baseline — no real edge.
That is the expected result for daily price direction, and the app reports it rather than hiding it.

> For learning only — not investment advice.
