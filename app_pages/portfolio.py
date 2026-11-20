import streamlit as st

from src import portfolio

st.title("Portfolio")
st.caption("The stocks you own, plus a watchlist: enter 0 shares for a stock you only want to follow. "
           "Saved on this Mac only (data/portfolio.csv, never committed to git).")

saved = portfolio.load()

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
