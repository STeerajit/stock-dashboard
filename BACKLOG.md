# Backlog

Ordered by priority. **P0** = fix before showing the project to anyone,
**P1** = makes it portfolio-ready, **P2** = valuable improvements, **P3** = blocked on a decision or external access.

Effort: **S** ≈ under 2 h · **M** ≈ half a day · **L** ≈ 1–2 days.

| # | Item | Priority | Effort |
|---|---|---|---|
| 1 | Pin dependency versions | P0 | S |
| 2 | Survive Yahoo Finance outages | P0 | M |
| 3 | Verify the SET50 list and validate the CSV | P0 | S |
| 4 | Verify screener row → stock page navigation | P0 | S |
| 5 | Offline smoke tests for both pages (AppTest) | P1 | M |
| 6 | Unit tests for data normalization | P1 | S |
| 7 | Continuous integration (GitHub Actions) | P1 | S |
| 8 | Deploy to Streamlit Community Cloud | P1 | M |
| 9 | Consistency and docs cleanup | P1 | S |
| 10 | Data pipeline: daily data store (DuckDB) | P2 | L |
| 11 | Realistic backtest: trading costs + walk-forward | P2 | M |
| 12 | Write-up: "Why my stock model didn't beat a coin flip" | P2 | M |
| 13 | Fair value and stock scoring | P2 | L |
| 14 | Dividend yield history computed from reliable data | P2 | M |
| 15 | Growth & quality columns in the screener | P2 | M |
| 16 | Phase 2 data spike: fund flows, NVDR, short sales, warnings | P3 | M |
| 17 | LLM news sentiment (step 3) | P3 | L |
| 18 | Thai / English UI toggle | P3 | M |

---

## 1. Pin dependency versions — P0 · S

**Why:** `requirements.txt` has no versions. A fresh install (or a deploy) can pull a newer
`yfinance`/`streamlit` that changes behavior — e.g. `get_snapshot` divides `dividendYield` by 100
because current yfinance returns percent, and `st.tabs(on_change=...)` / `bind="query-params"` need a recent Streamlit.
`pytest` is a dev-only tool but is installed in production.

**Acceptance criteria**
- [x] `requirements.txt` lists runtime packages only, each pinned with `==` to the versions in `.venv` today.
- [x] `requirements-dev.txt` starts with `-r requirements.txt` and adds `pytest` (pinned).
- [x] In a brand-new venv: `pip install -r requirements-dev.txt && pytest` → all tests pass.
- [x] README "How to run" mentions both files.

---

## 2. Survive Yahoo Finance outages — P0 · M

**Why:** `get_snapshots` turns every failed symbol into `{"symbol": sym}`. If Yahoo is down for *all*
symbols, the DataFrame has no `pe`/`price` columns, so `sector_medians` and the screener raise `KeyError`
and the user sees a traceback. Partial failures are also cached for 15 minutes (`cache.snapshots`),
so a 10-second network blip leaves blank rows for 15 minutes.

**Acceptance criteria**
- [x] `get_snapshots` always returns every snapshot column, even when all fetches fail (NaN values). Unit test with `yf.Ticker` monkeypatched to raise.
- [x] If more than 20% of symbols fail, `cache.snapshots()` raises instead of returning, so the result is **not** cached. Unit test asserts the raise.
- [x] With Yahoo unreachable, the screener shows one `st.error` with a "try again" message and no traceback (verified with AppTest from #5).
- [x] With Yahoo unreachable, the stock page Trading tab shows a warning instead of crashing.
- [x] When one symbol fails, the other 49 rows still render.

---

## 3. Verify the SET50 list and validate the CSV — P0 · S

> **Partly blocked** — the official H2/2026 file needs a SET login. See [BLOCKED.md](BLOCKED.md).

**Why:** `data/set50.csv` was built from SET's H1/2026 official list plus H2/2026 changes reported by a news site.
It was never checked against SET's own H2/2026 document. A wrong list undermines the whole screener.

**Acceptance criteria**
- [ ] The 50 symbols are checked against SET's official H2/2026 SET50 constituent list. The source URL and check date are written in the README.
- [x] New test `tests/test_universe.py`:
  - exactly 50 rows, 50 unique symbols, no blanks in `symbol`/`name`/`sector`;
  - every `sector` value belongs to a fixed allowed list (the SET sector names already used).
- [ ] `SET50_PERIOD` in `src/universe.py` matches the period printed in the official document.

---

## 4. Verify screener row → stock page navigation — P0 · S

**Why:** Selecting a row calls `st.session_state["symbol"] = ...` then `st.switch_page(...)`.
This path was never tested (the agent API cannot select dataframe rows). One risk: when the user comes back
to the screener, the old row selection could still be active and redirect them again immediately.

**Acceptance criteria** (manual check in a real browser, then documented in the PR)
- [ ] Click the PTT row → the stock page opens showing **PTT**, and the URL contains `?symbol=PTT`.
- [ ] Click "SET50 screener" in the sidebar → the screener stays open (no automatic redirect).
- [ ] With the Banking filter on, clicking the 3rd row opens the 3rd **visible** bank (not the 3rd stock overall).
- [ ] If any check fails, fix it and add an AppTest regression test where possible.

---

## 5. Offline smoke tests for both pages (AppTest) — P1 · M

**Why:** The UI is only checked by hand. Page-level bugs (like the `?symbol=` bug found earlier) are only caught
by running the app. Tests must not need the internet, so they stay fast and stable in CI.

**Acceptance criteria**
- [ ] `tests/test_pages.py` uses `streamlit.testing.v1.AppTest` with the `src.cache` loaders replaced by fixtures (small fake snapshots, prices, financials).
- [ ] Screener test: renders with no exception, table has as many rows as the fake universe, the sector filter reduces the row count.
- [ ] Stock page test: opening with `symbol=PTT` shows the title "PTT · ..." and each of the 6 tabs renders with no exception.
- [ ] Stock page test with financials returning an empty DataFrame → shows the "No data" warning and no exception.
- [ ] `pytest` passes with networking disabled (e.g. `pytest -p no:cacheprovider` on a machine with Wi-Fi off).

---

## 6. Unit tests for data normalization — P1 · S

**Why:** The riskiest code is unit conversion, and it has no tests: thaifin percent → fraction (`/100`),
`0` → NaN for P/E and P/BV, Yahoo `debtToEquity / 100`, `dividendYield / 100`, and the thaifin-vs-Yahoo D/E definitions.

**Acceptance criteria**
- [ ] Test for `_financials_thaifin` with a fake `yearly_dataframe` (monkeypatched `thaifin.Stock`):
  `gpm=50` → `Gross margin == 0.5`; `price_earning_ratio=0` → `P/E` is NaN; `None` cells → NaN (no exception);
  `attrs["source"] == "thaifin"`.
- [ ] Test for `get_snapshot` with a fake `info` dict: `dividendYield=4.78` → `div_yield == 0.0478`;
  `debtToEquity=57.4` → `de == 0.574`; `pos_52w` is 0 at the low and 1 at the high.
- [ ] Test that `get_financials` falls back to Yahoo when thaifin returns fewer than 2 years.

---

## 7. Continuous integration (GitHub Actions) — P1 · S

**Why:** A green CI badge shows reviewers the project is tested. Depends on #1 (pinned deps) and a GitHub repo.

**Acceptance criteria**
- [ ] `.github/workflows/ci.yml` runs on every push and pull request: install `requirements-dev.txt`, then `pytest`, then `ty check`.
- [ ] A deliberately failing test makes the workflow fail (checked once, then reverted).
- [ ] The README shows the CI status badge.

---

## 8. Deploy to Streamlit Community Cloud — P1 · M

**Why:** The biggest portfolio win is a live link reviewers can click. Requires a **public** GitHub repo
(the user must explicitly choose to make it public). Depends on #1 and #2.

**Acceptance criteria**
- [ ] The app is live at a public `*.streamlit.app` URL, and the README links to it at the top.
- [ ] Opening the live URL shows the screener with 50 rows within 30 seconds on a cold start.
- [ ] `<live-url>/stock?symbol=KBANK` opens KBANK directly.
- [ ] The README has at least 2 screenshots (screener, stock chart tab) stored in `docs/`.
- [ ] No secrets in the repo (`git grep -i "api_key\|token"` returns nothing).

---

## 9. Consistency and docs cleanup — P1 · S

**Why:** Some text is out of date after adding thaifin.

**Acceptance criteria**
- [ ] `src/fundamentals.py` module docstring mentions both data sources (it still says "Yahoo … 4-5 years" only).
- [ ] The sidebar caption in `app.py` names both Yahoo Finance and thaifin.
- [ ] The screener's D/E column help says it is Yahoo's *interest-bearing debt / equity* (the detail page may show thaifin's *total liabilities / equity*).
- [ ] The README project-structure block lists every file in `src/`, `app_pages/`, `tests/` (checked against `git ls-files`).

---

## 10. Data pipeline: daily data store (DuckDB) — P2 · L

**Why:** Every page view downloads live from Yahoo and thaifin. This makes the app slow on first load and
fragile when a source is down (#2 only softens that). We also keep no history of our own, e.g. a daily P/E series.
A small daily pipeline fixes all three and shows data-engineering skill.

**Acceptance criteria**
- [ ] `scripts/update_data.py` fetches, for every SET50 symbol: daily prices (adjusted **and** unadjusted close), the trading/valuation snapshot, yearly financials and dividends. It writes them to `data/market.duckdb` in the tables `prices`, `snapshots`, `financials`, `dividends`.
- [ ] Idempotent: running it twice on the same day leaves the same row counts (unique keys like `(date, symbol)`). Unit-tested on a temporary database.
- [ ] Incremental: the second run asks only for price days after the latest stored date. A unit test checks the requested date range with the fetchers mocked.
- [ ] Safety: if more than 20% of symbols fail, or any stored price is ≤ 0, the script exits non-zero and leaves the existing store untouched.
- [ ] The app reads through `src/cache.py` from the store, not the network. With Wi-Fi off, both pages still render the last stored data and show "Data as of <date>".
- [ ] The screener's first load from the store takes under 3 seconds.
- [ ] A scheduled GitHub Actions job runs the script on weekdays after market close (18:30 Bangkok = 11:30 UTC) and can also be started manually. Depends on #7.

---

## 11. Realistic backtest: trading costs + walk-forward — P2 · M

**Why:** The backtest ignores trading costs and uses a single 80/20 split, so the result depends on one lucky
or unlucky period. Also, the last training row's target is the first test day's return (a 1-day overlap).

**Acceptance criteria**
- [ ] `train_and_backtest` takes `cost_per_trade` (default 0.17% per side, roughly a Thai online commission + VAT) and deducts it each time the strategy enters or exits.
- [ ] A test: a strategy that flips every day ends lower with costs than without.
- [ ] Walk-forward evaluation: at least 4 consecutive test windows, each trained only on data before it; the UI shows accuracy per window and the average.
- [ ] A 1-day gap between train and test so no training target overlaps the test period; the existing leakage test still passes.
- [ ] The Prediction tab still says plainly whether the model beats the baseline.

---

## 12. Write-up: "Why my stock model didn't beat a coin flip" — P2 · M

**Why:** An honest negative result, explained well, is rare and memorable. It also gets the project far more
readers than a link alone. Needs the live app (#8) and the realistic backtest (#11), so the numbers hold up.

**Acceptance criteria**
- [ ] An article of 1,000–1,800 words is published on Medium, LinkedIn or dev.to (English; a Thai version is optional).
- [ ] It covers: the question, data sources and their limits, what data leakage is and how the test guards against it, and the results.
- [ ] The results table covers at least 5 SET50 stocks: model accuracy vs. baseline, and strategy vs. buy-and-hold **after trading costs**, averaged over the walk-forward windows.
- [ ] Every number is reproducible. `scripts/report_backtest.py` prints the table as Markdown, and the article's numbers match its output for the date stated in the article.
- [ ] At least 2 figures: an equity curve, and accuracy per walk-forward window.
- [ ] It links to the live app and the repo; the README links back to the article; it ends with a "not investment advice" note.

---

## 13. Fair value and stock scoring — P2 · L

**Why:** Comparing P/E with peers says "cheaper or dearer than others", not "worth how much". Fair-value models and
well-known scores show finance knowledge and set the project apart from generic dashboards.

**Acceptance criteria**
- [ ] `src/valuation.py` contains:
  - `ddm_value(dps, growth, required_return)` (Gordon growth). It raises `ValueError` when `required_return <= growth`.
  - `dcf_value(fcf, growth, years, terminal_growth, discount_rate, net_debt, shares)`.
- [ ] Unit tests use hand-computed examples, e.g. DDM with next dividend 2.00, r = 8%, g = 3% → **40.00**.
- [ ] A new "Fair value" tab on the stock page:
  - sliders for the assumptions, with defaults taken from the data (last dividend per share, 5-year dividend growth capped at 10%, r = 8%);
  - shows the fair value and the margin of safety vs. the current price;
  - shows a 3×3 sensitivity table (r × g).
- [ ] For Banking / Finance & Securities / Insurance, DCF is disabled with a one-line reason, and DDM is still shown.
- [ ] `src/scoring.py` computes the Piotroski F-score (9 checks) from yearly financials. Checks without data (e.g. current ratio) count as "n/a", and the score is shown as "x / available". A unit test with a fixture that passes every available check returns the maximum.
- [ ] The screener gets two sortable columns: "F-score" and "Magic Formula rank". The rank combines earnings yield with ROE as a stand-in for return on capital, and that stand-in is noted in the column help.
- [ ] Every fair-value view shows "estimate based on your assumptions — not investment advice".

---

## 14. Dividend yield history computed from reliable data — P2 · M

**Why:** thaifin's yearly dividend yield was dropped because its units are inconsistent (PTT: 0.13 in 2010,
3.1 in 2013). Yield vs. its own history is a key "cheap or expensive" signal for Thai dividend stocks.

**Acceptance criteria**
- [ ] Yearly yield = dividends per share with XD dates in year *Y* (Yahoo) ÷ **unadjusted** year-end close of *Y*.
- [ ] Unit test with fake dividends and prices returns the expected yields.
- [ ] Spot check: PTT and ADVANC yearly yields for 2022–2025 are within ±1 percentage point of SET's published figures (sources noted in the PR).
- [ ] The Valuation tab's history selector offers "Dividend yield" again; the comparison text uses percentage points ("+2.1 pp"), not "% above".

---

## 15. Growth & quality columns in the screener — P2 · M

**Why:** The screener shows only "now" numbers. Long-term quality (steady growth, steady ROE) is what the
financial history is for, and comparing it across 50 stocks is the screener's job.

**Acceptance criteria**
- [ ] New columns: 5-year revenue CAGR, 5-year net-income CAGR, 5-year average ROE (from `get_financials`).
- [ ] CAGR is blank (not an error) when there are fewer than 5 years or the start value is ≤ 0. Unit-tested.
- [ ] The financials for all 50 stocks are fetched in parallel and cached for 1 day; the screener's first load stays under 30 seconds.
- [ ] Sorting by "5y revenue CAGR" works in the UI.

---

## 16. Phase 2 data spike: fund flows, NVDR, short sales, warnings — P3 · M

**Why:** Sections 5–7 of the original spec (investor types, NVDR, short sales, top-10 shareholders,
Form 59, C-sign / cash balance / turnover list) have no free official API. **Blocked on the user choosing a source**
(website scraping vs. paid SETSMART/SET API vs. Settrade Open API).

**Acceptance criteria**
- [ ] `docs/data-sources.md` compares at least 3 sources: cost, which fields they provide, terms of use, and how stable they are.
- [ ] The user picks a source (decision recorded in that file).
- [ ] One proof of concept: NVDR net buy/sell for one stock over the last 20 trading days, as a function with a unit test on saved sample data.

---

## 17. LLM news sentiment (step 3) — P3 · L

**Why:** The original plan used an LLM for news sentiment as an extra model feature.
**Blocked on** a Claude API key and a news source (both cost money).

**Acceptance criteria**
- [ ] The API key is read from `st.secrets` / an environment variable, and `.streamlit/secrets.toml` is in `.gitignore`.
- [ ] A function scores a list of headlines as −1…+1 with a short reason. It is unit-tested with the API mocked.
- [ ] Scores are cached per headline, so the same headline is never paid for twice.
- [ ] The stock page shows the latest headlines with scores. If no key is set, the app still runs and shows an info message.
- [ ] The backtest reports accuracy with and without the sentiment feature, side by side.

---

## 18. Thai / English UI toggle — P3 · M

**Why:** The target users are Thai investors, but the portfolio audience may read English.

**Acceptance criteria**
- [ ] All user-facing strings live in one translation file (e.g. `src/i18n.py`), and none are hard-coded in `app_pages/`.
- [ ] A sidebar toggle switches between ไทย and English, and the choice is kept in the URL (`?lang=th`).
- [ ] A test fails if any translation key is missing in either language.
