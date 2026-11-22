# Investor features: requirements (2026-11-22)

Written from the point of view of a long-term dividend / fundamental investor who uses the app **locally** for
real decisions and wants plain-language explanations. Process and status: [`GOAL.md`](GOAL.md).

**How these were chosen:** three research passes (investor decision needs, competitor tools, free Thai data
sources), then a critic pass that checked each idea against the code and the project constraints
(free data only, public mode must not get slower, TH + EN text via `t()`, offline tests).

**Build order** (1 and 2 both edit `app_pages/today.py` and `app_pages/portfolio.py`, so build one after another):

| # | Feature | Size | Backlog |
|---|---|---|---|
| 1 | Dividend safety grade | M | #23 |
| 2 | Concentration warnings | S | #24 |
| 3 | Dividend income calendar, net of tax | M | #25 |

---

## 1. Dividend safety grade

**Decision it supports:** "Is this dividend likely to keep coming, or is the yield a trap?" Payout ratio is the
strongest known predictor of dividend cuts (Morningstar, 20-year study), and avoiding cuts matters more than the
highest yield. Paid tools sell this as a grade (Seeking Alpha Dividend Grades, Simply Safe Dividends).

**Where:** new pure module `src/safety.py`. Shown on the Stock page dividend tab, on each Dividend picks card,
and as a column in Portfolio (holdings only). **Not** on the Screener: it would need about 100 extra fetches in
public mode.

**Data (reuse):** `dp.trailing_dividends`, `qt.latest_eps` (TTM payout, as in `screen`), yearly FCF and Shares,
sector from `set100.csv`. New cached loaders `cache.dividend_events(symbol)` and `cache.quarterly(symbol)`
(feature 3 reuses `dividend_events`).

**Checks:** EPS payout, FCF payout, years since the last cut, years paid in a row, 5-year DPS CAGR,
special-dividend flag. (Net debt / EBITDA is left out: the data has no EBITDA.)

**Acceptance criteria**
- [ ] `grade()` returns one of 4 levels (`safe`, `ok`, `risky`, `unsafe`) or the separate state
  `not_enough_data`, plus a list of reasons, each translated with `text()` (TH and EN).
- [ ] FCF payout is skipped for financial sectors (`Banking`, `Finance & Securities`, `Insurance`), and the
  reason text says so. (No leverage check: the data has no EBITDA, and thaifin's D/E is meaningless for banks.)
- [ ] A check with missing data is "unknown", never "bad". Fewer than 3 known checks → "not enough data".
- [ ] A year whose DPS is more than 1.5× the previous paid year **and** more than 1.5× the following year (a
  one-off spike, last 10 complete years) is flagged special. The latest complete year (no following year yet) is
  special if its DPS is more than 1.5× the previous paid year **and** more than 1.5× the median of the previous 3
  paid years. Exactly 1.5× is not special; a
  steady grower or a recovery after a low year is never flagged. (Changed 2026-11-22: the first rule, 1.5× the
  median of the other 10 years, flagged 31 of 96 SET100 stocks, mostly steady growers.) It still counts as paid in the streak, but its amount is left out of the CAGR and of cut detection
  (so the year after a special dividend is not a cut).
- [ ] A cut is a year whose DPS is below 90% of the previous (non-special) year; a drop of exactly 10% is not a
  cut. (Changed 2026-11-22, owner's decision: Thai dividends follow a payout ratio and wobble year to year, so
  any drop counted as a cut. The 10% is not a research figure.)
- [ ] FCF payout = (DPS × Shares) / FCF. It is bad only if FCF ≤ 0 or payout > 100% in at least 2 of the last
  3 years, with at least 2 of those years known; otherwise unknown (thaifin's FCF includes acquisitions).
- [ ] EPS payout uses the same TTM calculation as the Dividend picks screen (one shared helper).
- [ ] 5-year CAGR is NaN-safe: missing data gives unknown, never 0%.
- [ ] Boundary unit tests for every threshold, built from `tests/fakes.py`. Each threshold's source is written
  in the module docstring or `docs/research/`.

## 2. Concentration warnings

**Decision it supports:** "Should I add to this stock or sector, or am I already too heavy?" SET100 dividend
stocks lean towards banks and energy, so a dividend portfolio drifts into a few sectors without noticing.
Common practice caps one stock at about 5–10% and a sector at 20–25%; the defaults below are looser because a
small personal portfolio holds fewer stocks.

**Where:** `concentration(pos, caps)` in `src/portfolio.py`. Portfolio page: a warning box plus cap inputs.
Today page: one line when something is over a cap. No new chart (the sector allocation chart already exists).

**Data (reuse):** `positions()` value, `est_dividend` and sector.

**Acceptance criteria**
- [ ] Default caps: 20% per stock, 35% per sector, 25% of dividend income from one stock. A breach means strictly
  above the cap. Caps can be changed on the Portfolio page and are kept in session state, so Today uses them too.
- [ ] Each breach shows the stock or sector, its actual %, and the cap.
- [ ] Watchlist rows (0 shares) and stocks without a price are left out of every share. Stocks outside SET100
  are left out of the sector check. No income warning when total income is 0.
- [ ] An empty portfolio gives no warnings and no errors.
- [ ] AppTest: Today shows the line only when something is over a cap.

## 3. Dividend income calendar, net of tax

**Decision it supports:** "How many baht will arrive in which month over the next 12 months?" This is the
signature feature of income trackers (Snowball, Settrade Sense alerts). Thai dividends have a 10% withholding
tax, so the useful number is the net amount.

**Where:** new pure module `src/income.py`. Portfolio page: a monthly bar chart and a table inside a tab that
loads only when opened (an expander is not lazy). Reuses `cache.dividend_events(symbol)` from feature 1.

**Data (reuse):** `store.load_dividends` / `fd.get_dividends`, `positions()` shares and cost.

**Acceptance criteria**
- [ ] The amount for a month is the last complete year's dividends with an XD date in that month × shares held,
  so the yearly gross equals `est_dividend` in `positions()`. If the year before had XD dates in different
  months, the stock is flagged "XD month may shift".
- [ ] Gross, 10% withholding tax and net are shown. The 12 monthly totals add up to the yearly gross estimate
  (within rounding).
- [ ] Labels say "expected XD month; payment usually about a month later". No payment date is invented, since
  the free data has none.
- [ ] A stock that paid nothing last year adds 0 and is listed as "no recent dividend".
- [ ] Net yield on cost is shown for each holding.
- [ ] Unit tests for the month binning and the totals, with fake dividend events.

---

## Ideas not chosen

| Idea | Why not now |
|---|---|
| Total return vs a benchmark | Needs a buy / sell / dividend-received ledger the app does not have (L). The only free total-return proxy is TDEX (SET50 only), a weak benchmark for a dividend portfolio. SET TRI is a paid feed. |
| Investment thesis journal with alerts | Needs new local storage and a separate path for public mode. Its alerts overlap the safety grade. |
| "Where should my next money go" planner | Builds on fair value, which depends on slider assumptions, so it would give false precision as a buy instruction. Revisit after features 1 and 2. |
| Thai dividend tax-credit helper | Needs each company's corporate tax rate (BOI exemptions) and the user's tax bracket, typed by hand and easy to get wrong. The 10% withholding part is in feature 3. |
| Fund flow, NVDR, short sales (#16) | No free, legitimate automated source. SET pages are behind bot protection and their terms forbid automated collection. Keep the links in `set_links.py`. |
| Upcoming XD / XR and payment dates | yfinance gives only the latest XD date, and payment dates are usually missing. SET's calendar is behind bot protection. |

## Research sources

- Dividend cuts and payout: https://www.morningstar.com/stocks/not-all-dividend-stocks-are-safe-heres-how-avoid-dividend-traps
- Thai dividend traps: https://www.thairath.co.th/money/investment/stocks/2807499
- Dividend grades: https://about.seekingalpha.com/quant-dividend-grades
- Income calendar: https://snowball-analytics.com/dividend-calendar
- Position sizing: https://www.aaii.com/journal/article/adjusting-overweight-positions,
  https://www.dividendvision.com/learn/position-sizing-income-portfolios
- Thai dividend tax: https://www.thairath.co.th/money/personal_finance/finance_banking/2857794, https://rd.go.th/37041.html
- SET TRI is a paid feed: https://www.set.or.th/en/market/index/tri/profile
- SET data pages: https://www.set.or.th/app/online-data/investor-types?lang=en
