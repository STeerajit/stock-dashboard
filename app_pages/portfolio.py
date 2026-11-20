from datetime import date

import pandas as pd
import streamlit as st

from src import cache, portfolio
from src.fundamentals import SnapshotError
from src.universe import describe

st.title("Portfolio")
st.caption("The stocks you own, plus a watchlist: enter 0 shares for a stock you only want to follow. "
           "Saved on this Mac only (data/portfolio.csv, never committed to git).")

saved = portfolio.load()
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
    st.info("No stocks yet. Add them in the table below, then press Save.", title="Empty portfolio")
else:
    try:
        pos = portfolio.positions(saved, quotes(saved["symbol"].tolist()))
    except SnapshotError as e:
        st.warning(str(e), title=SnapshotError.title)
    else:
        tot = portfolio.totals(pos)
        with st.container(horizontal=True):
            st.metric("Market value (THB)", f"{tot['value']:,.0f}", border=True, height="stretch")
            st.metric("Profit / loss (THB)", f"{tot['pnl']:+,.0f}",
                      f"{tot['pnl_pct']:+.1%}" if pd.notna(tot["pnl_pct"]) else None, border=True, height="stretch",
                      help=f"Market value minus cost ({tot['cost']:,.0f} THB).")
            st.metric("Estimated dividend / year (THB)", f"{tot['est_dividend']:,.0f}", border=True,
                      height="stretch", help=f"Dividend per share paid in {last_year} × shares you hold now.")
            st.metric("Yield on cost", f"{tot['yield_on_cost']:.2%}" if pd.notna(tot["yield_on_cost"]) else "–",
                      border=True, height="stretch", help="Estimated dividend / what you paid.")

        if missing := pos.loc[(pos["shares"] > 0) & pos["price"].isna(), "symbol"].tolist():
            st.warning(f"No current price for {', '.join(missing)}, so the totals leave them out. "
                       "Check the symbol, or try again in a minute.", title="Missing prices")

        nc = st.column_config.NumberColumn
        st.dataframe(
            pos.sort_values(["value", "symbol"], ascending=[False, True]),
            hide_index=True,
            column_order=["symbol", "sector", "shares", "avg_cost", "price", "value", "pnl", "pnl_pct",
                          "est_dividend", "yield_on_cost"],
            column_config={
                "symbol": st.column_config.TextColumn("Symbol", pinned=True),
                "sector": "Sector",
                "shares": nc("Shares", format="localized", help="0 = watchlist."),
                "avg_cost": nc("Avg. cost", format="%.2f"),
                "price": nc("Price", format="%.2f"),
                "value": nc("Value (THB)", format="localized"),
                "pnl": nc("P/L (THB)", format="localized"),
                "pnl_pct": nc("P/L %", format="percent"),
                "est_dividend": nc("Est. dividend (THB)", format="localized",
                                   help=f"Dividend per share paid in {last_year} × shares."),
                "yield_on_cost": nc("Yield on cost", format="percent"),
            },
            alt="Holdings and watchlist with value, profit or loss, estimated dividend and yield on cost",
        )

        alloc = portfolio.allocation(pos)
        if not alloc.empty:
            st.subheader("Allocation by sector")
            st.bar_chart((alloc * 100).round(1).rename("% of value"), horizontal=True,
                         x_label="% of market value",
                         alt="Share of the portfolio's market value in each sector")
        st.caption(f"No trading fees, VAT or dividend tax are included. Estimated dividend uses the dividends per "
                   f"share paid in {last_year} (the last complete year, by XD date); future dividends may differ. "
                   "Prices are delayed ~15 min.")

st.subheader("Edit holdings")
with st.form("holdings_form", border=False):
    edited = st.data_editor(
        saved,
        key="holdings",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "symbol": st.column_config.TextColumn("Symbol", help="SET symbol, e.g. PTT. Any Thai stock works."),
            "shares": st.column_config.NumberColumn("Shares", min_value=0, step=1, format="%d",
                                                    help="0 = watchlist only."),
            "avg_cost": st.column_config.NumberColumn("Average cost (THB)", min_value=0, format="%.2f",
                                                      help="Average price paid per share. Leave empty for "
                                                           "a watchlist stock."),
        },
    )
    submitted = st.form_submit_button("Save", icon=":material/save:", type="primary")

if submitted:
    holdings, problems = portfolio.clean(edited)
    if problems:
        st.error("Not saved. Please fix:\n" + "\n".join(f"- {p}" for p in problems), title="Check your input")
    else:
        portfolio.save(holdings)
        # The editor's state holds edits relative to the old table; drop it so the saved file is shown as-is
        # (otherwise added rows would be added a second time on top of the reloaded file).
        st.session_state.pop("holdings", None)
        st.session_state["saved_count"] = len(holdings)
        st.rerun()

if (count := st.session_state.pop("saved_count", None)) is not None:
    st.toast(f"Saved {count} stocks.", icon=":material/check:")
