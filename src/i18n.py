"""Every user-facing string, in English and Thai. Pages call `t("key", name=value)`.

The language comes from the sidebar toggle (kept in the URL as ?lang=th). Pure code (src/today.py,
src/portfolio.py, ...) takes a `lang` argument and calls `text(key, lang, ...)` instead, so it stays
testable without Streamlit. Placeholders use str.format: "{count} stocks".
"""

LANGS = {"en": "English", "th": "ไทย"}
DEFAULT = "en"

TEXT: dict[str, dict[str, str]] = {
    # ---------- app.py: navigation and sidebar ----------
    "app.page_title": {"en": "SET100 dashboard", "th": "แดชบอร์ด SET100"},
    "nav.today": {"en": "Today", "th": "วันนี้"},
    "nav.today_help": {"en": "Stocks in your portfolio and watchlist that may deserve a look today, and why.",
                       "th": "หุ้นในพอร์ตและรายการเฝ้าดูที่น่าดูวันนี้ พร้อมเหตุผล"},
    "nav.screener": {"en": "SET100 screener", "th": "คัดกรองหุ้น SET100"},
    "nav.screener_help": {"en": "All SET100 stocks in one table: price, valuation and quality. Sort, filter by "
                                "sector, and open any stock for details.",
                          "th": "หุ้น SET100 ทุกตัวในตารางเดียว: ราคา มูลค่า และคุณภาพ เรียงลำดับ กรองตามกลุ่ม "
                                "และเปิดดูรายละเอียดหุ้นแต่ละตัว"},
    "nav.stock": {"en": "Stock detail", "th": "รายละเอียดหุ้น"},
    "nav.stock_help": {"en": "One stock in depth: trading, chart with support/resistance, financials, valuation vs. "
                             "peers, dividends, and a prediction model.",
                       "th": "เจาะลึกหุ้นทีละตัว: การซื้อขาย กราฟพร้อมแนวรับแนวต้าน งบการเงิน มูลค่าเทียบคู่แข่ง "
                             "ปันผล และโมเดลทำนาย"},
    "nav.portfolio": {"en": "Portfolio", "th": "พอร์ต"},
    "nav.portfolio_help": {"en": "The stocks you own and your watchlist, saved on this Mac.",
                           "th": "หุ้นที่คุณถือและรายการเฝ้าดู บันทึกไว้ใน Mac เครื่องนี้"},
    "app.language": {"en": "Language", "th": "ภาษา"},
    "app.as_of": {"en": "Data as of **{when}** (local store). Stocks outside SET100 are fetched live.",
                  "th": "ข้อมูล ณ **{when}** (เก็บในเครื่อง) หุ้นนอก SET100 ดึงสดจากเน็ต"},
    "app.live": {"en": "Live data (no local store yet). Press Update data to save a copy for fast, offline use.",
                 "th": "ข้อมูลสด (ยังไม่มีข้อมูลเก็บในเครื่อง) กด อัปเดตข้อมูล เพื่อเก็บไว้ใช้เร็วขึ้นและใช้ได้ตอนไม่มีเน็ต"},
    "app.update": {"en": "Update data", "th": "อัปเดตข้อมูล"},
    "app.update_help": {"en": "Download today's data for all SET100 stocks into data/market.duckdb (about 1–2 "
                              "minutes). Same as running scripts/update_data.py.",
                        "th": "ดาวน์โหลดข้อมูลวันนี้ของหุ้น SET100 ทุกตัวเก็บไว้ที่ data/market.duckdb (ประมาณ 1–2 "
                              "นาที) เหมือนการรัน scripts/update_data.py"},
    "app.updating": {"en": "Downloading SET100 data...", "th": "กำลังดาวน์โหลดข้อมูล SET100..."},
    "app.update_failed": {"en": "Update failed", "th": "อัปเดตไม่สำเร็จ"},
    "app.update_skipped": {"en": "Skipped (old data kept): {symbols}", "th": "ข้ามไป (ใช้ข้อมูลเดิม): {symbols}"},
    "app.updated": {"en": "Updated {count} stocks.", "th": "อัปเดตแล้ว {count} ตัว"},
    "app.sources": {"en": "Data: Yahoo Finance (prices, delayed ~15 min) and thaifin (financial history). "
                          "For learning only — not investment advice.",
                    "th": "ข้อมูล: Yahoo Finance (ราคา ช้าประมาณ 15 นาที) และ thaifin (งบการเงินย้อนหลัง) "
                          "เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำการลงทุน"},

    # ---------- shared ----------
    "common.symbol": {"en": "Symbol", "th": "หุ้น"},
    "common.company": {"en": "Company", "th": "บริษัท"},
    "common.sector": {"en": "Sector", "th": "กลุ่มอุตสาหกรรม"},
    "common.price": {"en": "Price", "th": "ราคา"},
    "common.no_data": {"en": "No data", "th": "ไม่มีข้อมูล"},
    "common.list_expired_title": {"en": "SET100 list may be out of date", "th": "รายชื่อ SET100 อาจไม่เป็นปัจจุบัน"},
    "common.list_expired": {
        "en": "This SET100 list was valid until {end}. SET has likely published a new list, so some stocks may be "
              "missing or no longer in SET100. Update data/set100.csv (see README).",
        "th": "รายชื่อ SET100 นี้ใช้ได้ถึง {end} ตลาดหลักทรัพย์น่าจะประกาศรายชื่อใหม่แล้ว หุ้นบางตัวอาจขาดไปหรือไม่อยู่ใน "
              "SET100 แล้ว ให้อัปเดต data/set100.csv (ดู README)"},
    "common.retry": {"en": "Try again", "th": "ลองอีกครั้ง"},

    # ---------- Today ----------
    "today.title": {"en": "Today", "th": "วันนี้"},
    "today.caption": {"en": "Stocks in your portfolio and watchlist that may deserve a look today. "
                            "Signals, not advice — open a stock to check the full picture.",
                      "th": "หุ้นในพอร์ตและรายการเฝ้าดูที่อาจน่าดูวันนี้ เป็นสัญญาณ ไม่ใช่คำแนะนำ "
                            "เปิดดูหุ้นเพื่อดูภาพรวมทั้งหมด"},
    "today.empty_title": {"en": "Nothing to check yet", "th": "ยังไม่มีหุ้นให้ตรวจ"},
    "today.empty": {"en": "Your portfolio is empty. Open **Portfolio** in the sidebar, add the stocks you own "
                          "(or 0 shares to just watch one), and press Save.",
                    "th": "พอร์ตของคุณยังว่าง เปิด **พอร์ต** ที่แถบด้านข้าง เพิ่มหุ้นที่ถือ (หรือใส่ 0 หุ้นถ้าแค่อยากเฝ้าดู) "
                          "แล้วกด บันทึก"},
    "today.go_portfolio": {"en": "Go to Portfolio", "th": "ไปที่พอร์ต"},
    "today.checking": {"en": "Checking your stocks...", "th": "กำลังตรวจหุ้นของคุณ..."},
    "today.skipped_title": {"en": "Some stocks were skipped", "th": "ข้ามหุ้นบางตัว"},
    "today.skipped": {"en": "Could not load market data for {symbols}, so they were not checked. "
                            "Check the symbol, or try again in a minute.",
                      "th": "โหลดข้อมูลตลาดของ {symbols} ไม่ได้ จึงไม่ได้ตรวจ ตรวจสอบชื่อหุ้น หรือลองใหม่อีกครั้งในอีกสักครู่"},
    "today.none_title": {"en": "Nothing to look at today", "th": "วันนี้ไม่มีหุ้นที่ต้องดู"},
    "today.none": {"en": "None of your {count} stocks match a signal today.",
                   "th": "หุ้นทั้ง {count} ตัวของคุณไม่เข้าเงื่อนไขใดเลยวันนี้"},
    "today.count": {"en": "{flagged} of {checked} stocks to look at", "th": "หุ้นที่น่าดู {flagged} จาก {checked} ตัว"},
    "today.price": {"en": "**{symbol}** · {price} THB", "th": "**{symbol}** · {price} บาท"},
    "today.open": {"en": "Open {symbol}", "th": "เปิด {symbol}"},
    "today.legend_title": {"en": "What the signals mean", "th": "สัญญาณแต่ละข้อหมายถึงอะไร"},
    "today.legend": {
        "en": "- **Near support:** price is at most 3% above the nearest support level (a price where it turned up "
              "before).\n"
              "- **Broke resistance:** today's price is above the nearest resistance as of yesterday.\n"
              "- **RSI below 30 / above 70:** the price fell (rose) unusually fast — often called oversold "
              "(overbought).\n"
              "- **XD or earnings date within 14 days**, counting today as day 1. Yahoo often lacks Thai earnings "
              "dates.\n"
              "- **Cheap vs. its history:** current P/E is more than 20% below the median of its own yearly P/E.",
        "th": "- **ใกล้แนวรับ:** ราคาอยู่เหนือแนวรับที่ใกล้ที่สุดไม่เกิน 3% (ระดับราคาที่เคยเด้งขึ้น)\n"
              "- **ทะลุแนวต้าน:** ราคาวันนี้สูงกว่าแนวต้านที่ใกล้ที่สุดของเมื่อวาน\n"
              "- **RSI ต่ำกว่า 30 / สูงกว่า 70:** ราคาลง (ขึ้น) เร็วผิดปกติ มักเรียกว่าขายมากเกินไป (ซื้อมากเกินไป)\n"
              "- **วัน XD หรือวันประกาศงบภายใน 14 วัน** นับวันนี้เป็นวันที่ 1 Yahoo มักไม่มีวันประกาศงบของหุ้นไทย\n"
              "- **ถูกเมื่อเทียบกับอดีต:** P/E ปัจจุบันต่ำกว่าค่ากลาง P/E รายปีของตัวเองเกิน 20%"},
    # Reasons (src/today.py)
    "reason.near_support": {"en": "Near support: price {price:.2f} is {gap:.1%} above support {support:.2f}",
                            "th": "ใกล้แนวรับ: ราคา {price:.2f} อยู่เหนือแนวรับ {support:.2f} อยู่ {gap:.1%}"},
    "reason.broke_resistance": {"en": "Broke resistance: price {price:.2f} is above yesterday's resistance "
                                      "{resistance:.2f}",
                                "th": "ทะลุแนวต้าน: ราคา {price:.2f} สูงกว่าแนวต้านของเมื่อวาน {resistance:.2f}"},
    "reason.oversold": {"en": "RSI {rsi:.1f} — oversold (below {low})", "th": "RSI {rsi:.1f} — ขายมากเกินไป (ต่ำกว่า {low})"},
    "reason.overbought": {"en": "RSI {rsi:.1f} — overbought (above {high})",
                          "th": "RSI {rsi:.1f} — ซื้อมากเกินไป (สูงกว่า {high})"},
    "reason.xd": {"en": "XD date", "th": "วัน XD"},
    "reason.earnings": {"en": "Earnings date", "th": "วันประกาศงบ"},
    "reason.today": {"en": "today", "th": "วันนี้"},
    "reason.tomorrow": {"en": "tomorrow", "th": "พรุ่งนี้"},
    "reason.in_days": {"en": "in {days} days", "th": "อีก {days} วัน"},
    "reason.event": {"en": "{name} {when} ({date})", "th": "{name} {when} ({date})"},
    "reason.cheap": {"en": "Cheap vs. its history: P/E {pe:.1f} is {gap:.0%} below its median {median:.1f}",
                     "th": "ถูกเมื่อเทียบกับอดีต: P/E {pe:.1f} ต่ำกว่าค่ากลาง {median:.1f} อยู่ {gap:.0%}"},

    # ---------- Portfolio ----------
    "port.title": {"en": "Portfolio", "th": "พอร์ต"},
    "port.caption": {"en": "The stocks you own, plus a watchlist: enter 0 shares for a stock you only want to follow. "
                           "Saved on this Mac only (data/portfolio.csv, never committed to git).",
                     "th": "หุ้นที่คุณถือ และรายการเฝ้าดู: ใส่ 0 หุ้นสำหรับหุ้นที่แค่อยากติดตาม "
                           "บันทึกไว้ใน Mac เครื่องนี้เท่านั้น (data/portfolio.csv ไม่เคยถูก commit เข้า git)"},
    "port.public_title": {"en": "Demo", "th": "เดโม"},
    "port.public": {"en": "This is a public demo: your portfolio lives only in this browser tab and disappears when "
                          "you close it. Nothing is saved on the server.",
                    "th": "นี่คือเดโมสาธารณะ: พอร์ตของคุณอยู่แค่ในแท็บเบราว์เซอร์นี้ และจะหายไปเมื่อปิดแท็บ "
                          "ไม่มีอะไรถูกบันทึกบน server"},
    "port.empty_title": {"en": "Empty portfolio", "th": "พอร์ตว่าง"},
    "port.empty": {"en": "No stocks yet. Add them in the table below, then press Save.",
                   "th": "ยังไม่มีหุ้น เพิ่มหุ้นในตารางด้านล่าง แล้วกด บันทึก"},
    "port.value": {"en": "Market value (THB)", "th": "มูลค่าตลาด (บาท)"},
    "port.pnl": {"en": "Profit / loss (THB)", "th": "กำไร / ขาดทุน (บาท)"},
    "port.pnl_help": {"en": "Market value minus cost ({cost} THB).", "th": "มูลค่าตลาดลบต้นทุน ({cost} บาท)"},
    "port.dividend": {"en": "Estimated dividend / year (THB)", "th": "ปันผลคาดการณ์ / ปี (บาท)"},
    "port.dividend_help": {"en": "Dividend per share paid in {year} × shares you hold now.",
                           "th": "ปันผลต่อหุ้นที่จ่ายในปี {year} × จำนวนหุ้นที่ถืออยู่ตอนนี้"},
    "port.yoc": {"en": "Yield on cost", "th": "ผลตอบแทนปันผลเทียบต้นทุน"},
    "port.yoc_help": {"en": "Estimated dividend / what you paid.", "th": "ปันผลคาดการณ์ / เงินที่จ่ายซื้อ"},
    "port.missing_title": {"en": "Missing prices", "th": "ไม่มีราคา"},
    "port.missing": {"en": "No current price for {symbols}, so the totals leave them out. "
                           "Check the symbol, or try again in a minute.",
                     "th": "ไม่มีราคาปัจจุบันของ {symbols} จึงไม่ได้รวมในยอดรวม ตรวจสอบชื่อหุ้น หรือลองใหม่อีกครั้งในอีกสักครู่"},
    "port.shares": {"en": "Shares", "th": "จำนวนหุ้น"},
    "port.shares_help": {"en": "0 = watchlist.", "th": "0 = เฝ้าดูเท่านั้น"},
    "port.avg_cost": {"en": "Avg. cost", "th": "ต้นทุนเฉลี่ย"},
    "port.col_value": {"en": "Value (THB)", "th": "มูลค่า (บาท)"},
    "port.col_pnl": {"en": "P/L (THB)", "th": "กำไร/ขาดทุน (บาท)"},
    "port.col_pnl_pct": {"en": "P/L %", "th": "กำไร/ขาดทุน %"},
    "port.col_dividend": {"en": "Est. dividend (THB)", "th": "ปันผลคาดการณ์ (บาท)"},
    "port.col_dividend_help": {"en": "Dividend per share paid in {year} × shares.",
                               "th": "ปันผลต่อหุ้นที่จ่ายในปี {year} × จำนวนหุ้น"},
    "port.table_alt": {"en": "Holdings and watchlist with value, profit or loss, estimated dividend and yield on cost",
                       "th": "หุ้นที่ถือและรายการเฝ้าดู พร้อมมูลค่า กำไรขาดทุน ปันผลคาดการณ์ และผลตอบแทนปันผลเทียบต้นทุน"},
    "port.allocation": {"en": "Allocation by sector", "th": "สัดส่วนตามกลุ่มอุตสาหกรรม"},
    "port.alloc_series": {"en": "% of value", "th": "% ของมูลค่า"},
    "port.alloc_axis": {"en": "% of market value", "th": "% ของมูลค่าตลาด"},
    "port.alloc_alt": {"en": "Share of the portfolio's market value in each sector",
                       "th": "สัดส่วนมูลค่าตลาดของพอร์ตในแต่ละกลุ่มอุตสาหกรรม"},
    "port.note": {"en": "No trading fees, VAT or dividend tax are included. Estimated dividend uses the dividends per "
                        "share paid in {year} (the last complete year, by XD date); future dividends may differ. "
                        "Prices are delayed ~15 min.",
                  "th": "ไม่รวมค่าธรรมเนียม VAT หรือภาษีเงินปันผล ปันผลคาดการณ์ใช้ปันผลต่อหุ้นที่จ่ายในปี {year} "
                        "(ปีล่าสุดที่จบครบปี ตามวัน XD) ปันผลในอนาคตอาจต่างออกไป ราคาช้าประมาณ 15 นาที"},
    "port.edit": {"en": "Edit holdings", "th": "แก้ไขหุ้นที่ถือ"},
    "port.symbol_help": {"en": "SET symbol, e.g. PTT. Any Thai stock works.",
                         "th": "ชื่อย่อหุ้นใน SET เช่น PTT ใช้ได้กับหุ้นไทยทุกตัว"},
    "port.shares_edit_help": {"en": "0 = watchlist only.", "th": "0 = เฝ้าดูเท่านั้น"},
    "port.avg_cost_edit": {"en": "Average cost (THB)", "th": "ต้นทุนเฉลี่ย (บาท)"},
    "port.avg_cost_edit_help": {"en": "Average price paid per share. Leave empty for a watchlist stock.",
                                "th": "ราคาเฉลี่ยที่จ่ายต่อหุ้น เว้นว่างไว้ได้ถ้าเป็นหุ้นที่แค่เฝ้าดู"},
    "port.save": {"en": "Save", "th": "บันทึก"},
    "port.check_title": {"en": "Check your input", "th": "ตรวจสอบข้อมูลที่กรอก"},
    "port.not_saved": {"en": "Not saved. Please fix:", "th": "ยังไม่ได้บันทึก กรุณาแก้:"},
    "port.saved": {"en": "Saved {count} stocks.", "th": "บันทึกแล้ว {count} ตัว"},
    # Input problems (src/portfolio.py)
    "problem.empty_symbol": {"en": "Row {n}: the symbol is empty.", "th": "แถว {n}: ไม่ได้ใส่ชื่อหุ้น"},
    "problem.bad_symbol": {"en": "Row {n}: {symbol!r} is not a SET symbol (letters, digits and . & - only).",
                           "th": "แถว {n}: {symbol!r} ไม่ใช่ชื่อหุ้น SET (ใช้ได้แค่ตัวอักษร ตัวเลข และ . & -)"},
    "problem.empty_shares": {"en": "Row {n}: shares is empty (use 0 for a watchlist stock).",
                             "th": "แถว {n}: ไม่ได้ใส่จำนวนหุ้น (ใส่ 0 ถ้าแค่เฝ้าดู)"},
    "problem.negative_shares": {"en": "Row {n}: shares can't be negative.", "th": "แถว {n}: จำนวนหุ้นติดลบไม่ได้"},
    "problem.negative_cost": {"en": "Row {n}: average cost can't be negative.", "th": "แถว {n}: ต้นทุนเฉลี่ยติดลบไม่ได้"},
    "problem.empty_cost": {"en": "Row {n}: average cost is empty.", "th": "แถว {n}: ไม่ได้ใส่ต้นทุนเฉลี่ย"},
    "problem.duplicates": {"en": "Each stock can appear only once: {symbols}.",
                           "th": "หุ้นแต่ละตัวใส่ได้แค่ครั้งเดียว: {symbols}"},

    # ---------- Screener ----------
    "scr.title": {"en": "SET100 screener", "th": "คัดกรองหุ้น SET100"},
    "scr.caption": {"en": "SET100 constituents for {period}. Select a row to open the stock.",
                    "th": "รายชื่อหุ้น SET100 สำหรับช่วง {period} เลือกแถวเพื่อเปิดดูหุ้น"},
    "scr.sector_filter": {"en": "Sector", "th": "กลุ่มอุตสาหกรรม"},
    "scr.all_sectors": {"en": "All sectors", "th": "ทุกกลุ่ม"},
    "scr.set50_help": {"en": "Also in the SET50 index.", "th": "อยู่ในดัชนี SET50 ด้วย"},
    "scr.change": {"en": "Change", "th": "เปลี่ยนแปลง"},
    "scr.range52": {"en": "52-week range", "th": "ช่วงราคา 52 สัปดาห์"},
    "scr.range52_help": {"en": "Where the price sits between its 52-week low (0%) and high (100%).",
                         "th": "ราคาอยู่ตรงไหนระหว่างจุดต่ำสุด (0%) และสูงสุด (100%) ในรอบ 52 สัปดาห์"},
    "scr.value": {"en": "Value (THB)", "th": "มูลค่าซื้อขาย (บาท)"},
    "scr.value_help": {"en": "Today's traded value = price × volume.", "th": "มูลค่าซื้อขายวันนี้ = ราคา × ปริมาณ"},
    "scr.market_cap": {"en": "Market cap", "th": "มูลค่าตลาด"},
    "scr.pe_vs_sector": {"en": "P/E vs sector", "th": "P/E เทียบกลุ่ม"},
    "scr.pe_vs_sector_help": {"en": "Above 0% = more expensive than the sector median P/E.",
                              "th": "มากกว่า 0% = แพงกว่าค่ากลาง P/E ของกลุ่ม"},
    "scr.div_yield": {"en": "Div. yield", "th": "อัตราปันผล"},
    "scr.de_help": {"en": "Yahoo Finance: interest-bearing debt / shareholders' equity. Not reported for banks. "
                          "(The Financials tab may use thaifin's total liabilities / equity instead.)",
                    "th": "Yahoo Finance: หนี้ที่มีดอกเบี้ย / ส่วนของผู้ถือหุ้น ไม่มีสำหรับธนาคาร "
                          "(แท็บงบการเงินอาจใช้หนี้สินรวม / ส่วนของผู้ถือหุ้นจาก thaifin แทน)"},
    "scr.net_margin": {"en": "Net margin", "th": "อัตรากำไรสุทธิ"},
    "scr.rev_cagr": {"en": "5y revenue CAGR", "th": "รายได้โตเฉลี่ย 5 ปี"},
    "scr.rev_cagr_help": {"en": "Yearly revenue growth over the last 5 full years. Blank with fewer years of data or "
                                "a zero/negative start.",
                          "th": "อัตราการเติบโตของรายได้ต่อปีในช่วง 5 ปีเต็มล่าสุด เว้นว่างถ้ามีข้อมูลไม่ถึงหรือค่าเริ่มต้นเป็น 0 หรือติดลบ"},
    "scr.ni_cagr": {"en": "5y profit CAGR", "th": "กำไรโตเฉลี่ย 5 ปี"},
    "scr.ni_cagr_help": {"en": "Yearly net-income growth over the last 5 full years. Blank when either end is a loss.",
                         "th": "อัตราการเติบโตของกำไรสุทธิต่อปีในช่วง 5 ปีเต็มล่าสุด เว้นว่างถ้าปีต้นหรือปีท้ายขาดทุน"},
    "scr.roe_avg": {"en": "5y avg ROE", "th": "ROE เฉลี่ย 5 ปี"},
    "scr.roe_avg_help": {"en": "Average return on equity of the last 5 years.",
                         "th": "ผลตอบแทนต่อส่วนของผู้ถือหุ้นเฉลี่ย 5 ปีล่าสุด"},
    "scr.fscore_help": {"en": "Piotroski F-score: checks passed out of those with data (8 for most stocks; the current "
                              "ratio has no free data). Details on the stock's Fair value tab.",
                        "th": "Piotroski F-score: จำนวนข้อที่ผ่านจากข้อที่มีข้อมูล (หุ้นส่วนใหญ่มี 8 ข้อ เพราะไม่มีข้อมูล "
                              "current ratio ฟรี) ดูรายละเอียดที่แท็บมูลค่าที่เหมาะสมของหุ้นแต่ละตัว"},
    "scr.magic": {"en": "Magic Formula rank", "th": "อันดับ Magic Formula"},
    "scr.magic_help": {"en": "Greenblatt's Magic Formula across SET100: rank by earnings yield (1 / P/E) plus rank by "
                             "ROE, which stands in for return on capital. 1 = best. Blank for loss-making stocks.",
                       "th": "Magic Formula ของ Greenblatt ใน SET100: อันดับ earnings yield (1 / P/E) รวมกับอันดับ ROE "
                             "(ใช้แทนผลตอบแทนต่อเงินทุน) 1 = ดีที่สุด เว้นว่างสำหรับหุ้นที่ขาดทุน"},
    "scr.table_alt": {"en": "SET100 stocks with price, valuation and profitability metrics",
                      "th": "หุ้น SET100 พร้อมราคา มูลค่า และตัวชี้วัดความสามารถทำกำไร"},
    "scr.medians": {"en": "Sector medians", "th": "ค่ากลางของแต่ละกลุ่ม"},
    "scr.medians_alt": {"en": "Median valuation and ROE per sector within SET100",
                        "th": "ค่ากลางมูลค่าและ ROE ของแต่ละกลุ่มใน SET100"},
    "scr.medians_note": {"en": "Some sectors have only one or two SET100 members, so their median is just those stocks.",
                         "th": "บางกลุ่มมีหุ้นใน SET100 แค่ 1–2 ตัว ค่ากลางจึงเป็นของหุ้นเหล่านั้นเท่านั้น"},

    # ---------- Stock page ----------
    "stock.select": {"en": "Stock", "th": "หุ้น"},
    "stock.select_help": {"en": "Pick a SET100 stock, or type any SET symbol and press Enter.",
                          "th": "เลือกหุ้น SET100 หรือพิมพ์ชื่อหุ้น SET ตัวไหนก็ได้แล้วกด Enter"},
    "stock.invalid_title": {"en": "Not a valid symbol", "th": "ชื่อหุ้นไม่ถูกต้อง"},
    "stock.invalid": {"en": "A SET symbol has only letters, digits and . & - (up to 15 characters), e.g. PTT.",
                      "th": "ชื่อหุ้น SET มีได้แค่ตัวอักษร ตัวเลข และ . & - (ไม่เกิน 15 ตัว) เช่น PTT"},
    "stock.set_links": {"en": "See on the SET website", "th": "ดูที่เว็บ SET"},
    "stock.set_links_caption": {"en": "For what has no free data feed: money flows, shareholders, warning signs, "
                                      "XR dates and news.",
                                "th": "สำหรับข้อมูลที่ไม่มีแหล่งฟรี: เงินไหลเข้าออก ผู้ถือหุ้น สัญญาณเตือน วัน XR และข่าว"},
    "stock.all_stocks": {"en": " — all stocks, look up {symbol}", "th": " — หุ้นทุกตัว ค้นหา {symbol}"},
    "tab.trading": {"en": ":material/swap_vert: Trading", "th": ":material/swap_vert: การซื้อขาย"},
    "tab.chart": {"en": ":material/candlestick_chart: Chart", "th": ":material/candlestick_chart: กราฟ"},
    "tab.financials": {"en": ":material/account_balance: Financials", "th": ":material/account_balance: งบการเงิน"},
    "tab.valuation": {"en": ":material/sell: Valuation", "th": ":material/sell: มูลค่า"},
    "tab.dividends": {"en": ":material/event: Dividends & calendar", "th": ":material/event: ปันผลและปฏิทิน"},
    "tab.fair": {"en": ":material/balance: Fair value", "th": ":material/balance: มูลค่าที่เหมาะสม"},
    "tab.prediction": {"en": ":material/online_prediction: Prediction", "th": ":material/online_prediction: ทำนาย"},
    # Trading
    "trade.volume": {"en": "Volume", "th": "ปริมาณซื้อขาย"},
    "trade.vol_ratio": {"en": "{ratio:.1f}× avg", "th": "{ratio:.1f}× ค่าเฉลี่ย"},
    "trade.volume_help": {"en": "Today's volume compared with the 3-month average volume.",
                          "th": "ปริมาณวันนี้เทียบกับปริมาณเฉลี่ย 3 เดือน"},
    "trade.value": {"en": "Value traded (THB)", "th": "มูลค่าซื้อขาย (บาท)"},
    "trade.market_cap": {"en": "Market cap (THB)", "th": "มูลค่าตลาด (บาท)"},
    "trade.bid_offer": {"en": "Bid / Offer", "th": "เสนอซื้อ / เสนอขาย"},
    "trade.bid_offer_help": {"en": "Best bid and offer only (delayed). Full market depth needs a broker feed.",
                             "th": "เฉพาะราคาเสนอซื้อขายที่ดีที่สุด (ล่าช้า) ถ้าต้องการทุกระดับราคาต้องใช้ข้อมูลจากโบรกเกอร์"},
    "trade.high52": {"en": "52-week high", "th": "สูงสุด 52 สัปดาห์"},
    "trade.low52": {"en": "52-week low", "th": "ต่ำสุด 52 สัปดาห์"},
    "trade.pos52": {"en": "Position in 52-week range", "th": "ตำแหน่งในช่วง 52 สัปดาห์"},
    "trade.pos52_help": {"en": "0% = at the 52-week low, 100% = at the 52-week high.",
                         "th": "0% = อยู่ที่จุดต่ำสุด 52 สัปดาห์, 100% = อยู่ที่จุดสูงสุด 52 สัปดาห์"},
    "trade.free_float": {"en": "Free float (Yahoo estimate)", "th": "Free float (ประมาณการของ Yahoo)"},
    "trade.free_float_help": {"en": "Share of shares not held by insiders or major holders, as estimated by Yahoo. "
                                    "SET's official figure is under 'Major shareholders and free float' on the SET "
                                    "website.",
                              "th": "สัดส่วนหุ้นที่ไม่ได้ถือโดยผู้บริหารหรือผู้ถือหุ้นใหญ่ ตามที่ Yahoo ประมาณ "
                                    "ตัวเลขทางการของ SET อยู่ที่ 'ผู้ถือหุ้นใหญ่และ free float' บนเว็บ SET"},
    "trade.high_activity_title": {"en": "High activity", "th": "ซื้อขายคึกคัก"},
    "trade.high_activity": {"en": "Volume today is {ratio:.1f}× the average — unusual interest.",
                            "th": "ปริมาณวันนี้สูงเป็น {ratio:.1f} เท่าของค่าเฉลี่ย — ตลาดสนใจผิดปกติ"},
    # Chart
    "chart.period": {"en": "Period", "th": "ช่วงเวลา"},
    "chart.no_prices": {"en": "No price data", "th": "ไม่มีข้อมูลราคา"},
    "chart.alt": {"en": "{symbol} candlestick chart with SMA20/50, support and resistance lines, volume and RSI",
                  "th": "กราฟแท่งเทียนของ {symbol} พร้อม SMA20/50 เส้นแนวรับแนวต้าน ปริมาณซื้อขาย และ RSI"},
    "chart.note": {"en": "Prices are adjusted for dividends and splits. S = support, R = resistance: price levels where "
                         "the stock turned around before (swing highs/lows within ±10 days, merged when within 2%).",
                   "th": "ราคาปรับปันผลและการแตกพาร์แล้ว S = แนวรับ, R = แนวต้าน: ระดับราคาที่หุ้นเคยกลับตัว "
                         "(จุดสูงสุด/ต่ำสุดในช่วง ±10 วัน รวมเป็นระดับเดียวถ้าห่างกันไม่เกิน 2%)"},
    "chart.price_axis": {"en": "Price (THB)", "th": "ราคา (บาท)"},
    "chart.volume": {"en": "Volume", "th": "ปริมาณ"},
    # Financials
    "fin.none": {"en": "No financial statements found for this stock.", "th": "ไม่พบงบการเงินของหุ้นตัวนี้"},
    "fin.short_title": {"en": "Shorter history than usual", "th": "ข้อมูลย้อนหลังสั้นกว่าปกติ"},
    "fin.caption": {"en": "Annual figures {first}–{last} ({years} years). Source: {source}.",
                    "th": "ตัวเลขรายปี {first}–{last} ({years} ปี) แหล่งข้อมูล: {source}"},
    "fin.Revenue": {"en": "Revenue", "th": "รายได้"},
    "fin.Net income": {"en": "Net income", "th": "กำไรสุทธิ"},
    "fin.EPS": {"en": "EPS", "th": "กำไรต่อหุ้น (EPS)"},
    "fin.Revenue growth": {"en": "Revenue growth", "th": "การเติบโตของรายได้"},
    "fin.Net income growth": {"en": "Net income growth", "th": "การเติบโตของกำไรสุทธิ"},
    "fin.Gross margin": {"en": "Gross margin", "th": "อัตรากำไรขั้นต้น"},
    "fin.Net margin": {"en": "Net margin", "th": "อัตรากำไรสุทธิ"},
    "fin.ROE": {"en": "ROE", "th": "ROE"},
    "fin.D/E": {"en": "D/E", "th": "D/E"},
    "fin.Free cash flow": {"en": "Free cash flow", "th": "กระแสเงินสดอิสระ"},
    "fin.de_help": {"en": "{definition}. Banks and finance companies naturally carry much higher leverage.",
                    "th": "{definition} ธนาคารและบริษัทการเงินมีหนี้สูงกว่าปกติตามธรรมชาติของธุรกิจ"},
    "fin.de_default": {"en": "Debt / equity", "th": "หนี้สิน / ส่วนของผู้ถือหุ้น"},
    "fin.fcf_help": {"en": "Cash from operations minus investment spending.", "th": "เงินสดจากการดำเนินงานลบเงินลงทุน"},
    "fin.rev_ni": {"en": "Revenue and net income", "th": "รายได้และกำไรสุทธิ"},
    "fin.billion": {"en": "THB billion", "th": "พันล้านบาท"},
    "fin.rev_ni_alt": {"en": "{symbol} yearly revenue and net income", "th": "รายได้และกำไรสุทธิรายปีของ {symbol}"},
    "fin.margins": {"en": "Margins and ROE", "th": "อัตรากำไรและ ROE"},
    "fin.margins_alt": {"en": "{symbol} gross margin, net margin and ROE by year",
                        "th": "อัตรากำไรขั้นต้น อัตรากำไรสุทธิ และ ROE รายปีของ {symbol}"},
    "fin.fcf_alt": {"en": "{symbol} yearly free cash flow", "th": "กระแสเงินสดอิสระรายปีของ {symbol}"},
    "fin.fcf_banks": {"en": "For banks, lenders and insurers, lending and investing are the business itself, so free "
                            "cash flow swings widely and is not a useful health measure.",
                      "th": "สำหรับธนาคาร บริษัทสินเชื่อ และประกัน การปล่อยกู้และการลงทุนคือธุรกิจหลัก "
                            "กระแสเงินสดอิสระจึงแกว่งมากและไม่เหมาะใช้วัดความแข็งแรง"},
    "fin.table_alt": {"en": "{symbol} yearly financial figures", "th": "ตัวเลขทางการเงินรายปีของ {symbol}"},
    # Valuation
    "val.vs_peers": {"en": "Compared with the median of SET100 stocks in {sector}.",
                     "th": "เทียบกับค่ากลางของหุ้น SET100 ในกลุ่ม {sector}"},
    "val.no_peers": {"en": "Stocks outside SET100 have no sector comparison.",
                     "th": "หุ้นนอก SET100 ไม่มีการเทียบกับกลุ่ม"},
    "val.vs_sector": {"en": "{diff:+.0%} vs sector", "th": "{diff:+.0%} เทียบกลุ่ม"},
    "val.sector_median": {"en": "Sector median: {value}", "th": "ค่ากลางของกลุ่ม: {value}"},
    "val.div_yield": {"en": "Dividend yield", "th": "อัตราปันผล"},
    "val.colors": {"en": "Red = more expensive (or lower yield) than sector peers; green = cheaper.",
                   "th": "แดง = แพงกว่า (หรือปันผลต่ำกว่า) หุ้นในกลุ่มเดียวกัน, เขียว = ถูกกว่า"},
    "val.history": {"en": "Compared with its own history", "th": "เทียบกับอดีตของตัวเอง"},
    "val.metric": {"en": "Metric", "th": "ตัวชี้วัด"},
    "val.metric_yield": {"en": "Dividend yield", "th": "อัตราปันผล"},
    "val.no_history_title": {"en": "No history", "th": "ไม่มีข้อมูลย้อนหลัง"},
    "val.no_history": {"en": "Not enough yearly {metric} history for this stock.",
                       "th": "ข้อมูล {metric} รายปีของหุ้นตัวนี้ไม่พอ"},
    "val.yield_series": {"en": "Dividend yield (%)", "th": "อัตราปันผล (%)"},
    "val.median_series": {"en": "{years}-year median", "th": "ค่ากลาง {years} ปี"},
    "val.yield_alt": {"en": "{symbol} yearly dividend yield compared with its median",
                      "th": "อัตราปันผลรายปีของ {symbol} เทียบกับค่ากลาง"},
    "val.cheaper": {"en": "cheaper", "th": "ถูกกว่า"},
    "val.dearer": {"en": "more expensive", "th": "แพงกว่า"},
    "val.yield_verdict": {"en": "Current dividend yield **{current}** is **{pp:+.1f} pp** vs. its {years}-year median of "
                                "{median} — {verdict} than usual.",
                          "th": "อัตราปันผลปัจจุบัน **{current}** ต่างจากค่ากลาง {years} ปี ({median}) อยู่ "
                                "**{pp:+.1f} pp** — {verdict}ปกติ"},
    "val.yield_note": {"en": "Yearly yield = dividends per share with XD dates in that year ÷ the year's last close as "
                             "traded (not adjusted for dividends). A year without dividends counts as 0%. pp = "
                             "percentage points. Current value: Yahoo (trailing 12 months).",
                       "th": "อัตราปันผลรายปี = ปันผลต่อหุ้นที่วัน XD อยู่ในปีนั้น ÷ ราคาปิดวันสุดท้ายของปี (ไม่ปรับปันผล) "
                             "ปีที่ไม่จ่ายปันผลนับเป็น 0% pp = จุดเปอร์เซ็นต์ ค่าปัจจุบัน: Yahoo (12 เดือนล่าสุด)"},
    "val.history_alt": {"en": "{symbol} year-end {metric} by year compared with its median",
                        "th": "{metric} ณ สิ้นปีของ {symbol} รายปีเทียบกับค่ากลาง"},
    "val.below": {"en": "below", "th": "ต่ำกว่า"},
    "val.above": {"en": "above", "th": "สูงกว่า"},
    "val.verdict": {"en": "Current {metric} **{current}** is **{diff:.0%} {direction}** its {years}-year median of "
                          "{median} — {verdict} than usual.",
                    "th": "{metric} ปัจจุบัน **{current}** **{direction}ค่ากลาง {years} ปี ({median}) อยู่ {diff:.0%}** "
                          "— {verdict}ปกติ"},
    "val.history_note": {"en": "Median is used instead of average so one unusual year (e.g. a loss year) doesn't "
                               "distort it. Current value: Yahoo (trailing 12 months); history: {source} (year-end), "
                               "so the two can differ slightly.",
                         "th": "ใช้ค่ากลางแทนค่าเฉลี่ย เพื่อไม่ให้ปีที่ผิดปกติ (เช่น ปีที่ขาดทุน) ทำให้ผลเพี้ยน "
                               "ค่าปัจจุบัน: Yahoo (12 เดือนล่าสุด) ข้อมูลย้อนหลัง: {source} (สิ้นปี) จึงอาจต่างกันเล็กน้อย"},
    # Dividends & calendar
    "div.xd": {"en": "Next / last XD date", "th": "วัน XD ถัดไป / ล่าสุด"},
    "div.earnings": {"en": "Next earnings date", "th": "วันประกาศงบถัดไป"},
    "div.earnings_help": {"en": "From Yahoo; often missing for Thai stocks. Check SET announcements to be sure.",
                          "th": "จาก Yahoo มักไม่มีสำหรับหุ้นไทย ควรตรวจกับประกาศของ SET"},
    "div.none_title": {"en": "No dividends", "th": "ไม่มีปันผล"},
    "div.none": {"en": "No dividend history on Yahoo Finance.", "th": "ไม่มีประวัติปันผลใน Yahoo Finance"},
    "div.per_year": {"en": "Dividend per share by year (THB)", "th": "ปันผลต่อหุ้นรายปี (บาท)"},
    "div.alt": {"en": "{symbol} dividend per share by year", "th": "ปันผลต่อหุ้นรายปีของ {symbol}"},
    "div.note": {"en": "Grouped by XD date. The current year may be incomplete.",
                 "th": "จัดกลุ่มตามวัน XD ปีปัจจุบันอาจยังไม่ครบ"},
    # Fair value
    "fair.no_value_title": {"en": "No meaningful value", "th": "ไม่มีค่าที่มีความหมาย"},
    "fair.no_value": {"en": "The {model} result is zero or negative: with these assumptions, net debt is larger than the "
                            "value of the future cash flows. The model says little about this stock.",
                      "th": "ผลของ {model} เป็นศูนย์หรือติดลบ: ด้วยสมมติฐานนี้ หนี้สุทธิสูงกว่ามูลค่ากระแสเงินสดในอนาคต "
                            "โมเดลนี้จึงบอกอะไรเกี่ยวกับหุ้นตัวนี้ได้น้อย"},
    "fair.value": {"en": "Fair value ({model})", "th": "มูลค่าที่เหมาะสม ({model})"},
    "fair.price_now": {"en": "Price now", "th": "ราคาตอนนี้"},
    "fair.margin": {"en": "Margin of safety", "th": "ส่วนเผื่อความปลอดภัย"},
    "fair.margin_help": {"en": "How far the fair value is above (+) or below (−) today's price.",
                         "th": "มูลค่าที่เหมาะสมสูงกว่า (+) หรือต่ำกว่า (−) ราคาวันนี้เท่าไร"},
    "fair.estimate_title": {"en": "Estimate only", "th": "เป็นเพียงการประมาณ"},
    "fair.estimate": {"en": "An estimate based on your assumptions — not investment advice. Small changes in the "
                            "assumptions move the result a lot; see the tables.",
                      "th": "เป็นการประมาณจากสมมติฐานของคุณ ไม่ใช่คำแนะนำการลงทุน สมมติฐานที่เปลี่ยนเล็กน้อยทำให้ผลเปลี่ยนมาก "
                            "ดูได้จากตาราง"},
    "fair.ddm": {"en": "Dividend discount model (DDM)", "th": "แบบจำลองคิดลดเงินปันผล (DDM)"},
    "fair.no_dividend_title": {"en": "No dividend", "th": "ไม่มีปันผล"},
    "fair.no_dividend": {"en": "{symbol} paid no dividend in {year}, so the dividend model can't value it.",
                         "th": "{symbol} ไม่ได้จ่ายปันผลในปี {year} จึงใช้แบบจำลองปันผลประเมินไม่ได้"},
    "fair.ddm_g": {"en": "Dividend growth per year", "th": "การเติบโตของปันผลต่อปี"},
    "fair.ddm_g_help": {"en": "Growth forever. Default: growth of dividends per share over the last 5 full years, "
                              "at most 6% (it must stay below the required return).",
                        "th": "การเติบโตตลอดไป ค่าเริ่มต้น: การเติบโตของปันผลต่อหุ้นใน 5 ปีเต็มล่าสุด ไม่เกิน 6% "
                              "(ต้องต่ำกว่าผลตอบแทนที่ต้องการ)"},
    "fair.ddm_r": {"en": "Required return", "th": "ผลตอบแทนที่ต้องการ"},
    "fair.ddm_r_help": {"en": "The yearly return you want for the risk. Default 8%.",
                        "th": "ผลตอบแทนต่อปีที่คุณต้องการสำหรับความเสี่ยงนี้ ค่าเริ่มต้น 8%"},
    "fair.ddm_note": {"en": "Dividend per share paid in {year}: {dps} THB → next year {next} THB at {g:.1%} growth.",
                      "th": "ปันผลต่อหุ้นที่จ่ายในปี {year}: {dps} บาท → ปีหน้า {next} บาท ที่การเติบโต {g:.1%}"},
    "fair.cant": {"en": "Can't compute", "th": "คำนวณไม่ได้"},
    "fair.ddm_alt": {"en": "{symbol} DDM fair value for required return and growth ±1 point",
                     "th": "มูลค่าที่เหมาะสมแบบ DDM ของ {symbol} เมื่อผลตอบแทนที่ต้องการและการเติบโตเปลี่ยน ±1 จุด"},
    "fair.dcf": {"en": "Discounted cash flow (DCF)", "th": "แบบจำลองคิดลดกระแสเงินสด (DCF)"},
    "fair.no_dcf_title": {"en": "DCF not shown", "th": "ไม่แสดง DCF"},
    "fair.no_dcf": {"en": "Not used for banks, lenders and insurers: lending and investing are their business, so their "
                          "free cash flow says little about their value. Use the dividend model above.",
                    "th": "ไม่ใช้กับธนาคาร บริษัทสินเชื่อ และประกัน เพราะการปล่อยกู้และการลงทุนคือธุรกิจหลัก "
                          "กระแสเงินสดอิสระจึงบอกมูลค่าได้น้อย ใช้แบบจำลองปันผลด้านบนแทน"},
    "fair.not_enough_title": {"en": "Not enough data", "th": "ข้อมูลไม่พอ"},
    "fair.not_enough": {"en": "Needs a positive free cash flow and the number of shares for the last year.",
                        "th": "ต้องมีกระแสเงินสดอิสระเป็นบวกและจำนวนหุ้นของปีล่าสุด"},
    "fair.dcf_g": {"en": "Cash-flow growth, next 5 years", "th": "การเติบโตของกระแสเงินสด 5 ปีข้างหน้า"},
    "fair.dcf_g_help": {"en": "Default: revenue growth over the last 5 years, between 0% and 10%.",
                        "th": "ค่าเริ่มต้น: การเติบโตของรายได้ 5 ปีล่าสุด อยู่ระหว่าง 0% ถึง 10%"},
    "fair.dcf_tg": {"en": "Growth after that", "th": "การเติบโตหลังจากนั้น"},
    "fair.dcf_tg_help": {"en": "Long-run growth forever. Default 2%.", "th": "การเติบโตระยะยาวตลอดไป ค่าเริ่มต้น 2%"},
    "fair.dcf_r": {"en": "Discount rate", "th": "อัตราคิดลด"},
    "fair.dcf_r_help": {"en": "The yearly return you want. Default 9%.", "th": "ผลตอบแทนต่อปีที่คุณต้องการ ค่าเริ่มต้น 9%"},
    "fair.dcf_note": {"en": "Free cash flow {year}: {fcf} THB; net debt {net_debt} THB; shares {shares}.",
                      "th": "กระแสเงินสดอิสระปี {year}: {fcf} บาท; หนี้สุทธิ {net_debt} บาท; จำนวนหุ้น {shares}"},
    "fair.dcf_alt": {"en": "{symbol} DCF fair value for discount rate and growth ±1 point",
                     "th": "มูลค่าที่เหมาะสมแบบ DCF ของ {symbol} เมื่ออัตราคิดลดและการเติบโตเปลี่ยน ±1 จุด"},
    "fair.fscore": {"en": "Piotroski F-score", "th": "Piotroski F-score"},
    "fair.no_scores": {"en": "No yearly financials to score.", "th": "ไม่มีงบการเงินรายปีให้คำนวณคะแนน"},
    "fair.fscore_help": {"en": "One point per check passed (last year vs. the year before). Checks without free data "
                               "are left out, so the maximum is the number available.",
                         "th": "ได้ 1 คะแนนต่อข้อที่ผ่าน (ปีล่าสุดเทียบกับปีก่อน) ข้อที่ไม่มีข้อมูลฟรีจะไม่นับ "
                               "คะแนนเต็มจึงเท่ากับจำนวนข้อที่มีข้อมูล"},
    "fair.no_check_data": {"en": " (no data)", "th": " (ไม่มีข้อมูล)"},
    "check.Positive ROA": {"en": "Positive ROA", "th": "ROA เป็นบวก"},
    "check.Positive operating cash flow": {"en": "Positive operating cash flow",
                                           "th": "กระแสเงินสดจากการดำเนินงานเป็นบวก"},
    "check.ROA improved": {"en": "ROA improved", "th": "ROA ดีขึ้น"},
    "check.Cash flow above profit": {"en": "Cash flow above profit", "th": "กระแสเงินสดสูงกว่ากำไร"},
    "check.Lower debt / assets": {"en": "Lower debt / assets", "th": "หนี้สิน / สินทรัพย์ลดลง"},
    "check.Higher current ratio": {"en": "Higher current ratio", "th": "Current ratio สูงขึ้น"},
    "check.No new shares": {"en": "No new shares", "th": "ไม่ได้ออกหุ้นใหม่"},
    "check.Higher gross margin": {"en": "Higher gross margin", "th": "อัตรากำไรขั้นต้นสูงขึ้น"},
    "check.Higher asset turnover": {"en": "Higher asset turnover", "th": "อัตราหมุนเวียนสินทรัพย์สูงขึ้น"},
    # Prediction
    "pred.intro": {"en": "A Random Forest model predicts whether **tomorrow's close will be higher than today's**. "
                         "Walk-forward test: the newest 40% of 5 years is split into 4 periods; each period is "
                         "predicted by a model trained only on the days before it (with a 1-day gap), as if it were "
                         "run live.",
                   "th": "โมเดล Random Forest ทำนายว่า **ราคาปิดพรุ่งนี้จะสูงกว่าวันนี้หรือไม่** "
                         "ทดสอบแบบ walk-forward: แบ่งข้อมูล 40% ล่าสุดของ 5 ปีเป็น 4 ช่วง แต่ละช่วงทำนายด้วยโมเดลที่เทรน"
                         "จากข้อมูลก่อนหน้าเท่านั้น (เว้น 1 วัน) เหมือนใช้งานจริง"},
    "pred.training": {"en": "Training model...", "th": "กำลังเทรนโมเดล..."},
    "pred.cant_title": {"en": "Can't train the model", "th": "เทรนโมเดลไม่ได้"},
    "pred.accuracy": {"en": "Model accuracy (4 periods)", "th": "ความแม่นยำของโมเดล (4 ช่วง)"},
    "pred.baseline": {"en": "Baseline accuracy", "th": "ความแม่นยำพื้นฐาน"},
    "pred.baseline_help": {"en": "Always guessing the most common direction. The model is only useful if it beats this.",
                           "th": "ทายทิศทางที่เกิดบ่อยที่สุดทุกครั้ง โมเดลมีประโยชน์ก็ต่อเมื่อชนะค่านี้"},
    "pred.next_day": {"en": "Next day: chance of going up", "th": "วันถัดไป: โอกาสขึ้น"},
    "pred.edge_title": {"en": "The model has an edge", "th": "โมเดลมีความได้เปรียบ"},
    "pred.edge": {"en": "The model is {edge:+.1%} more accurate than the baseline on unseen data.",
                  "th": "โมเดลแม่นกว่าค่าพื้นฐาน {edge:+.1%} บนข้อมูลที่ไม่เคยเห็น"},
    "pred.no_edge_title": {"en": "No real edge", "th": "ไม่มีความได้เปรียบจริง"},
    "pred.no_edge": {"en": "The model is {edge:+.1%} vs. the baseline. This is normal: daily stock moves are very close "
                           "to random.",
                     "th": "โมเดลต่างจากค่าพื้นฐาน {edge:+.1%} เป็นเรื่องปกติ เพราะการขึ้นลงรายวันของหุ้นใกล้เคียงการสุ่มมาก"},
    "pred.periods": {"en": "Accuracy in each test period", "th": "ความแม่นยำในแต่ละช่วงทดสอบ"},
    "pred.col_period": {"en": "Period", "th": "ช่วงเวลา"},
    "pred.col_model": {"en": "Model", "th": "โมเดล"},
    "pred.col_baseline": {"en": "Baseline", "th": "ค่าพื้นฐาน"},
    "pred.col_edge": {"en": "Model − baseline", "th": "โมเดล − ค่าพื้นฐาน"},
    "pred.periods_alt": {"en": "{symbol} model and baseline accuracy in each walk-forward test period",
                         "th": "ความแม่นยำของโมเดลและค่าพื้นฐานของ {symbol} ในแต่ละช่วงทดสอบ"},
    "pred.average": {"en": "Average over the {count} periods: model {model:.1%}, baseline {baseline:.1%}.",
                     "th": "ค่าเฉลี่ย {count} ช่วง: โมเดล {model:.1%}, ค่าพื้นฐาน {baseline:.1%}"},
    "pred.backtest": {"en": "Backtest: 1 baht invested over the test periods",
                      "th": "ทดสอบย้อนหลัง: ลงทุน 1 บาทตลอดช่วงทดสอบ"},
    "pred.buy_hold": {"en": "Buy & hold", "th": "ซื้อแล้วถือ"},
    "pred.after_costs": {"en": "Model strategy (after costs)", "th": "กลยุทธ์โมเดล (หลังหักค่าธรรมเนียม)"},
    "pred.before_costs": {"en": "Model strategy (before costs)", "th": "กลยุทธ์โมเดล (ก่อนหักค่าธรรมเนียม)"},
    "pred.value_axis": {"en": "Value of 1 baht", "th": "มูลค่าของ 1 บาท"},
    "pred.backtest_alt": {"en": "Growth of 1 baht in {symbol}: buy and hold versus holding only on days the model "
                                "predicts up",
                          "th": "การเติบโตของ 1 บาทใน {symbol}: ซื้อแล้วถือ เทียบกับถือเฉพาะวันที่โมเดลทายว่าขึ้น"},
    "pred.note": {"en": "Model strategy = hold only on days the model predicts 'up' ({share:.0%} of test days), paying "
                        "{cost:.2%} per buy or sell ({trades} trades). Buy & hold pays almost nothing. Taxes are "
                        "ignored.",
                  "th": "กลยุทธ์โมเดล = ถือเฉพาะวันที่โมเดลทายว่า 'ขึ้น' ({share:.0%} ของวันทดสอบ) เสียค่าธรรมเนียม "
                        "{cost:.2%} ต่อการซื้อหรือขายแต่ละครั้ง ({trades} ครั้ง) ซื้อแล้วถือแทบไม่เสียค่าธรรมเนียม ไม่คิดภาษี"},
    "pred.features": {"en": "Which features the model relied on", "th": "โมเดลพึ่งตัวแปรไหน"},
    "pred.features_alt": {"en": "Feature importance of the Random Forest model",
                          "th": "ความสำคัญของตัวแปรในโมเดล Random Forest"},

    # ---------- SET website links (src/set_links.py) ----------
    "link.price": {"en": "Price and trading signs", "th": "ราคาและเครื่องหมายการซื้อขาย"},
    "link.shareholders": {"en": "Major shareholders and free float", "th": "ผู้ถือหุ้นใหญ่และ free float"},
    "link.rights": {"en": "Rights & benefits (XD, XR)", "th": "สิทธิประโยชน์ (XD, XR)"},
    "link.news": {"en": "News", "th": "ข่าว"},
    "link.investor_types": {"en": "Investor types", "th": "ประเภทนักลงทุน"},
    "link.nvdr": {"en": "NVDR", "th": "NVDR"},
    "link.short_sales": {"en": "Short sales", "th": "การขายชอร์ต"},
    "link.c_sign": {"en": "Caution signs (C)", "th": "เครื่องหมายเตือน (C)"},
    "link.surveillance": {"en": "Cash balance and turnover list", "th": "Cash balance และ turnover list"},
    "link.auto_pause": {"en": "Auto Pause", "th": "Auto Pause"},
    "link.form59": {"en": "Form 59 (executives' trades, SEC website)",
                    "th": "แบบ 59 (การซื้อขายของผู้บริหาร เว็บ ก.ล.ต.)"},
}


def text(key: str, lang: str = DEFAULT, **values) -> str:
    """The text for `key` in `lang` (falls back to English for an unknown language), filled with `values`."""
    entry = TEXT[key]
    return entry.get(lang, entry[DEFAULT]).format(**values)


def current_lang() -> str:
    """The language chosen in the sidebar (kept in the URL as ?lang=th); English by default."""
    import streamlit as st

    lang = st.session_state.get("lang_choice") or st.query_params.get("lang", DEFAULT)
    return lang if lang in LANGS else DEFAULT


def t(key: str, **values) -> str:
    """The text for `key` in the current language. Use in pages."""
    return text(key, current_lang(), **values)
