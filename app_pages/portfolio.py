from datetime import date

import pandas as pd
import streamlit as st

from src import cache, portfolio
from src.fundamentals import SnapshotError
from src.i18n import current_lang, t
from src.universe import describe

st.title(t("port.title"))
# Public demo: holdings stay in this visitor's session, never in a file on the server (see portfolio.public_mode).
public = portfolio.public_mode()
st.caption(t("port.caption_public" if public else "port.caption"))
if public:
    st.info(t("port.public"), title=t("port.public_title"), icon=":material/public:")
saved = st.session_state.get("demo_holdings", portfolio.empty()) if public else portfolio.load()
last_year = date.today().year - 1


def quotes(symbols: list[str]) -> pd.DataFrame:
    """Price, sector and last full year's dividend per share for each symbol. Raises SnapshotError."""
    universe = cache.set100()
    listed = set(universe["symbol"])
    snaps = cache.snapshots() if listed & set(symbols) else pd.DataFrame(columns=["symbol", "price"])
    rows = []
    for sym in symbols:
        snap = snaps if sym in listed else cache.snapshot(sym)
        price = snap.loc[snap["symbol"] == sym, "price"]
        rows.append({"symbol": sym, "price": price.iloc[0] if len(price) else float("nan"),
                     "dps": portfolio.last_full_year_dps(cache.dividends(sym), date.today().year),
                     "sector": describe(universe, sym)[1]})
    return pd.DataFrame(rows, columns=["symbol", "price", "dps", "sector"])


if saved.empty:
    st.info(t("port.empty"), title=t("port.empty_title"))
else:
    try:
        pos = portfolio.positions(saved, quotes(saved["symbol"].tolist()))
    except SnapshotError as e:
        st.warning(str(e), title=SnapshotError.title)
    else:
        tot = portfolio.totals(pos)
        with st.container(horizontal=True):
            st.metric(t("port.value"), f"{tot['value']:,.0f}", border=True, height="stretch")
            st.metric(t("port.pnl"), f"{tot['pnl']:+,.0f}",
                      f"{tot['pnl_pct']:+.1%}" if pd.notna(tot["pnl_pct"]) else None, border=True, height="stretch",
                      help=t("port.pnl_help", cost=f"{tot['cost']:,.0f}"))
            st.metric(t("port.dividend"), f"{tot['est_dividend']:,.0f}", border=True,
                      height="stretch", help=t("port.dividend_help", year=last_year))
            st.metric(t("port.yoc"), f"{tot['yield_on_cost']:.2%}" if pd.notna(tot["yield_on_cost"]) else "–",
                      border=True, height="stretch", help=t("port.yoc_help"))

        if missing := pos.loc[(pos["shares"] > 0) & pos["price"].isna(), "symbol"].tolist():
            st.warning(t("port.missing", symbols=", ".join(missing)), title=t("port.missing_title"))

        nc = st.column_config.NumberColumn
        st.dataframe(
            pos.sort_values(["value", "symbol"], ascending=[False, True]),
            hide_index=True,
            column_order=["symbol", "sector", "shares", "avg_cost", "price", "value", "pnl", "pnl_pct",
                          "est_dividend", "yield_on_cost"],
            column_config={
                "symbol": st.column_config.TextColumn(t("common.symbol"), pinned=True),
                "sector": st.column_config.TextColumn(t("common.sector")),
                "shares": nc(t("port.shares"), format="localized", help=t("port.shares_help")),
                "avg_cost": nc(t("port.avg_cost"), format="%.2f"),
                "price": nc(t("common.price"), format="%.2f"),
                "value": nc(t("port.col_value"), format="localized"),
                "pnl": nc(t("port.col_pnl"), format="localized"),
                "pnl_pct": nc(t("port.col_pnl_pct"), format="percent"),
                "est_dividend": nc(t("port.col_dividend"), format="localized",
                                   help=t("port.col_dividend_help", year=last_year)),
                "yield_on_cost": nc(t("port.yoc"), format="percent"),
            },
            alt=t("port.table_alt"),
        )

        alloc = portfolio.allocation(pos)
        if not alloc.empty:
            st.subheader(t("port.allocation"))
            st.bar_chart((alloc * 100).round(1).rename(t("port.alloc_series")), horizontal=True,
                         x_label=t("port.alloc_axis"), alt=t("port.alloc_alt"))
        st.caption(t("port.note", year=last_year))

st.subheader(t("port.edit"))
with st.form("holdings_form", border=False):
    edited = st.data_editor(
        saved,
        key="holdings",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "symbol": st.column_config.TextColumn(t("common.symbol"), help=t("port.symbol_help")),
            "shares": st.column_config.NumberColumn(t("port.shares"), min_value=0, step=1, format="%d",
                                                    help=t("port.shares_edit_help")),
            "avg_cost": st.column_config.NumberColumn(t("port.avg_cost_edit"), min_value=0, format="%.2f",
                                                      help=t("port.avg_cost_edit_help")),
        },
    )
    submitted = st.form_submit_button(t("port.save"), icon=":material/save:", type="primary")

if submitted:
    holdings, problems = portfolio.clean(edited, lang=current_lang())
    if problems:
        st.error(t("port.not_saved") + "\n" + "\n".join(f"- {p}" for p in problems), title=t("port.check_title"))
    else:
        if public:
            st.session_state["demo_holdings"] = holdings
        else:
            portfolio.save(holdings)
        # The editor's state holds edits relative to the old table; drop it so the saved file is shown as-is
        # (otherwise added rows would be added a second time on top of the reloaded file).
        st.session_state.pop("holdings", None)
        st.session_state["saved_count"] = len(holdings)
        st.rerun()

if (count := st.session_state.pop("saved_count", None)) is not None:
    st.toast(t("port.saved", count=count), icon=":material/check:")
