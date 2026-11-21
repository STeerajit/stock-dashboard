"""Entry point. Run with:  streamlit run app.py"""

from pathlib import Path

import duckdb
import streamlit as st

from src import portfolio, store
from src.i18n import DEFAULT, LANGS, t
from src.universe import load_set100

# Language: chosen in the sidebar and kept in the URL as ?lang=th, so a link or reload keeps it.
# (A widget bound to the URL would put the label "ไทย" there instead of "th".)
if "lang_choice" not in st.session_state:
    url_lang = st.query_params.get("lang", DEFAULT)
    st.session_state["lang_choice"] = url_lang if url_lang in LANGS else DEFAULT

st.set_page_config(page_title=t("app.page_title"), page_icon=":material/candlestick_chart:", layout="wide")
st.html(Path(__file__).parent / "src" / "style.css")  # card surfaces; delete this line to switch the CSS off

page = st.navigation(
    [
        st.Page("app_pages/today.py", title=t("nav.today"), icon=":material/today:", default=True,
                help=t("nav.today_help")),
        st.Page("app_pages/screener.py", title=t("nav.screener"), icon=":material/table_chart:",
                url_path="screener", help=t("nav.screener_help")),
        st.Page("app_pages/dividend_picks.py", title=t("nav.picks"), icon=":material/savings:",
                url_path="dividend-picks", help=t("nav.picks_help")),
        st.Page("app_pages/stock.py", title=t("nav.stock"), icon=":material/candlestick_chart:", url_path="stock",
                help=t("nav.stock_help")),
        st.Page("app_pages/portfolio.py", title=t("nav.portfolio"), icon=":material/account_balance_wallet:",
                url_path="portfolio", help=t("nav.portfolio_help")),
    ]
)

with st.sidebar:
    st.segmented_control(t("app.language"), list(LANGS), format_func=lambda code: LANGS[code], key="lang_choice", required=True)
    if st.session_state["lang_choice"] == DEFAULT:
        st.query_params.pop("lang", None)
    else:
        st.query_params["lang"] = st.session_state["lang_choice"]

    try:
        as_of = store.as_of(store.STORE_PATH)
    except duckdb.Error:  # locked by an update running elsewhere
        as_of = None
    if as_of:
        st.caption(t("app.as_of", when=f"{as_of:%d %b %Y %H:%M}"))
    else:
        st.caption(t("app.live"))
    # Not on the public demo: one visitor's click would make every visitor wait for the download.
    if not portfolio.public_mode() and st.button(t("app.update"), icon=":material/sync:", help=t("app.update_help")):
        with st.spinner(t("app.updating")):
            try:
                report = store.update_store(store.STORE_PATH, load_set100()["symbol"].tolist(), store.live_fetchers())
            except (store.UpdateError, duckdb.Error) as e:
                st.error(str(e), title=t("app.update_failed"))
            else:
                st.cache_data.clear()
                if report.failed:
                    st.warning(t("app.update_skipped", symbols=", ".join(report.failed)))
                st.success(t("app.updated", count=len(report.updated)))
    st.caption(t("app.sources"))

page.run()
