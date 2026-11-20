# Spec

What this app is for, what was decided along the way, and how far each part of the original spec has got.
Work items live in [BACKLOG.md](../BACKLOG.md); this file is the *why*.

## Goal

A personal tool for **one investor** (the author) to use for real investing, on a Mac:
pick stocks on fundamentals, then time entries with the chart, and track the stocks they own.

## Original spec (20 Nov 2026, verbatim)

The first request was "ต้องการทำสำหรับหุ้นไทย ตาม set 100" plus this list:

```
ข้อมูลที่ต้องดูสำหรับหุ้นไทย

1. ราคาและการซื้อขาย
   - ราคา, Volume/Value, Bid/Offer, ช่วงราคา 52 สัปดาห์, Market Cap
   - ตอบคำถาม: ตอนนี้ตลาดสนใจหุ้นตัวนี้แค่ไหน

2. งบการเงิน (ย้อนหลัง 5 ปีขึ้นไป)
   - รายได้และกำไรที่เติบโต, Margin, ROE, D/E, Free Cash Flow, ปันผล
   - ตอบคำถาม: บริษัทดีจริงไหม แข็งแรงไหม

3. มูลค่า
   - P/E, P/BV, Dividend Yield เทียบกับค่าเฉลี่ยในอดีตและคู่แข่งในกลุ่ม
   - ตอบคำถาม: ราคาตอนนี้แพงหรือถูก

4. กราฟ
   - แนวโน้ม, แนวรับแนวต้าน, MA, RSI, Volume (ต้องใช้ราคา adjusted)
   - ตอบคำถาม: ควรเข้าซื้อตอนไหน

5. เงินไหลเข้าออก (เฉพาะไทย)
   - Investor Type (ต่างชาติ/สถาบัน/รายย่อย), NVDR, Short Sales
   - ตอบคำถาม: ใครกำลังซื้อหรือขาย

6. ผู้ถือหุ้น
   - ผู้ถือหุ้นใหญ่ 10 อันดับแรก, Free float, แบบ 59 (ผู้บริหารซื้อขาย)
   - ตอบคำถาม: ใครคุมบริษัท คนในมั่นใจไหม

7. สัญญาณเตือน (เฉพาะไทย)
   - เครื่องหมาย C, Cash Balance, Turnover List, Auto Pause
   - ตอบคำถาม: หุ้นมีปัญหาหรือถูกปั่นหรือเปล่า

8. ข่าวและปฏิทิน
   - ข่าวประกาศ SET, วันประกาศงบ, วัน XD/XR
   - ตอบคำถาม: มีเหตุการณ์อะไรที่จะกระทบราคา
```

## Decisions

| Topic | Decision | Why |
|---|---|---|
| Stock universe | SET100 → SET50 → **SET100** for the screener; the stock page and portfolio accept **any Thai symbol** | Started as SET100, cut to SET50 to keep the first version small, back to SET100 for real use. Owned stocks may sit outside any index. |
| News sentiment | **Cancelled** (was BACKLOG #17: LLM news sentiment) | Needs a paid API key and a paid news source; not needed to make decisions. |
| Prediction model | Kept, **for learning only** — never used to decide | Honest result: it does not beat a naive baseline. |
| Data | **Free sources only** (Yahoo Finance, thaifin). Where no free data exists, link to the SET website | No budget for SETSMART / paid APIs. |
| Price delay | ~15 min delay is fine | Mixed style, not day trading. |
| Where it runs | **This Mac only** (`scripts/stocks.sh`), single user | Personal tool; no hosting, no login. Deploying (BACKLOG #8) is not a goal for real use. |
| UI language | English everywhere | Simpler; Thai toggle (#18) stays a P3 idea. |
| Portfolio | Holdings = (symbol, shares, average cost), edited in the app, saved to `data/portfolio.csv` (gitignored). `shares = 0` means watchlist | Real holdings are private and must never be committed. |
| Portfolio numbers | P&L per stock and total (THB and %), allocation by sector, estimated dividend and yield on cost. **No fees or taxes** | Keeps the maths checkable; stated on screen. |
| Estimated dividend | Dividend per share of the **last complete calendar year** × shares | A full year is known; the current year is partial. |
| Sector of stocks outside SET100 | Shown as `Outside SET100` | Yahoo's sector names do not match SET's, so they cannot be mixed. |
| Today overview (planned) | Flags a held/watched stock when: price within 3% above support or broke resistance; RSI < 30 or > 70; XD or earnings date within 14 days; P/E more than 20% below its own historical median | One screen that says "look at these today". |

## Status of the 8 categories

| # | Category | Status | Where / what is missing |
|---|---|---|---|
| 1 | Price & trading | Done | Stock page → Trading tab; screener columns |
| 2 | Financial statements (5+ years) | Done | Financials tab: up to ~16 years from thaifin (Yahoo fallback ~4 years, with a warning) |
| 3 | Valuation | Done | Valuation tab: P/E, P/BV, yield vs. sector median and vs. own history (yield from dividends ÷ unadjusted year-end price) |
| 4 | Chart | Done | Chart tab: adjusted candles, SMA20/50, support/resistance, volume, RSI |
| 5 | Money flows | Partial | Links only: SET's all-stock pages for investor types, NVDR, short sales ("See on the SET website"). No per-stock free data (#16) |
| 6 | Shareholders | Partial | Free float (Yahoo estimate) on the Trading tab; link to SET's major shareholders page. Form 59 is on the SEC website, not linked (could not be verified) |
| 7 | Warning signs | Partial | Links only: SET's caution signs, cash balance / turnover list and Auto Pause pages (all stocks) |
| 8 | News & calendar | Partial | Earnings and XD dates in the app; XR dates and news via links to the stock's SET pages. News sentiment cancelled |

Plus two parts that were not in the original list: the **screener** (compare all stocks at once) and the
**prediction model** (learning only).

## Order of work

1. **Goal A** — data base and portfolio: SET100 list, any symbol on the stock page, Portfolio page with its numbers (BACKLOG #19). **Done 2026-11-21.**
2. **Goal B** — today overview page (#20), yield vs. own history (#14), links to the SET website + free float + XR (#21). **Done 2026-11-21.**
