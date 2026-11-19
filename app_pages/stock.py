import numpy as np
import pandas as pd
import streamlit as st

from src import cache
from src.charts import price_chart
from src.fundamentals import pe_history, sector_medians
from src.indicators import support_resistance


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


universe = cache.set50()
# Options are plain symbols so the URL can be shared as ?symbol=PTT (a format_func
# would change the option labels and the URL value would no longer match).
symbol = st.selectbox("Stock", universe["symbol"].tolist(), key="symbol", bind="query-params")
row = universe.set_index("symbol").loc[symbol]
st.title(f"{symbol} · {row['name']}")
st.caption(row["sector"])

snaps = cache.snapshots()
snap = snaps.set_index("symbol").loc[symbol]
medians = sector_medians(snaps, universe).loc[row["sector"]]

tabs = st.tabs(
    [":material/swap_vert: Trading", ":material/candlestick_chart: Chart", ":material/account_balance: Financials",
     ":material/sell: Valuation", ":material/event: Dividends & calendar", ":material/online_prediction: Prediction"],
    key="tab", on_change="rerun",
)
t_trade, t_chart, t_fin, t_val, t_div, t_pred = tabs

# ============ 1. Trading: how much is the market paying attention? ============
if t_trade.open:
    with t_trade:
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
            if row["sector"] in ("Banking", "Finance & Securities", "Insurance"):
                st.caption("For banks, lenders and insurers, lending and investing are the business itself, "
                           "so free cash flow swings widely and is not a useful health measure.")

            table = fin.drop(columns=["P/E", "P/BV"]).T
            table.columns = [str(c) for c in table.columns]
            fmt = {"Revenue": baht, "Net income": baht, "Free cash flow": baht, "EPS": num, "D/E": num}
            shown = table.apply(lambda r: r.map(fmt.get(r.name, pct)), axis=1)
            st.dataframe(shown, alt=f"{symbol} yearly financial figures")

# ============ 3. Valuation: expensive or cheap? ============
if t_val.open:
    with t_val:
        st.caption(f"Compared with the median of SET50 stocks in {row['sector']}.")

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

        metric = st.segmented_control("Metric", ["P/E", "P/BV"], default="P/E", key="val_metric",
                                      required=True)
        series = history[metric].dropna() if metric in history else pd.Series(dtype=float)
        if len(series) < 2:
            st.info(f"Not enough yearly {metric} history for this stock.", title="No history")
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
