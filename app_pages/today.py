from datetime import date

import streamlit as st

from src import cache, portfolio
from src import dividend_picks as dp
from src import signals as sg
from src.fundamentals import SnapshotError, pe_history
from src.i18n import current_lang, t
from src.picks_backtest import load_results, rule_passed
from src.today import price_levels, reasons

st.title(t("today.title"))
st.caption(t("today.caption"))

holdings = (st.session_state.get("demo_holdings", portfolio.empty()) if portfolio.public_mode()
            else portfolio.load())
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

try:  # the caps set on the Portfolio page, if any
    breaches = portfolio.concentration(portfolio.positions(holdings, cache.quotes(holdings["symbol"].tolist())),
                                       st.session_state.get("conc_caps", portfolio.DEFAULT_CAPS))
except SnapshotError:  # no prices: nothing to weigh
    breaches = []
if breaches:
    st.warning(t("today.conc", items="; ".join(portfolio.breach_text(b, current_lang()) for b in breaches)),
               icon=":material/pie_chart:")

checked = len(holdings) - len(failed)
if not flagged:
    if checked:
        st.success(t("today.none", count=checked), title=t("today.none_title"))
else:
    st.subheader(t("today.count", flagged=len(flagged), checked=checked))
    for symbol, price, why in flagged:
        with st.container(border=True, key=f"card-watch-{symbol}"):
            st.markdown(t("today.price", symbol=symbol, price=f"{price:,.2f}"))
            st.markdown("\n".join(f"- {w}" for w in why))
            st.page_link("app_pages/stock.py", label=t("today.open", symbol=symbol), icon=":material/arrow_forward:",
                         query_params={"symbol": symbol})

# Sell signals from Dividend Picks, for the SET100 stocks you own (not the watchlist).
held = holdings.loc[holdings["shares"] > 0, "symbol"].tolist()
data = cache.picks_data() if held else {}
held_set100 = [s for s in held if s in data]
if held_set100:
    day = max(d.close.index[-1] for d in data.values())
    screened = dp.screen(data, day).set_index("symbol")
    show_sell = rule_passed(load_results(), "sell_now")
    warnings = []
    for symbol in held_set100:
        sig = sg.compute(data[symbol], day, rank=screened.at[symbol, "rank"], stage=str(screened.at[symbol, "stage"]),
                         lang=current_lang())
        on = [s for key, s in sig.items() if sg.SIGNALS[key].side == "sell" and s.on]
        if on:
            warnings.append((symbol, on, show_sell and sg.sell_now(sig)))
    if warnings:
        st.subheader(t("today.sell_title", count=len(warnings)))
        st.caption(t("today.sell_caption"))
        for symbol, on, sell in warnings:
            with st.container(border=True, key=f"card-sell-{symbol}"):
                st.markdown(f"**{symbol}**" + (f"  ·  :red-badge[{t('pk.sell')}]" if sell else ""))
                st.markdown("\n".join(f"- **{t(f'sig.name.{s.key}')}**: {s.label}" for s in on))
                st.page_link("app_pages/stock.py", label=t("today.open", symbol=symbol),
                             icon=":material/arrow_forward:", query_params={"symbol": symbol})

with st.expander(t("today.legend_title")):
    st.markdown(t("today.legend"))
