"""Entry point. Run with:  streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="SET100 dashboard", page_icon=":material/candlestick_chart:", layout="wide")

page = st.navigation(
    [
        st.Page(
            "app_pages/screener.py", title="SET100 screener", icon=":material/table_chart:", default=True,
            help="All SET100 stocks in one table: price, valuation and quality. Sort, filter by sector, "
                 "and open any stock for details.",
        ),
        st.Page(
            "app_pages/stock.py", title="Stock detail", icon=":material/candlestick_chart:", url_path="stock",
            help="One stock in depth: trading, chart with support/resistance, financials, valuation vs. "
                 "peers, dividends, and a prediction model.",
        ),
    ]
)

with st.sidebar:
    st.caption("Data: Yahoo Finance (prices, delayed ~15 min) and thaifin (financial history). "
               "For learning only — not investment advice.")

page.run()
