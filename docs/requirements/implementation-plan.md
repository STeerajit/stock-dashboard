# Implementation plan (reviewed 2026-11-22)

Requirements: [`investor-features.md`](investor-features.md). Branches are stacked:
`feat/safety-grade` (from `main`) → `feat/concentration` → `feat/income-calendar`.
Each: test-first, `scripts/check.sh` must pass, commit on the feature branch only, never `main`, never push.

## Gotchas for every feature
- `tests/test_docs.py` requires every new `src/` and `tests/` file to be listed in the README "Project structure" block.
- Page fixtures stub only some loaders: `fake_cache` (`tests/test_pages.py`), `fake_market` (`tests/test_portfolio.py`),
  `today_page` (`tests/test_today.py`). Any new `cache.*` call on a page must be stubbed there, or the network guard raises.
- i18n: pure modules use `text(key, lang, ...)`, pages use `t()`. Keys built at run time (e.g. `text(f"safety.check.{k}")`)
  must be added to `test_keys_built_at_run_time_exist`. TH and EN need the same placeholders. Page AST test rejects
  literal strings passed to `markdown`, `caption`, etc.
- `st.expander` is not lazy. For lazy loading use the `stock.py` pattern: `st.tabs(..., key=..., on_change="rerun")` + `if tab.open:`.
- `ty`: cast `.at[]` / `.get()` results (see `cast(int, ...)` in `app_pages/dividend_picks.py`), annotate `Literal` fields,
  no `st.cache_data` on functions taking `StockData` (unhashable).

## 1. Safety grade — `feat/safety-grade`
- `src/cache.py`: add `dividend_events(symbol)` (`store.load_dividends` if `_stored`, else `fd.get_dividends`;
  `ttl="24h", max_entries=100`, same pattern as `dividends()`), and `quarterly(symbol)` wrapping `_quarterly`.
- `src/dividend_picks.py`: factor `ttm_payout(d, as_of)` out of `screen` (uses `published_financials`,
  `qt.fiscal_year_end`, `qt.published`, `qt.latest_eps`, `trailing_dividends`); `screen` uses it.
- New pure `src/safety.py`:
  ```python
  class Check(NamedTuple): key: str; status: Literal["good","ok","bad","unknown","skipped"]; reason: str
  class Grade(NamedTuple): level: str; checks: list[Check]   # level in LEVELS or "not_enough_data"
  LEVELS = ("safe", "ok", "risky", "unsafe")
  FINANCIAL_SECTORS = {"Banking", "Finance & Securities", "Insurance"}
  def per_year(dividends: pd.Series, as_of) -> pd.Series
  def special_years(per_year: pd.Series, factor=1.5) -> set[int]   # median of the other years, last 10 complete years
  def years_since_cut(...) -> float   # per-year scan, special years removed first
  def paid_streak(...) -> int          # special years count as paid
  def grade(d: dp.StockData, sector: str, as_of, lang="en") -> Grade
  ```
  CAGR: use `fd._cagr` (NaN-safe; make it public if needed), NOT `valuation.dividend_growth` (returns 0.0, caps at 10%).
  Thresholds + sources (Morningstar payout study, SETHD 100% cap) in the docstring or `docs/research/dividend-safety.md`.
- Wiring: Dividend picks cards build from `data[symbol]` (no new fetches). Stock page: inside `if t_div.open`, build
  `StockData` from `cache.prices`, `cache.unadjusted_close`, `cache.dividend_events`, `cache.financials`,
  `cache.quarterly`; stub these in `fake_cache`. Portfolio: column for held stocks only (document ~2 thaifin fetches
  per holding in public mode).
- Tests: `test_payout_at_threshold_boundaries` (parametrised below/at/above), `test_missing_check_is_unknown_not_bad`,
  `test_fewer_than_3_known_is_not_enough_data`, `test_bank_skips_fcf_and_says_so`,
  `test_special_year_flagged_above_1_5x_median` (1.5× exactly not flagged), `test_special_year_excluded_from_cagr_and_cut`,
  `test_fcf_bad_in_one_of_3_years_is_not_bad`, `test_fcf_bad_in_2_of_3_is_bad`, `test_reasons_in_thai`;
  page tests for stock dividend tab, picks cards, portfolio column.

## 2. Concentration — `feat/concentration`
- Move `quotes()` from `app_pages/portfolio.py` to `cache.quotes(symbols)` (plain function over cached loaders) so Today can use it.
  `today_page` fixture must then stub `set100`, `snapshots`, `snapshot`, `dividends`.
- `src/portfolio.py`: `Breach(kind: Literal["stock","sector","income"], name, share, cap)`,
  `DEFAULT_CAPS = {"stock": .20, "sector": .35, "income": .25}`, `concentration(pos, caps=DEFAULT_CAPS) -> list[Breach]`.
  Filter `value.notna()` like `totals`; breach = strictly greater; skip `OUTSIDE_SET100` for sectors; no income breach when total is 0.
- Caps in `st.session_state["conc_caps"]` (a key no widget owns), copied via `on_change`; defaults if missing.
  Help text: a one-stock portfolio always breaches the stock cap.
- Tests: `test_default_caps`, `test_breach_reports_name_share_cap`, `test_at_cap_is_not_a_breach`,
  `test_watchlist_and_unpriced_excluded`, `test_empty_portfolio_no_breaches`, `test_income_share_uses_est_dividend`,
  `test_zero_income_no_income_breach`; AppTest: Portfolio warning box (stock, %, cap) and cap change persists;
  Today line only when over a cap.

## 3. Income calendar — `feat/income-calendar`
- New pure `src/income.py`: `TAX = 0.10`; `monthly(events: dict[str, pd.Series], shares: dict[str, float], this_year: int)
  -> pd.DataFrame` (12 rows, gross/tax/net per symbol; amounts from the last complete year only, so yearly gross ==
  `est_dividend`); year −2 used only for the "XD month may shift" flag; `summary(pos, calendar) -> pd.DataFrame`
  (yearly gross, net, net yield on cost = net / cost, `no_recent` flag).
- Portfolio page: lazy tab (`.open` pattern), call `cache.dividend_events` only for held stocks.
- Tests: `test_bins_by_xd_month`, `test_two_payments_same_month_sum`, `test_months_sum_to_yearly_gross`,
  `test_tax_is_10_percent_net_is_90`, `test_no_dividend_last_year_is_zero_and_listed`, `test_net_yield_on_cost`,
  `test_watchlist_rows_ignored`; AppTest: "expected XD month" label appears, calendar does not load until its tab opens.
