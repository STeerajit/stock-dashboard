from datetime import date

import streamlit as st

from src import cache
from src.fundamentals import SnapshotError, sector_medians
from src.i18n import current_lang, t
from src.scoring import magic_formula_rank
from src.screener import selected_symbol
from src.universe import SET100_PERIOD, set100_expiry_warning

st.title(t("scr.title"))
st.caption(t("scr.caption", period=SET100_PERIOD))
if expiry_warning := set100_expiry_warning(date.today(), lang=current_lang()):
    st.warning(expiry_warning, title=t("common.list_expired_title"))

universe = cache.set100()
sectors = sorted(universe["sector"].unique())
picked = st.multiselect(t("scr.sector_filter"), sectors, placeholder=t("scr.all_sectors"), key="sectors")

table_slot = st.container()
with table_slot.skeleton():
    try:
        snaps = cache.snapshots()
    except SnapshotError as e:
        table_slot.error(str(e), title=SnapshotError.title)
        table_slot.button(t("common.retry"), icon=":material/refresh:", key="retry")
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
        column_order=["symbol", "name", "sector", "in_set50", "price", "change_pct", "pos_52w", "value_traded",
                      "market_cap", "pe", "pe_vs_sector", "pbv", "div_yield", "roe", "de", "net_margin",
                      "rev_cagr5", "ni_cagr5", "roe_avg5", "fscore", "magic_rank"],
        column_config={
            "symbol": st.column_config.TextColumn(t("common.symbol"), pinned=True),
            "name": st.column_config.TextColumn(t("common.company")),
            "sector": st.column_config.TextColumn(t("common.sector")),
            "in_set50": st.column_config.CheckboxColumn("SET50", help=t("scr.set50_help")),
            "price": nc(t("common.price"), format="%.2f"),
            "change_pct": nc(t("scr.change"), format="percent"),
            "pos_52w": st.column_config.ProgressColumn(
                t("scr.range52"), min_value=0, max_value=1, format="percent", help=t("scr.range52_help"),
            ),
            "value_traded": nc(t("scr.value"), format="compact", help=t("scr.value_help")),
            "market_cap": nc(t("scr.market_cap"), format="compact"),
            "pe": nc("P/E", format="%.1f"),
            "pe_vs_sector": nc(t("scr.pe_vs_sector"), format="percent", help=t("scr.pe_vs_sector_help")),
            "pbv": nc("P/BV", format="%.2f"),
            "div_yield": nc(t("scr.div_yield"), format="percent"),
            "roe": nc("ROE", format="percent"),
            "de": nc("D/E", format="%.2f", help=t("scr.de_help")),
            "net_margin": nc(t("scr.net_margin"), format="percent"),
            "rev_cagr5": nc(t("scr.rev_cagr"), format="percent", help=t("scr.rev_cagr_help")),
            "ni_cagr5": nc(t("scr.ni_cagr"), format="percent", help=t("scr.ni_cagr_help")),
            "roe_avg5": nc(t("scr.roe_avg"), format="percent", help=t("scr.roe_avg_help")),
            "fscore": nc("F-score", format="%d", help=t("scr.fscore_help")),
            "magic_rank": nc(t("scr.magic"), format="%d", help=t("scr.magic_help")),
        },
        alt=t("scr.table_alt"),
    )

symbol = selected_symbol(shown, event.selection.rows)
if symbol:
    # Pass the symbol in the URL (the stock page's selectbox is bound to ?symbol=), so a reload,
    # bookmark or shared link keeps showing this stock.
    st.switch_page("app_pages/stock.py", query_params={"symbol": symbol})

with st.expander(t("scr.medians")):
    st.dataframe(
        medians.reset_index(),
        hide_index=True,
        column_config={
            "sector": st.column_config.TextColumn(t("common.sector")),
            "pe": nc("P/E", format="%.1f"),
            "pbv": nc("P/BV", format="%.2f"),
            "div_yield": nc(t("scr.div_yield"), format="percent"),
            "roe": nc("ROE", format="percent"),
        },
        alt=t("scr.medians_alt"),
    )
    st.caption(t("scr.medians_note"))
