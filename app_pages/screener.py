from datetime import date

import streamlit as st

from src import cache
from src.fundamentals import SnapshotError, sector_medians
from src.scoring import magic_formula_rank
from src.screener import selected_symbol
from src.universe import SET100_PERIOD, set100_expiry_warning

st.title("SET100 screener")
st.caption(f"SET100 constituents for {SET100_PERIOD}. Select a row to open the stock.")
if expiry_warning := set100_expiry_warning(date.today()):
    st.warning(expiry_warning, title="SET100 list may be out of date")

universe = cache.set100()
sectors = sorted(universe["sector"].unique())
picked = st.multiselect("Sector", sectors, placeholder="All sectors", key="sectors")

table_slot = st.container()
with table_slot.skeleton():
    try:
        snaps = cache.snapshots()
    except SnapshotError as e:
        table_slot.error(str(e), title=SnapshotError.title)
        table_slot.button("Try again", icon=":material/refresh:", key="retry")
        st.stop()

    medians = sector_medians(snaps, universe)
    df = universe.merge(snaps, on="symbol").merge(cache.growth(), on="symbol", how="left")
    # How expensive vs. sector peers: +0.20 = P/E 20% above the sector median.
    df["pe_vs_sector"] = df["pe"] / df["sector"].map(medians["pe"]) - 1
    df["magic_rank"] = magic_formula_rank(df)  # ranked across all SET100, before the sector filter
    if picked:
        df = df[df["sector"].isin(picked)]
    shown = df.sort_values("market_cap", ascending=False)  # the exact rows, in the exact order, on screen

    nc = st.column_config.NumberColumn
    event = table_slot.dataframe(
        shown,
        hide_index=True,
        key="screener",
        on_select="rerun",
        selection_mode="single-row",
        height=640,
        column_order=["symbol", "name", "sector", "in_set50", "price", "change_pct", "pos_52w", "value_traded", "market_cap",
                      "pe", "pe_vs_sector", "pbv", "div_yield", "roe", "de", "net_margin",
                      "rev_cagr5", "ni_cagr5", "roe_avg5", "fscore", "magic_rank"],
        column_config={
            "symbol": st.column_config.TextColumn("Symbol", pinned=True),
            "name": "Company",
            "sector": "Sector",
            "in_set50": st.column_config.CheckboxColumn("SET50", help="Also in the SET50 index."),
            "price": nc("Price", format="%.2f"),
            "change_pct": nc("Change", format="percent"),
            "pos_52w": st.column_config.ProgressColumn(
                "52-week range", min_value=0, max_value=1, format="percent",
                help="Where the price sits between its 52-week low (0%) and high (100%).",
            ),
            "value_traded": nc("Value (THB)", format="compact", help="Today's traded value = price × volume."),
            "market_cap": nc("Market cap", format="compact"),
            "pe": nc("P/E", format="%.1f"),
            "pe_vs_sector": nc("P/E vs sector", format="percent",
                               help="Above 0% = more expensive than the sector median P/E."),
            "pbv": nc("P/BV", format="%.2f"),
            "div_yield": nc("Div. yield", format="percent"),
            "roe": nc("ROE", format="percent"),
            "de": nc("D/E", format="%.2f", help="Yahoo Finance: interest-bearing debt / shareholders' equity. "
                                               "Not reported for banks. (The Financials tab may use thaifin's "
                                               "total liabilities / equity instead.)"),
            "net_margin": nc("Net margin", format="percent"),
            "rev_cagr5": nc("5y revenue CAGR", format="percent",
                            help="Yearly revenue growth over the last 5 full years. Blank with fewer years of "
                                 "data or a zero/negative start."),
            "ni_cagr5": nc("5y profit CAGR", format="percent",
                           help="Yearly net-income growth over the last 5 full years. Blank when either end "
                                "is a loss."),
            "roe_avg5": nc("5y avg ROE", format="percent", help="Average return on equity of the last 5 years."),
            "fscore": nc("F-score", format="%d", help="Piotroski F-score: checks passed out of those with data "
                                                      "(8 for most stocks; the current ratio has no free data). "
                                                      "Details on the stock's Fair value tab."),
            "magic_rank": nc("Magic Formula rank", format="%d",
                             help="Greenblatt's Magic Formula across SET100: rank by earnings yield (1 / P/E) plus "
                                  "rank by ROE, which stands in for return on capital. 1 = best. Blank for "
                                  "loss-making stocks."),
        },
        alt="SET100 stocks with price, valuation and profitability metrics",
    )

symbol = selected_symbol(shown, event.selection.rows)
if symbol:
    # Pass the symbol in the URL (the stock page's selectbox is bound to ?symbol=), so a reload,
    # bookmark or shared link keeps showing this stock.
    st.switch_page("app_pages/stock.py", query_params={"symbol": symbol})

with st.expander("Sector medians"):
    st.dataframe(
        medians.reset_index(),
        hide_index=True,
        column_config={
            "sector": "Sector",
            "pe": nc("P/E", format="%.1f"),
            "pbv": nc("P/BV", format="%.2f"),
            "div_yield": nc("Div. yield", format="percent"),
            "roe": nc("ROE", format="percent"),
        },
        alt="Median valuation and ROE per sector within SET100",
    )
    st.caption("Some sectors have only one or two SET100 members, so their median is just those stocks.")
