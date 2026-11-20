from datetime import date
from typing import cast

import numpy as np
import pandas as pd
import streamlit as st

from src import cache
from src.portfolio import last_full_year_dps
from src.scoring import piotroski
from src.charts import price_chart
from src.fundamentals import SCORE_COLUMNS, SnapshotError, growth_quality, pe_history, sector_medians, snapshot_for, yield_history
from src.indicators import support_resistance
from src.set_links import set_links
from src.valuation import DEFAULT_REQUIRED_RETURN, dcf_value, ddm_value, default_ddm_growth, sensitivity
from src.universe import OUTSIDE_SET100, describe, is_valid_symbol, set100_expiry_warning


def baht(x: float | None) -> str:
    """1_234_000_000 -> '1.23B'."""
    if x is None or pd.isna(x):
        return "–"
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            return f"{x / div:,.2f}{unit}"
    return f"{x:,.2f}"


def pct(x: float | None, digits: int = 1) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:.{digits}%}"


def num(x: float | None, digits: int = 2) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:,.{digits}f}"


universe = cache.set100()
# Options are plain symbols so the URL can be shared as ?symbol=PTT (a format_func
# would change the option labels and the URL value would no longer match).
# accept_new_options: any Thai stock can be typed in (or put in the URL), not only SET100.
symbol = st.selectbox("Stock", universe["symbol"].tolist(), key="symbol", bind="query-params",
                      accept_new_options=True, help="Pick a SET100 stock, or type any SET symbol and press Enter.")
symbol = symbol.strip().upper()
if not is_valid_symbol(symbol):
    st.error("A SET symbol has only letters, digits and . & - (up to 15 characters), e.g. PTT.",
             title="Not a valid symbol")
    st.stop()
name, sector = describe(universe, symbol)
in_set100 = sector != OUTSIDE_SET100
st.title(f"{symbol} · {name}")
st.caption(sector)
if expiry_warning := set100_expiry_warning(date.today()):
    st.warning(expiry_warning, title="SET100 list may be out of date")

with st.popover("See on the SET website", icon=":material/open_in_new:"):
    st.caption("For what has no free data feed: money flows, shareholders, warning signs, XR dates and news.")
    for link in set_links(symbol):
        st.markdown(f"- [{link.label}]({link.url})" + (f" — all stocks, look up {symbol}" if link.market_wide else ""))

snapshot_error: SnapshotError | None = None
try:
    if in_set100:
        snaps = cache.snapshots()
        medians = cast(pd.Series, sector_medians(snaps, universe).loc[sector])  # sectors are unique
    else:
        snaps = cache.snapshot(symbol)
        medians = pd.Series(np.nan, index=["pe", "pbv", "div_yield", "roe"])  # no SET peers to compare with
    snap = snapshot_for(snaps, symbol)
except SnapshotError as e:
    snapshot_error = e  # `snap` and `medians` are then unset: tabs that use them call need_snapshot() first


def need_snapshot() -> None:
    """Inside a tab that needs live market data: show a warning and stop if it is unavailable."""
    if snapshot_error:
        st.warning(str(snapshot_error), title=SnapshotError.title)
        st.stop()

tabs = st.tabs(
    [":material/swap_vert: Trading", ":material/candlestick_chart: Chart", ":material/account_balance: Financials",
     ":material/sell: Valuation", ":material/event: Dividends & calendar", ":material/balance: Fair value",
     ":material/online_prediction: Prediction"],
    key="tab", on_change="rerun",
)
t_trade, t_chart, t_fin, t_val, t_div, t_fair, t_pred = tabs

# ============ 1. Trading: how much is the market paying attention? ============
if t_trade.open:
    with t_trade:
        need_snapshot()
        vol_ratio = snap["volume"] / snap["avg_volume"] if snap["avg_volume"] else np.nan
        with st.container(horizontal=True):
            st.metric("Price", num(snap["price"]), pct(snap["change_pct"], 2), border=True, height="stretch")
            st.metric("Volume", baht(snap["volume"]), f"{vol_ratio:.1f}× avg" if pd.notna(vol_ratio) else None,
                      delta_color="off", border=True, height="stretch",
                      help="Today's volume compared with the 3-month average volume.")
            st.metric("Value traded (THB)", baht(snap["value_traded"]), border=True, height="stretch")
            st.metric("Market cap (THB)", baht(snap["market_cap"]), border=True, height="stretch")
        with st.container(horizontal=True):
            st.metric("Bid / Offer", f"{num(snap['bid'])} / {num(snap['ask'])}", border=True, height="stretch",
                      help="Best bid and offer only (delayed). Full market depth needs a broker feed.")
            st.metric("52-week high", num(snap["high_52w"]), border=True, height="stretch")
            st.metric("52-week low", num(snap["low_52w"]), border=True, height="stretch")
            st.metric("Position in 52-week range", pct(snap["pos_52w"], 0), border=True, height="stretch",
                      help="0% = at the 52-week low, 100% = at the 52-week high.")
            st.metric("Free float (Yahoo estimate)", pct(snap["free_float"], 0), border=True, height="stretch",
                      help="Share of shares not held by insiders or major holders, as estimated by Yahoo. "
                           "SET's official figure is under 'Major shareholders and free float' on the SET website.")
        if pd.notna(vol_ratio) and vol_ratio >= 2:
            st.info(f"Volume today is {vol_ratio:.1f}× the average — unusual interest.", title="High activity")

# ============ 4. Chart: trend, support/resistance, MA, RSI, volume ============
if t_chart.open:
    with t_chart:
        period = st.segmented_control("Period", ["3M", "6M", "1Y", "2Y", "5Y"], default="1Y", key="period",
                                      required=True)
        days = {"3M": 63, "6M": 126, "1Y": 250, "2Y": 500, "5Y": 1250}[period]
        try:
            df = cache.prices(symbol).tail(days)
        except cache.NoPriceData as e:
            st.warning(str(e), title="No price data")
            st.stop()
        supports, resistances = support_resistance(df)
        st.plotly_chart(
            price_chart(df, symbol, supports, resistances),
            alt=f"{symbol} candlestick chart with SMA20/50, support and resistance lines, volume and RSI",
        )
        st.caption(
            "Prices are adjusted for dividends and splits. S = support, R = resistance: price levels where the "
            "stock turned around before (swing highs/lows within ±10 days, merged when within 2%)."
        )

# ============ 2. Financials: is the business good and strong? ============
if t_fin.open:
    with t_fin:
        fin = cache.financials(symbol)
        if fin.empty:
            st.warning("No financial statements found for this stock.", title="No data")
        else:
            if fallback_note := fin.attrs.get("fallback_note"):
                st.warning(fallback_note, title="Shorter history than usual")
            src = fin.attrs.get("source", "?")
            st.caption(f"Annual figures {fin.index.min()}–{fin.index.max()} ({len(fin)} years). Source: {src}.")
            last = fin.iloc[-1]
            with st.container(horizontal=True):
                st.metric("Revenue", baht(last["Revenue"]), pct(last["Revenue growth"]), border=True, height="stretch")
                st.metric("Net income", baht(last["Net income"]), pct(last["Net income growth"]), border=True,
                          height="stretch")
                st.metric("ROE", pct(last["ROE"]), border=True, height="stretch")
                st.metric("D/E", num(last["D/E"]), border=True, height="stretch",
                          help=f"{fin.attrs.get('de_definition', 'Debt / equity')}. "
                               "Banks and finance companies naturally carry much higher leverage.")
                st.metric("Free cash flow", baht(last["Free cash flow"]), border=True, height="stretch",
                          help="Cash from operations minus investment spending.")

            left, right = st.columns(2)
            with left:
                st.subheader("Revenue and net income")
                st.bar_chart((fin[["Revenue", "Net income"]] / 1e9).rename(index=str), stack=False,
                             y_label="THB billion", alt=f"{symbol} yearly revenue and net income")
            with right:
                st.subheader("Margins and ROE")
                st.line_chart(fin[["Gross margin", "Net margin", "ROE"]].rename(index=str),
                              alt=f"{symbol} gross margin, net margin and ROE by year")

            st.subheader("Free cash flow")
            st.bar_chart((fin["Free cash flow"] / 1e9).rename(index=str), y_label="THB billion",
                         alt=f"{symbol} yearly free cash flow")
            if sector in ("Banking", "Finance & Securities", "Insurance"):
                st.caption("For banks, lenders and insurers, lending and investing are the business itself, "
                           "so free cash flow swings widely and is not a useful health measure.")

            table = fin.drop(columns=["P/E", "P/BV", *SCORE_COLUMNS]).T
            table.columns = [str(c) for c in table.columns]
            fmt = {"Revenue": baht, "Net income": baht, "Free cash flow": baht, "EPS": num, "D/E": num}
            shown = table.apply(lambda r: r.map(fmt.get(r.name, pct)), axis=1)
            st.dataframe(shown, alt=f"{symbol} yearly financial figures")

# ============ 3. Valuation: expensive or cheap? ============
if t_val.open:
    with t_val:
        need_snapshot()
        st.caption(f"Compared with the median of SET100 stocks in {sector}." if in_set100 else
                   "Stocks outside SET100 have no sector comparison.")

        def vs(value, median):
            return f"{value / median - 1:+.0%} vs sector" if pd.notna(value) and pd.notna(median) and median else None

        with st.container(horizontal=True):
            st.metric("P/E", num(snap["pe"], 1), vs(snap["pe"], medians["pe"]), delta_color="inverse",
                      border=True, height="stretch", help=f"Sector median: {num(medians['pe'], 1)}")
            st.metric("P/BV", num(snap["pbv"]), vs(snap["pbv"], medians["pbv"]), delta_color="inverse",
                      border=True, height="stretch", help=f"Sector median: {num(medians['pbv'])}")
            st.metric("Dividend yield", pct(snap["div_yield"]), vs(snap["div_yield"], medians["div_yield"]),
                      border=True, height="stretch", help=f"Sector median: {pct(medians['div_yield'])}")
        st.caption("Red = more expensive (or lower yield) than sector peers; green = cheaper.")

        st.subheader("Compared with its own history")
        fin = cache.financials(symbol)
        history = fin[["P/E", "P/BV"]].copy() if not fin.empty else pd.DataFrame()
        if not history.empty and history["P/E"].count() < 2:
            # Yahoo fallback has no yearly P/E: approximate it from year-end prices and EPS.
            try:
                history["P/E"] = pe_history(cache.prices(symbol), fin)
            except cache.NoPriceData:
                pass

        metric = st.segmented_control("Metric", ["P/E", "P/BV", "Dividend yield"], default="P/E",
                                      key="val_metric", required=True)
        if metric == "Dividend yield":
            try:
                series = yield_history(cache.dividends(symbol), cache.unadjusted_close(symbol), date.today().year)
            except cache.NoPriceData:
                series = pd.Series(dtype=float)
        else:
            series = history[metric].dropna() if metric in history else pd.Series(dtype=float)
        if len(series) < 2:
            st.info(f"Not enough yearly {metric} history for this stock.", title="No history")
        elif metric == "Dividend yield":
            median = series.median()
            st.line_chart(pd.DataFrame({"Dividend yield (%)": series * 100,
                                        f"{len(series)}-year median": median * 100}).rename(index=str),
                          y_label="%", alt=f"{symbol} yearly dividend yield compared with its median")
            current = snap["div_yield"]
            if pd.notna(current):
                pp = (current - median) * 100
                verdict = "cheaper" if pp > 0 else "more expensive"  # a higher yield means a lower price
                st.markdown(f"Current dividend yield **{pct(current)}** is **{pp:+.1f} pp** vs. its "
                            f"{len(series)}-year median of {pct(median)} — {verdict} than usual.")
            st.caption("Yearly yield = dividends per share with XD dates in that year ÷ the year's last close as "
                       "traded (not adjusted for dividends). A year without dividends counts as 0%. "
                       "pp = percentage points. Current value: Yahoo (trailing 12 months).")
        else:
            median = series.median()
            st.line_chart(pd.DataFrame({metric: series, f"{len(series)}-year median": median}).rename(index=str),
                          alt=f"{symbol} year-end {metric} by year compared with its median")
            current = {"P/E": snap["pe"], "P/BV": snap["pbv"]}[metric]
            if pd.notna(current) and median:
                diff = current / median - 1
                verdict = "cheaper" if diff < 0 else "more expensive"
                st.markdown(f"Current {metric} **{num(current)}** is **{abs(diff):.0%} "
                            f"{'below' if diff < 0 else 'above'}** its {len(series)}-year median of "
                            f"{num(median)} — {verdict} than usual.")
            st.caption("Median is used instead of average so one unusual year (e.g. a loss year) doesn't distort it. "
                       f"Current value: Yahoo (trailing 12 months); history: {fin.attrs.get('source', '?')} "
                       "(year-end), so the two can differ slightly.")

# ============ 8 (partly). Dividends & calendar ============
if t_div.open:
    with t_div:
        need_snapshot()
        with st.container(horizontal=True):
            st.metric("Next / last XD date", snap["ex_div_date"].strftime("%d %b %Y") if pd.notna(snap["ex_div_date"])
                      else "–", border=True, height="stretch")
            st.metric("Next earnings date", snap["earnings_date"].strftime("%d %b %Y")
                      if pd.notna(snap["earnings_date"]) else "–", border=True, height="stretch",
                      help="From Yahoo; often missing for Thai stocks. Check SET announcements to be sure.")
            st.metric("Dividend yield", pct(snap["div_yield"]), border=True, height="stretch")
        div = cache.dividends(symbol)
        if div.empty:
            st.info("No dividend history on Yahoo Finance.", title="No dividends")
        else:
            st.subheader("Dividend per share by year (THB)")
            st.bar_chart(div.tail(15).rename(index=str), alt=f"{symbol} dividend per share by year")
            st.caption("Grouped by XD date. The current year may be incomplete.")

# ============ Fair value and F-score (backlog #13) ============
FINANCIAL_SECTORS = ("Banking", "Finance & Securities", "Insurance")


def pct_slider(label: str, low: float, high: float, default: float, key: str, help: str) -> float:
    """A slider in percent (e.g. 8.0) that returns a fraction (0.08)."""
    value = st.slider(label, low, high, float(min(max(round(default * 100 * 2) / 2, low), high)), step=0.5,
                      format="%.1f%%", key=key, help=help)
    return value / 100


def show_fair_value(name: str, fair: float, price: float) -> None:
    if fair <= 0:
        st.info(f"The {name} result is zero or negative: with these assumptions, net debt is larger than the value "
                "of the future cash flows. The model says little about this stock.", title="No meaningful value")
        return
    with st.container(horizontal=True):
        st.metric(f"Fair value ({name})", num(fair), border=True, height="stretch")
        st.metric("Price now", num(price), border=True, height="stretch")
        st.metric("Margin of safety", pct(fair / price - 1, 0), border=True, height="stretch",
                  help="How far the fair value is above (+) or below (−) today's price.")


def show_sensitivity(table: pd.DataFrame, r_label: str, g_label: str, alt: str) -> None:
    shown = table.copy()
    shown.index = [f"{r_label} {r:.1%}" for r in shown.index]
    shown.columns = [f"{g_label} {g:.1%}" for g in shown.columns]
    st.dataframe(shown.map(lambda v: num(v)), alt=alt)


if t_fair.open:
    with t_fair:
        need_snapshot()
        price = snap["price"]
        st.info("An estimate based on your assumptions — not investment advice. Small changes in the "
                "assumptions move the result a lot; see the tables.", title="Estimate only", icon=":material/info:")
        this_year = date.today().year

        st.subheader("Dividend discount model (DDM)")
        div = cache.dividends(symbol)
        last_dps = last_full_year_dps(div, this_year)
        if pd.isna(last_dps) or last_dps <= 0:
            st.info(f"{symbol} paid no dividend in {this_year - 1}, so the dividend model can't value it.",
                    title="No dividend")
        else:
            c1, c2 = st.columns(2)
            with c1:
                g = pct_slider("Dividend growth per year", -5.0, 10.0, default_ddm_growth(div, this_year), "ddm_g",
                               "Growth forever. Default: growth of dividends per share over the last 5 full years, "
                               "at most 6% (it must stay below the required return).")
            with c2:
                r = pct_slider("Required return", 4.0, 15.0, DEFAULT_REQUIRED_RETURN, "ddm_r",
                               "The yearly return you want for the risk. Default 8%.")
            st.caption(f"Dividend per share paid in {this_year - 1}: {num(last_dps)} THB → next year "
                       f"{num(last_dps * (1 + g))} THB at {g:.1%} growth.")
            try:
                show_fair_value("DDM", ddm_value(last_dps * (1 + g), g, r), price)
            except ValueError as e:
                st.error(str(e), title="Can't compute")
            show_sensitivity(sensitivity(lambda rr, gg: ddm_value(last_dps * (1 + gg), gg, rr),
                                         [r - 0.01, r, r + 0.01], [g - 0.01, g, g + 0.01]),
                             "r", "g", f"{symbol} DDM fair value for required return and growth ±1 point")

        st.subheader("Discounted cash flow (DCF)")
        fin = cache.financials(symbol)
        last = fin.iloc[-1] if not fin.empty else pd.Series(dtype=float)
        if sector in FINANCIAL_SECTORS:
            st.info("Not used for banks, lenders and insurers: lending and investing are their business, so "
                    "their free cash flow says little about their value. Use the dividend model above.",
                    title="DCF not shown")
        elif last.empty or not last.get("Free cash flow", 0) > 0 or not last.get("Shares", 0) > 0:
            st.info("Needs a positive free cash flow and the number of shares for the last year.",
                    title="Not enough data")
        else:
            rev_cagr = growth_quality(fin)["rev_cagr5"]
            c1, c2, c3 = st.columns(3)
            with c1:
                g = pct_slider("Cash-flow growth, next 5 years", -5.0, 15.0,
                               min(max(0.0 if pd.isna(rev_cagr) else rev_cagr, 0.0), 0.10), "dcf_g",
                               "Default: revenue growth over the last 5 years, between 0% and 10%.")
            with c2:
                tg = pct_slider("Growth after that", 0.0, 4.0, 0.02, "dcf_tg", "Long-run growth forever. Default 2%.")
            with c3:
                r = pct_slider("Discount rate", 5.0, 15.0, 0.09, "dcf_r", "The yearly return you want. Default 9%.")
            net_debt = float(np.nan_to_num(last.get("Total debt", 0.0)) - np.nan_to_num(last.get("Cash", 0.0)))
            st.caption(f"Free cash flow {fin.index[-1]}: {baht(last['Free cash flow'])} THB; net debt "
                       f"{baht(net_debt)} THB; shares {baht(last['Shares'])}.")
            dcf = lambda rr, gg: dcf_value(last["Free cash flow"], gg, 5, tg, rr, net_debt, last["Shares"])  # noqa: E731
            try:
                show_fair_value("DCF", dcf(r, g), price)
            except ValueError as e:
                st.error(str(e), title="Can't compute")
            show_sensitivity(sensitivity(dcf, [r - 0.01, r, r + 0.01], [g - 0.01, g, g + 0.01]),
                             "r", "g", f"{symbol} DCF fair value for discount rate and growth ±1 point")

        st.subheader("Piotroski F-score")
        score = piotroski(fin)
        if not score.available:
            st.info("No yearly financials to score.", title="No data")
        else:
            st.metric("F-score", f"{score.points} / {score.available}", border=True, width="content",
                      help="One point per check passed (last year vs. the year before). Checks without free "
                           "data are left out, so the maximum is the number available.")
            st.markdown("\n".join(f"- {'✅' if ok else '❌' if ok is False else '➖'} {name}"
                                   + (" (no data)" if ok is None else "") for name, ok in score.checks.items()))

# ============ Prediction (from step 2) ============
if t_pred.open:
    with t_pred:
        st.markdown(
            "A Random Forest model predicts whether **tomorrow's close will be higher than today's**. "
            "It is trained on the older 80% of 5 years of data and tested on the newest 20% it has never seen."
        )
        try:
            with st.spinner("Training model..."):
                result = cache.backtest(symbol)
        except (ValueError, cache.NoPriceData) as e:
            st.warning(str(e), title="Can't train the model")
            st.stop()

        with st.container(horizontal=True):
            st.metric("Model accuracy (test)", f"{result.accuracy:.1%}", border=True, height="stretch")
            st.metric("Baseline accuracy", f"{result.baseline_accuracy:.1%}", border=True, height="stretch",
                      help="Always guessing the most common direction. The model is only useful if it beats this.")
            st.metric("Next day: chance of going up", f"{result.next_day_prob_up:.0%}", border=True, height="stretch")

        edge = result.accuracy - result.baseline_accuracy
        if edge > 0.02:
            st.success(f"The model is {edge:+.1%} more accurate than the baseline on unseen data.",
                       title="The model has an edge")
        else:
            st.info(f"The model is {edge:+.1%} vs. the baseline. "
                    "This is normal: daily stock moves are very close to random.", title="No real edge")

        st.subheader("Backtest: 1 baht invested in the test period")
        eq = result.test
        st.line_chart(
            eq[["Buy_and_hold", "Model_strategy"]].rename(
                columns={"Buy_and_hold": "Buy & hold", "Model_strategy": "Model strategy"}),
            y_label="Value of 1 baht",
            alt=f"Growth of 1 baht in {symbol}: buy and hold versus holding only on days the model predicts up",
        )
        st.caption(f"Model strategy = hold only on days the model predicts 'up' ({eq['Prediction'].mean():.0%} "
                   "of test days). Ignores trading fees and taxes.")
        st.subheader("Which features the model relied on")
        st.bar_chart(result.feature_importance, horizontal=True,
                     alt="Feature importance of the Random Forest model")
