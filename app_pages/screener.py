import streamlit as st

from src import cache
from src.fundamentals import SnapshotError, sector_medians
from src.screener import selected_symbol
from src.universe import SET50_PERIOD

st.title("SET50 screener")
st.caption(f"SET50 constituents for {SET50_PERIOD}. Select a row to open the stock.")

universe = cache.set50()
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
    df = universe.merge(snaps, on="symbol")
    # How expensive vs. sector peers: +0.20 = P/E 20% above the sector median.
    df["pe_vs_sector"] = df["pe"] / df["sector"].map(medians["pe"]) - 1
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
        column_order=["symbol", "name", "sector", "price", "change_pct", "pos_52w", "value_traded", "market_cap",
                      "pe", "pe_vs_sector", "pbv", "div_yield", "roe", "de", "net_margin"],
        column_config={
            "symbol": st.column_config.TextColumn("Symbol", pinned=True),
            "name": "Company",
            "sector": "Sector",
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
        },
        alt="SET50 stocks with price, valuation and profitability metrics",
    )

symbol = selected_symbol(shown, event.selection.rows)
if symbol:
    st.session_state["symbol"] = symbol  # the stock page's selectbox key (also bound to ?symbol=)
    st.switch_page("app_pages/stock.py")

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
        alt="Median valuation and ROE per sector within SET50",
    )
    st.caption("Some sectors have only one or two SET50 members, so their median is just those stocks.")
