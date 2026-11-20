# Blocked items

## Backlog #7 — prove the GitHub Actions workflow fails on a failing test

**Status:** the workflow file is written, but it has **never run**. The repo has no GitHub remote yet, and
pushing was not allowed. What was checked instead: `scripts/check.sh`, the exact command the workflow runs,
exits 1 with a deliberately failing test and 0 after reverting it (locally, 2026-11-20).

**What you need to do** (after the repo is on GitHub, e.g. as part of #8):
1. Push the branch and open the **Actions** tab → the "CI" run should be green.
2. On a throwaway branch, add `def test_fail(): assert False` to any test file and push → the run must turn red.
3. Delete that branch. Then tick this box in BACKLOG.md #7.

Also check that the README badge works: it assumes the repo is `STeerajit/stock-dashboard`.
