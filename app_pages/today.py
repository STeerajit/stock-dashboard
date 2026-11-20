from datetime import date

import streamlit as st

from src import cache, portfolio
from src.fundamentals import SnapshotError, pe_history
from src.i18n import current_lang, t
from src.today import price_levels, reasons

st.title(t("today.title"))
st.caption(t("today.caption"))

holdings = portfolio.load()
if holdings.empty:
    st.info(t("today.empty"), title=t("today.empty_title"))
    st.page_link("app_pages/portfolio.py", label=t("today.go_portfolio"), icon=":material/account_balance_wallet:")
    st.stop()


def pe_median(symbol: str) -> float | None:
    """Median of the stock's own yearly P/E (as on the Valuation tab), or None without enough history."""
    fin = cache.financials(symbol)
    if fin.empty:
        return None
    series = fin["P/E"].dropna()
    if len(series) < 2:  # Yahoo fallback has no yearly P/E: approximate it from year-end prices and EPS
        series = pe_history(cache.prices(symbol), fin).dropna()
    return float(series.median()) if len(series) >= 2 else None


flagged, failed = [], []
with st.spinner(t("today.checking")):
    for symbol in holdings["symbol"]:
        try:
            snap = cache.snapshot_of(symbol)
            prices = cache.prices(symbol)
        except (SnapshotError, cache.NoPriceData):
            failed.append(symbol)
            continue
        price, support, resistance = price_levels(prices)
        why = reasons(today=date.today(), price=price, support=support, resistance_before_today=resistance,
                      rsi=prices["RSI14"].iloc[-1], ex_div_date=snap["ex_div_date"],
                      earnings_date=snap["earnings_date"], pe=snap["pe"], pe_median=pe_median(symbol),
                      lang=current_lang())
        if why:
            flagged.append((symbol, price, why))

if failed:
    st.warning(t("today.skipped", symbols=", ".join(failed)), title=t("today.skipped_title"))

checked = len(holdings) - len(failed)
if not flagged:
    if checked:
        st.success(t("today.none", count=checked), title=t("today.none_title"))
else:
    st.subheader(t("today.count", flagged=len(flagged), checked=checked))
    for symbol, price, why in flagged:
        with st.container(border=True):
            st.markdown(t("today.price", symbol=symbol, price=f"{price:,.2f}"))
            st.markdown("\n".join(f"- {w}" for w in why))
            st.page_link("app_pages/stock.py", label=t("today.open", symbol=symbol), icon=":material/arrow_forward:",
                         query_params={"symbol": symbol})

with st.expander(t("today.legend_title")):
    st.markdown(t("today.legend"))
