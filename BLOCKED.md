# Blocked items

## Backlog #7 — prove the GitHub Actions workflow fails on a failing test

**Status:** since 2026-11-21 the repo is on GitHub and the CI workflow runs green on `main`. Still unchecked:
that a failing test turns it red. What was checked instead: `scripts/check.sh`, the exact command the workflow runs,
exits 1 with a deliberately failing test and 0 after reverting it (locally, 2026-11-20).

**What you need to do** (after the repo is on GitHub, e.g. as part of #8):
1. Push the branch and open the **Actions** tab → the "CI" run should be green.
2. On a throwaway branch, add `def test_fail(): assert False` to any test file and push → the run must turn red.
3. Delete that branch. Then tick this box in BACKLOG.md #7.

Also check that the README badge works: it assumes the repo is `STeerajit/stock-dashboard`.

## Backlog #14 — spot check of yearly dividend yield against SET, years 2022–2023

**Status:** partly checked (2026-11-21). SET's free factsheet page
(`https://www.set.or.th/en/market/product/stock/quote/<SYMBOL>/factsheet`) shows the dividend yield only for the
last two full years, so SET's own figure for 2022 and 2023 could not be found without a login.

| Stock | Year | App | SET factsheet | Difference |
|---|---|---|---|---|
| PTT | 2025 | 6.88% | 6.62% | +0.26 pp |
| PTT | 2024 | 6.30% | 6.30% | 0.00 pp |
| ADVANC | 2025 | 4.04% | 3.39% | +0.65 pp |
| ADVANC | 2024 | 3.30% | 3.00% | +0.30 pp |

For 2022–2023 only the inputs were checked: dividends per share per year match SET's dividend table on the same
page exactly (PTT 2.10 and 1.50 THB; ADVANC 7.69 and 8.24 THB), so the yield differs from SET's only through
the year-end price used.

**What you need to do** (optional): log in to set.or.th (or open SETSMART if you have it), find PTT and ADVANC
dividend yield at year-end 2022 and 2023, and check they are within ±1 pp of the app (PTT 6.32%, 4.20%;
ADVANC 3.94%, 3.80%). Then tick the spot-check box in BACKLOG.md #14.

## Backlog #12 — publish the article

**Status:** written and reproducible ([docs/article.md](docs/article.md), figures in `docs/img/`), not published.
Publishing needs your own Medium, LinkedIn or dev.to account, and the "Live app" link needs the deploy (#8).

**What you need to do:** paste `docs/article.md` into your platform (upload the two PNGs from `docs/img/`), add
the live-app link once #8 is done, publish, and put the article's URL in the README. Then tick the two open
boxes in BACKLOG.md #12.

## Backlog #8 — deploy to Streamlit Community Cloud

**Status:** ready to deploy, not deployed. The repo is public on GitHub (https://github.com/STeerajit/stock-dashboard,
`main` pushed 2026-11-21, CI green); Streamlit Cloud needs your own login. (Checked: all commits use your GitHub noreply address, so no personal email becomes public.)

**What you need to do:**
1. ~~Put the repo on GitHub as public and push `main`~~ — done.
2. Open https://share.streamlit.io, sign in with GitHub → **Create app** → repo, branch `main`, file `app.py`,
   Python 3.11 → **Advanced settings → Secrets**: `STOCKS_PUBLIC = "1"` → **Deploy**.
3. Check: the screener shows 100 rows within 30 s, and `<url>/stock?symbol=KBANK` opens KBANK.
4. Put the URL at the top of the README and in docs/article.md ("Live app"), then tick the boxes in BACKLOG #8.

## Dividend Picks — buybacks left out of net payout yield (needs your decision)

**Status (2026-11-21):** the Conservative Formula ranks by *net payout yield* (dividends + buybacks). Our only
share count is thaifin's year-end market cap / close, and it is not reliable: PTT, whose share count has not
changed, moves 28,563M → 28,638M → 27,882M shares (2022–2025), and PRM jumps 2,610M → 2,011M → 2,500M. Used as
buybacks, that noise (up to ±25% a year) would outweigh the dividend yield itself.

**What was done instead:** `USE_BUYBACKS = False` in `src/dividend_picks.py`, so the rank uses the dividend yield
only. The buyback calculation and its tests stay, ready for better data.

**What you need to decide:** keep dividend yield only (buybacks are rare among Thai SET100 companies), or name a
source for real share counts (e.g. SET's company profile) to fetch.

## Dividend Picks — no history for the SET index (needs your decision)

**Status (2026-11-21):** the "market trend" signal compares the SET index with its 10-month average. Yahoo
Finance returns only today's value for `^SET.BK` (and `^SET`), for every period tried (5y, 10y, 15y, max, a start
date), through both `yf.download` and `Ticker.history`.

**What was done instead:** `equal_weight_index()` in `src/dividend_picks.py` builds an equal-weighted index of the
current SET100 stocks from the stored dividend-adjusted prices, and the signal says so on the page. It differs from
the real SET index: equal weights instead of market-cap weights, dividends included, and today's SET100 members
only (survivorship bias).

**What you need to decide:** keep the stand-in, or name a source for the SET index history (for example a CSV
downloaded from SET's website, saved in `data/`).
