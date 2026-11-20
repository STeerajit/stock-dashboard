# Blocked items

## Backlog #3 — verify the SET50 list against SET's official H2/2026 document

**Status:** partly done. The CSV validation test is in place (`tests/test_universe.py`).
Checking the 50 symbols against the official list is **blocked**, and `SET50_PERIOD` was not changed.
No symbols were guessed or changed.

**Why blocked:** SET's official H2/2026 constituent files can only be downloaded after logging in to set.or.th.

**What was tried (2026-11-20):**

| URL | Result |
|---|---|
| https://www.set.or.th/en/market/information/securities-list/constituents-list-set50-set100 | 200, but every 2026 file is behind "Login to download file" |
| https://media.set.or.th/set/Documents/2026/Jun/SET50_100_H2_2026.pdf | 404 |
| https://media.set.or.th/set/Documents/2026/Jun/SET50_100_H2_2026_revise.pdf | 404 |
| https://media.set.or.th/set/Documents/2026/May/SET50_100_H2_2026.pdf | 404 |
| https://media.set.or.th/set/Documents/2026/Jun/SET50SET100_H2_2026.pdf | 404 |
| https://media.set.or.th/set/Documents/2026/Jun/SET50_100_H2_2026.PDF | 404 |
| https://media.set.or.th/set/Documents/2025/Dec/SET50_100_H1_2026.pdf | 200, but it is the **H1**/2026 list (the base the CSV was built from) |

**Important finding:** the SET page lists **two** H2/2026 files:
- "July 1, 2026 to December 30, 2026" → `.../2026/Jun/SET50-SET100-H2-2026.pdf`
- "July 1, 2026 to December 31, 2026 – between the periodic review update" → `.../2026/Jul/SET50_SET100_H2_2026_revise.pdf`

So SET **revised** the H2 list mid-period. The current CSV (H1 list + the June changes reported by Kaohoon)
may not include that revision.

**What you need to do:** log in to set.or.th, download the *revise* file above, and either paste its
SET50 table to Claude, or edit `data/set50.csv` by hand (`pytest tests/test_universe.py` checks the format).
Then set `SET50_PERIOD` in `src/universe.py` to the period printed in that document.

## Backlog #7 — prove the GitHub Actions workflow fails on a failing test

**Status:** the workflow file is written, but it has **never run**. The repo has no GitHub remote yet, and
pushing was not allowed. What was checked instead: `scripts/check.sh`, the exact command the workflow runs,
exits 1 with a deliberately failing test and 0 after reverting it (locally, 2026-11-20).

**What you need to do** (after the repo is on GitHub, e.g. as part of #8):
1. Push the branch and open the **Actions** tab → the "CI" run should be green.
2. On a throwaway branch, add `def test_fail(): assert False` to any test file and push → the run must turn red.
3. Delete that branch. Then tick this box in BACKLOG.md #7.

Also check that the README badge works: it assumes the repo is `STeerajit/stock-dashboard`.
