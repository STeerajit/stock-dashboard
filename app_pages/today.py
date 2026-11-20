from datetime import date

import pandas as pd
import streamlit as st

from src import cache, portfolio
from src.fundamentals import SnapshotError, pe_history
from src.today import price_levels, reasons

st.title("Today")
st.caption("Stocks in your portfolio and watchlist that may deserve a look today. "
           "Signals, not advice — open a stock to check the full picture.")

holdings = portfolio.load()
if holdings.empty:
    st.info("Your portfolio is empty. Open **Portfolio** in the sidebar, add the stocks you own (or 0 shares to "
            "just watch one), and press Save.", title="Nothing to check yet")
    st.page_link("app_pages/portfolio.py", label="Go to Portfolio", icon=":material/account_balance_wallet:")
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
with st.spinner("Checking your stocks..."):
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
                      earnings_date=snap["earnings_date"], pe=snap["pe"], pe_median=pe_median(symbol))
        if why:
            flagged.append((symbol, price, why))

if failed:
    st.warning(f"Could not load market data for {', '.join(failed)}, so they were not checked. "
               "Check the symbol, or try again in a minute.", title="Some stocks were skipped")

checked = len(holdings) - len(failed)
if not flagged:
    if checked:
        st.success(f"None of your {checked} stocks match a signal today.", title="Nothing to look at today")
else:
    st.subheader(f"{len(flagged)} of {checked} stocks to look at")
    for symbol, price, why in flagged:
        with st.container(border=True):
            st.markdown(f"**{symbol}** · {price:,.2f} THB")
            st.markdown("\n".join(f"- {w}" for w in why))
            st.page_link("app_pages/stock.py", label=f"Open {symbol}", icon=":material/arrow_forward:",
                         query_params={"symbol": symbol})

with st.expander("What the signals mean"):
    st.markdown(
        "- **Near support:** price is at most 3% above the nearest support level (a price where it turned up "
        "before).\n"
        "- **Broke resistance:** today's price is above the nearest resistance as of yesterday.\n"
        "- **RSI below 30 / above 70:** the price fell (rose) unusually fast — often called oversold (overbought).\n"
        "- **XD or earnings date within 14 days**, counting today as day 1. Yahoo often lacks Thai earnings dates.\n"
        "- **Cheap vs. its history:** current P/E is more than 20% below the median of its own yearly P/E."
    )
