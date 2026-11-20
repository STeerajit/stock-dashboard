"""Entry point. Run with:  streamlit run app.py"""

import duckdb
import streamlit as st

from src import store
from src.universe import load_set100

st.set_page_config(page_title="SET100 dashboard", page_icon=":material/candlestick_chart:", layout="wide")

page = st.navigation(
    [
        st.Page(
            "app_pages/today.py", title="Today", icon=":material/today:", default=True,
            help="Stocks in your portfolio and watchlist that may deserve a look today, and why.",
        ),
        st.Page(
            "app_pages/screener.py", title="SET100 screener", icon=":material/table_chart:", url_path="screener",
            help="All SET100 stocks in one table: price, valuation and quality. Sort, filter by sector, "
                 "and open any stock for details.",
        ),
        st.Page(
            "app_pages/stock.py", title="Stock detail", icon=":material/candlestick_chart:", url_path="stock",
            help="One stock in depth: trading, chart with support/resistance, financials, valuation vs. "
                 "peers, dividends, and a prediction model.",
        ),
        st.Page(
            "app_pages/portfolio.py", title="Portfolio", icon=":material/account_balance_wallet:",
            url_path="portfolio", help="The stocks you own and your watchlist, saved on this Mac.",
        ),
    ]
)

with st.sidebar:
    try:
        as_of = store.as_of(store.STORE_PATH)
    except duckdb.Error:  # locked by an update running elsewhere
        as_of = None
    if as_of:
        st.caption(f"Data as of **{as_of:%d %b %Y %H:%M}** (local store). Stocks outside SET100 are fetched live.")
    else:
        st.caption("Live data (no local store yet). Press Update data to save a copy for fast, offline use.")
    if st.button("Update data", icon=":material/sync:", help="Download today's data for all SET100 stocks into "
                 "data/market.duckdb (about 1–2 minutes). Same as running scripts/update_data.py."):
        with st.spinner("Downloading SET100 data..."):
            try:
                report = store.update_store(store.STORE_PATH, load_set100()["symbol"].tolist(), store.live_fetchers())
            except (store.UpdateError, duckdb.Error) as e:
                st.error(str(e), title="Update failed")
            else:
                st.cache_data.clear()
                if report.failed:
                    st.warning(f"Skipped (old data kept): {', '.join(report.failed)}")
                st.success(f"Updated {len(report.updated)} stocks.")
    st.caption("Data: Yahoo Finance (prices, delayed ~15 min) and thaifin (financial history). "
               "For learning only — not investment advice.")

page.run()
