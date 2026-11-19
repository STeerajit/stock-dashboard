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

## Backlog #4 — verify screener row → stock page in a real browser

**Status:** covered by tests as far as possible without a browser. The real-browser check is **blocked**:
the Claude in Chrome extension was not connected (2026-11-20), and AppTest cannot click dataframe rows.

**What is tested now** (`tests/test_navigation.py`, offline):
- The row → symbol mapping (`src/screener.py:selected_symbol`) uses the table **exactly as shown**. With the
  Banking filter on, the 3rd row is the 3rd visible bank, not the 3rd stock overall.
- When the screener sets `st.session_state["symbol"]` and switches page, the stock page opens that symbol.
- `/stock?symbol=SCB` opens SCB.

**Still to check by hand (about 2 minutes):** run `streamlit run app.py`, then:
1. Click the **PTT** row → the stock page shows "PTT · PTT", and the address bar contains `?symbol=PTT`.
2. Click **SET50 screener** in the sidebar → you stay on the screener (no automatic jump back to PTT).
3. Choose **Banking** in the Sector filter, click the 3rd row → the stock page shows that 3rd bank.

If step 2 jumps back to the stock page, the old row selection is being kept between pages. The fix is to clear
`st.session_state["screener"]` before calling `st.switch_page`.
