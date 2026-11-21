# Goal: investor-driven features (2026-11-22)

Find and build the 3-5 features a real long-term dividend/fundamental investor
(who also wants plain-language explanations) would want next, then implement them.
The owner uses the app **locally** for real investing (DuckDB store + saved portfolio).

## Constraints (every feature must respect)
- Free data only (yfinance, thaifin, public pages). No paid APIs, no LLM calls.
- Local-first; must not break public mode (`STOCKS_PUBLIC=1`) or make cold start slower.
- All UI text via `t()` in TH and EN.
- Tests cannot use the network (`tests/conftest.py`); use `tests/fakes.py`.
- Done = new tests pass and `scripts/check.sh` passes.

## Steps
| # | Step | Done when | Status |
|---|---|---|---|
| 0 | Write this file | file exists | done |
| 1 | 3 research subagents: investor needs, competitor apps, free data sources | each report cites sources | done |
| 2 | Merge into candidates; critic subagent challenges vs constraints | 3-5 ranked features | done (3) |
| 3 | Write `investor-features.md` (acceptance criteria per feature, rejected ideas + reasons); add items to `BACKLOG.md` | files written | done |
| 4 | Critic reviews implementation plan; summary posted in chat (no waiting) | no major objections left | done |
| 5 | Implement features in priority order, one agent per feature, own git worktree + branch, test-first; may commit on feature branch, never `main`, never push. Stuck > 2 attempts → skip, note reason here | tests + `scripts/check.sh` pass | todo |
| 6 | Review code; owner decides whether to merge into `main` | owner decision | todo |

## Log
- 2026-11-22: plan agreed with owner.
- 2026-11-22: research done (investor needs, competitors, free data). Critic picked 3: safety grade, concentration, income calendar. Rejected ideas + reasons in investor-features.md.
- 2026-11-22: plan reviewed; requirement fixes applied; plan in implementation-plan.md. Starting step 5.
