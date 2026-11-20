# SET100 Dashboard

[![CI](https://github.com/STeerajit/stock-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/STeerajit/stock-dashboard/actions/workflows/ci.yml)

Personal dashboard for Thai stocks: a Today page that lists which of your stocks deserve a look and why, a screener to compare the 100 largest (SET100), a detail page for
any Thai stock covering trading activity, chart, financials, valuation vs. peers and dividends, and a
portfolio page to track your holdings and watchlist — plus an honestly-evaluated price prediction model.

What it is for, the decisions behind it and the status of each part: [docs/SPEC.md](docs/SPEC.md).

## How to run

One-time setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # app + test tools (use requirements.txt for the app only)
```

Dependencies are pinned to exact versions: `requirements.txt` holds what the app needs at runtime,
`requirements-dev.txt` adds the test tools.

Every day, start the app in the background and open it in the browser (macOS):

```bash
scripts/stocks.sh        # starts it on http://localhost:8501 if needed, then opens the browser
scripts/stocks.sh stop   # stops it
```

It keeps running after you close the terminal; its output goes to `stocks.log`. Tip: add
`alias stocks='<path to repo>/scripts/stocks.sh'` to `~/.zshrc` to type just `stocks`.
To run it in the foreground instead: `.venv/bin/streamlit run app.py`.

Share a stock directly with `http://localhost:8501/stock?symbol=PTT` (any SET symbol works, e.g. `?symbol=MAJOR`).

Run all checks — tests (offline, including a data-leakage check) and the type checker.
CI runs this same script on every push and pull request:

```bash
scripts/check.sh
```

## What each part answers

| Section | Shows | Question it answers |
|---|---|---|
| Today (start page) | Your portfolio and watchlist stocks that are near support, broke resistance, have RSI < 30 or > 70, an XD or earnings date within 14 days, or a P/E > 20% below their own median | Which of my stocks should I look at today? |
| Screener | All SET100 (SET50 marked): price, 52-week position, value traded, P/E (vs. sector), P/BV, yield, ROE, D/E, 5-year revenue/profit CAGR and average ROE | Which stocks deserve a closer look? |
| Trading | Price, volume vs. average, value traded, bid/offer, 52-week range, market cap, free float (Yahoo estimate) | How much attention is the market paying? |
| Chart | Adjusted candlesticks, SMA20/50, support/resistance, volume, RSI | Where is the trend; where might price react? |
| Financials | Up to 16 years: revenue & profit growth, margins, ROE, D/E, free cash flow | Is the business good and strong? |
| Valuation | P/E, P/BV, yield vs. sector median; P/E, P/BV and dividend yield vs. their own history | Is the price expensive or cheap? |
| Dividends & calendar | Dividend per share by year, XD date, earnings date | What events may move the price? |
| Portfolio | Your holdings and watchlist: value, P&L, estimated dividend, yield on cost, allocation by sector | How is my money doing? |
| Fair value | Dividend discount model and discounted cash flow with your assumptions, 3×3 sensitivity tables, Piotroski F-score check by check | What could it be worth, and is the business improving? |
| Prediction | Random Forest next-day direction, time-based split, baseline & backtest | Can a simple model beat guessing? (Usually not.) |

## Data sources and limits

- **Prices, trading snapshot, current valuation, dividends:** Yahoo Finance via `yfinance` — delayed ~15 min.
- **Financial history (2010 onward) and yearly P/E, P/BV:** [`thaifin`](https://pypi.org/project/thaifin/).
  Falls back to Yahoo (~4 years) if thaifin is unavailable; the app shows which source was used.
  - thaifin's D/E is *total liabilities* / equity; Yahoo's is *interest-bearing debt* / equity.
  - thaifin's yearly dividend yield is not used: its units are inconsistent across years.
  - Recently listed stocks (e.g. MRDIYT) have only 1–2 years of history.
- **SET100 list:** `data/set100.csv`, for 1 Jul – 31 Dec 2026, built on 2026-11-21 from SET's official
  `SET50_SET100_H2_2026_revise.pdf` ("SET100 / SET100FF Index Constituents … July 1 - December 31, 2026,
  Update on August 3, 2026", pages 3–5; SET50 on pages 1–2 sets the `in_set50` column), from the
  "July 1, 2026 to December 31, 2026 – between the periodic review update" file on
  https://www.set.or.th/en/market/information/securities-list/constituents-list-set50-set100 (login required).
  Symbols and sectors are as printed; names of non-SET50 stocks are the PDF's, minus "Public Company Limited".
  SET reviews the index every 6 months — update the CSV (and the lists in `tests/test_universe.py`) in January
  and July, together with `SET100_PERIOD` and `SET100_PERIOD_END` in `src/universe.py`. After
  `SET100_PERIOD_END`, both pages warn that the list may be out of date.
  The stock page also opens stocks outside SET100 (`?symbol=MAJOR`); their sector shows as "Outside SET100".
- **Your portfolio:** `data/portfolio.csv`, written by the Portfolio page. It is in `.gitignore`, so your real
  holdings are never committed. Numbers ignore trading fees, VAT and dividend tax; the estimated dividend is
  last complete year's dividend per share × shares.
- **Linked, not shown** (no free official API): the stock page's "See on the SET website" button links to the
  stock's SET pages (trading signs, major shareholders, XD/XR, news) and to SET's all-stock pages for investor
  types, NVDR, short sales, caution signs, cash balance / turnover list and Auto Pause, plus Form 59 on the SEC
  website.
- **Dividend yield history:** dividends per share (Yahoo, by XD year) ÷ the year's last close as traded, last 15
  years (Yahoo returns nothing for longer periods of some stocks).

## Project structure

```
app.py                         # entry point + navigation
app_pages/today.py             # default page: portfolio stocks to look at today
app_pages/screener.py          # SET100 table
app_pages/stock.py             # one-stock detail page (7 tabs)
app_pages/portfolio.py         # holdings + watchlist editor
src/__init__.py
src/universe.py                # SET100 list + the SET sector names in use
src/data.py                    # daily prices
src/fundamentals.py            # snapshot, financials, dividends, P/E history, sector medians
src/indicators.py              # SMA, RSI, volatility, support/resistance
src/charts.py                  # Plotly price chart
src/model.py                   # prediction model + backtest
src/screener.py                # screener helpers (selected row -> symbol)
src/portfolio.py               # load, check and save holdings (data/portfolio.csv)
src/today.py                   # rules that flag a stock on the Today page
src/set_links.py               # links to the SET website + free float
src/valuation.py               # fair value: DDM, DCF, sensitivity table
src/scoring.py                 # Piotroski F-score, Magic Formula rank
src/cache.py                   # Streamlit caching of all loaders
data/set100.csv                # SET100 constituents (with an in_set50 flag)
scripts/check.sh               # all checks (pytest + ty); CI runs the same script
scripts/stocks.sh              # start/stop the app in the background (macOS)
.github/workflows/ci.yml       # GitHub Actions CI
tests/conftest.py              # blocks network access; fake Yahoo fixture
tests/fakes.py                 # offline fakes for yfinance
tests/test_model.py            # features, target, leakage, backtest split
tests/test_fundamentals.py     # S/R levels, P/E history, sector medians, thaifin fallback
tests/test_normalization.py    # unit conversions from thaifin and Yahoo
tests/test_outage.py           # behaviour when Yahoo is down
tests/test_pages.py            # AppTest smoke tests for both pages
tests/test_navigation.py       # screener row -> stock page
tests/test_portfolio.py        # holdings: input checks, saving, Portfolio page
tests/test_today.py            # Today rules at their boundaries
tests/test_growth.py           # 5-year CAGR and average ROE
tests/test_valuation.py        # DDM / DCF hand-computed examples
tests/test_scoring.py          # F-score checks, Magic Formula rank
tests/test_set_links.py        # SET links and free float
tests/test_universe.py         # SET100 CSV matches SET's document
tests/test_requirements.py     # pinned dependencies
tests/test_ci.py               # CI workflow and check script
tests/test_docs.py             # README and in-app text stay in sync with the code
```

## Results of the prediction model (honest)

On the stocks tested, test accuracy is about the same as a naive baseline — no real edge.
That is the expected result for daily price direction, and the app reports it rather than hiding it.

> For learning only — not investment advice.
