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
Publishing needs your own Medium, LinkedIn or dev.to account. The "Live app" link is already in it.

**What you need to do:** paste `docs/article.md` into your platform (upload the two PNGs from `docs/img/`),
publish, and put the article's URL in the README. Then tick the two open
boxes in BACKLOG.md #12.
