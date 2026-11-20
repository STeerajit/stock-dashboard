from datetime import date
from typing import cast

import numpy as np
import pandas as pd
import streamlit as st

from src import cache
from src.charts import price_chart
from src.fundamentals import (SCORE_COLUMNS, SnapshotError, growth_quality, pe_history, sector_medians, snapshot_for,
                              yield_history)
from src.i18n import current_lang, t
from src.indicators import support_resistance
from src.portfolio import last_full_year_dps
from src.scoring import piotroski
from src.set_links import set_links
from src.universe import OUTSIDE_SET100, describe, is_valid_symbol, set100_expiry_warning
from src.valuation import DEFAULT_REQUIRED_RETURN, dcf_value, ddm_value, default_ddm_growth, sensitivity

lang = current_lang()


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


def fin_label(column: str) -> str:
    """Display name of a financials column (FIN_COLUMNS) in the current language."""
    return t(f"fin.{column}")


universe = cache.set100()
# Options are plain symbols so the URL can be shared as ?symbol=PTT (a format_func
# would change the option labels and the URL value would no longer match).
# accept_new_options: any Thai stock can be typed in (or put in the URL), not only SET100.
symbol = st.selectbox(t("stock.select"), universe["symbol"].tolist(), key="symbol", bind="query-params",
                      accept_new_options=True, help=t("stock.select_help"))
symbol = symbol.strip().upper()
if not is_valid_symbol(symbol):
    st.error(t("stock.invalid"), title=t("stock.invalid_title"))
    st.stop()
name, sector = describe(universe, symbol)
in_set100 = sector != OUTSIDE_SET100
st.title(f"{symbol} · {name}")
st.caption(sector)
if expiry_warning := set100_expiry_warning(date.today(), lang=lang):
    st.warning(expiry_warning, title=t("common.list_expired_title"))

with st.popover(t("stock.set_links"), icon=":material/open_in_new:"):
    st.caption(t("stock.set_links_caption"))
    for link in set_links(symbol, lang):
        st.markdown(f"- [{link.label}]({link.url})" + (t("stock.all_stocks", symbol=symbol) if link.market_wide else ""))

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
    [t("tab.trading"), t("tab.chart"), t("tab.financials"), t("tab.valuation"), t("tab.dividends"), t("tab.fair"),
     t("tab.prediction")],
    key="tab", on_change="rerun",
)
t_trade, t_chart, t_fin, t_val, t_div, t_fair, t_pred = tabs

# ============ 1. Trading: how much is the market paying attention? ============
if t_trade.open:
    with t_trade:
        need_snapshot()
        vol_ratio = snap["volume"] / snap["avg_volume"] if snap["avg_volume"] else np.nan
        with st.container(horizontal=True):
            st.metric(t("common.price"), num(snap["price"]), pct(snap["change_pct"], 2), border=True, height="stretch")
            st.metric(t("trade.volume"), baht(snap["volume"]),
                      t("trade.vol_ratio", ratio=vol_ratio) if pd.notna(vol_ratio) else None,
                      delta_color="off", border=True, height="stretch", help=t("trade.volume_help"))
            st.metric(t("trade.value"), baht(snap["value_traded"]), border=True, height="stretch")
            st.metric(t("trade.market_cap"), baht(snap["market_cap"]), border=True, height="stretch")
        with st.container(horizontal=True):
            st.metric(t("trade.bid_offer"), f"{num(snap['bid'])} / {num(snap['ask'])}", border=True, height="stretch",
                      help=t("trade.bid_offer_help"))
            st.metric(t("trade.high52"), num(snap["high_52w"]), border=True, height="stretch")
            st.metric(t("trade.low52"), num(snap["low_52w"]), border=True, height="stretch")
            st.metric(t("trade.pos52"), pct(snap["pos_52w"], 0), border=True, height="stretch",
                      help=t("trade.pos52_help"))
            st.metric(t("trade.free_float"), pct(snap["free_float"], 0), border=True, height="stretch",
                      help=t("trade.free_float_help"))
        if pd.notna(vol_ratio) and vol_ratio >= 2:
            st.info(t("trade.high_activity", ratio=vol_ratio), title=t("trade.high_activity_title"))

# ============ 4. Chart: trend, support/resistance, MA, RSI, volume ============
if t_chart.open:
    with t_chart:
        period = st.segmented_control(t("chart.period"), ["3M", "6M", "1Y", "2Y", "5Y"], default="1Y", key="period",
                                      required=True)
        days = {"3M": 63, "6M": 126, "1Y": 250, "2Y": 500, "5Y": 1250}[period]
        try:
            df = cache.prices(symbol).tail(days)
        except cache.NoPriceData as e:
            st.warning(str(e), title=t("chart.no_prices"))
            st.stop()
        supports, resistances = support_resistance(df)
        st.plotly_chart(price_chart(df, symbol, supports, resistances, lang), alt=t("chart.alt", symbol=symbol))
        st.caption(t("chart.note"))

# ============ 2. Financials: is the business good and strong? ============
if t_fin.open:
    with t_fin:
        fin = cache.financials(symbol)
        if fin.empty:
            st.warning(t("fin.none"), title=t("common.no_data"))
        else:
            if fallback_note := fin.attrs.get("fallback_note"):
                st.warning(fallback_note, title=t("fin.short_title"))
            src = fin.attrs.get("source", "?")
            st.caption(t("fin.caption", first=fin.index.min(), last=fin.index.max(), years=len(fin), source=src))
            last = fin.iloc[-1]
            with st.container(horizontal=True):
                st.metric(fin_label("Revenue"), baht(last["Revenue"]), pct(last["Revenue growth"]), border=True,
                          height="stretch")
                st.metric(fin_label("Net income"), baht(last["Net income"]), pct(last["Net income growth"]),
                          border=True, height="stretch")
                st.metric(fin_label("ROE"), pct(last["ROE"]), border=True, height="stretch")
                st.metric(fin_label("D/E"), num(last["D/E"]), border=True, height="stretch",
                          help=t("fin.de_help", definition=fin.attrs.get("de_definition", t("fin.de_default"))))
                st.metric(fin_label("Free cash flow"), baht(last["Free cash flow"]), border=True, height="stretch",
                          help=t("fin.fcf_help"))

            def labelled(df: pd.DataFrame) -> pd.DataFrame:
                return df.rename(index=str, columns=fin_label)

            left, right = st.columns(2)
            with left:
                st.subheader(t("fin.rev_ni"))
                st.bar_chart(labelled(fin[["Revenue", "Net income"]] / 1e9), stack=False,
                             y_label=t("fin.billion"), alt=t("fin.rev_ni_alt", symbol=symbol))
            with right:
                st.subheader(t("fin.margins"))
                st.line_chart(labelled(fin[["Gross margin", "Net margin", "ROE"]]),
                              alt=t("fin.margins_alt", symbol=symbol))

            st.subheader(fin_label("Free cash flow"))
            st.bar_chart((fin["Free cash flow"] / 1e9).rename(fin_label("Free cash flow")).rename(index=str),
                         y_label=t("fin.billion"), alt=t("fin.fcf_alt", symbol=symbol))
            if sector in ("Banking", "Finance & Securities", "Insurance"):
                st.caption(t("fin.fcf_banks"))

            table = fin.drop(columns=["P/E", "P/BV", *SCORE_COLUMNS]).T
            table.columns = [str(c) for c in table.columns]
            fmt = {"Revenue": baht, "Net income": baht, "Free cash flow": baht, "EPS": num, "D/E": num}
            shown = table.apply(lambda r: r.map(fmt.get(r.name, pct)), axis=1).rename(index=fin_label)
            st.dataframe(shown, alt=t("fin.table_alt", symbol=symbol))

# ============ 3. Valuation: expensive or cheap? ============
if t_val.open:
    with t_val:
        need_snapshot()
        st.caption(t("val.vs_peers", sector=sector) if in_set100 else t("val.no_peers"))

        def vs(value, median):
            return t("val.vs_sector", diff=value / median - 1) if pd.notna(value) and pd.notna(median) and median \
                else None

        with st.container(horizontal=True):
            st.metric("P/E", num(snap["pe"], 1), vs(snap["pe"], medians["pe"]), delta_color="inverse",
                      border=True, height="stretch", help=t("val.sector_median", value=num(medians["pe"], 1)))
            st.metric("P/BV", num(snap["pbv"]), vs(snap["pbv"], medians["pbv"]), delta_color="inverse",
                      border=True, height="stretch", help=t("val.sector_median", value=num(medians["pbv"])))
            st.metric(t("val.div_yield"), pct(snap["div_yield"]), vs(snap["div_yield"], medians["div_yield"]),
                      border=True, height="stretch", help=t("val.sector_median", value=pct(medians["div_yield"])))
        st.caption(t("val.colors"))

        st.subheader(t("val.history"))
        fin = cache.financials(symbol)
        history = fin[["P/E", "P/BV"]].copy() if not fin.empty else pd.DataFrame()
        if not history.empty and history["P/E"].count() < 2:
            # Yahoo fallback has no yearly P/E: approximate it from year-end prices and EPS.
            try:
                history["P/E"] = pe_history(cache.prices(symbol), fin)
            except cache.NoPriceData:
                pass

        # Options are fixed keys; only their labels are translated (so the chosen metric survives a language switch).
        metric = st.segmented_control(t("val.metric"), ["P/E", "P/BV", "Dividend yield"], default="P/E",
                                      format_func=lambda m: t("val.metric_yield") if m == "Dividend yield" else m,
                                      key="val_metric", required=True)
        metric_label = t("val.metric_yield") if metric == "Dividend yield" else metric
        if metric == "Dividend yield":
            try:
                series = yield_history(cache.dividends(symbol), cache.unadjusted_close(symbol), date.today().year)
            except cache.NoPriceData:
                series = pd.Series(dtype=float)
        else:
            series = history[metric].dropna() if metric in history else pd.Series(dtype=float)
        median_label = t("val.median_series", years=len(series))
        if len(series) < 2:
            st.info(t("val.no_history", metric=metric_label), title=t("val.no_history_title"))
        elif metric == "Dividend yield":
            median = series.median()
            st.line_chart(pd.DataFrame({t("val.yield_series"): series * 100,
                                        median_label: median * 100}).rename(index=str),
                          y_label="%", alt=t("val.yield_alt", symbol=symbol))
            current = snap["div_yield"]
            if pd.notna(current):
                pp = (current - median) * 100
                verdict = t("val.cheaper") if pp > 0 else t("val.dearer")  # a higher yield means a lower price
                st.markdown(t("val.yield_verdict", current=pct(current), pp=pp, years=len(series), median=pct(median),
                              verdict=verdict))
            st.caption(t("val.yield_note"))
        else:
            median = series.median()
            st.line_chart(pd.DataFrame({metric: series, median_label: median}).rename(index=str),
                          alt=t("val.history_alt", symbol=symbol, metric=metric))
            current = {"P/E": snap["pe"], "P/BV": snap["pbv"]}[metric]
            if pd.notna(current) and median:
                diff = current / median - 1
                st.markdown(t("val.verdict", metric=metric, current=num(current), diff=abs(diff),
                              direction=t("val.below") if diff < 0 else t("val.above"), years=len(series),
                              median=num(median), verdict=t("val.cheaper") if diff < 0 else t("val.dearer")))
            st.caption(t("val.history_note", source=fin.attrs.get("source", "?")))

# ============ 8 (partly). Dividends & calendar ============
if t_div.open:
    with t_div:
        need_snapshot()
        with st.container(horizontal=True):
            st.metric(t("div.xd"), snap["ex_div_date"].strftime("%d %b %Y") if pd.notna(snap["ex_div_date"])
                      else "–", border=True, height="stretch")
            st.metric(t("div.earnings"), snap["earnings_date"].strftime("%d %b %Y")
                      if pd.notna(snap["earnings_date"]) else "–", border=True, height="stretch",
                      help=t("div.earnings_help"))
            st.metric(t("val.div_yield"), pct(snap["div_yield"]), border=True, height="stretch")
        div = cache.dividends(symbol)
        if div.empty:
            st.info(t("div.none"), title=t("div.none_title"))
        else:
            st.subheader(t("div.per_year"))
            st.bar_chart(div.tail(15).rename(index=str), alt=t("div.alt", symbol=symbol))
            st.caption(t("div.note"))

# ============ Fair value and F-score (backlog #13) ============
FINANCIAL_SECTORS = ("Banking", "Finance & Securities", "Insurance")


def pct_slider(label: str, low: float, high: float, default: float, key: str, help: str) -> float:
    """A slider in percent (e.g. 8.0) that returns a fraction (0.08)."""
    value = st.slider(label, low, high, float(min(max(round(default * 100 * 2) / 2, low), high)), step=0.5,
                      format="%.1f%%", key=key, help=help)
    return value / 100


def show_fair_value(model: str, fair: float, price: float) -> None:
    if fair <= 0:
        st.info(t("fair.no_value", model=model), title=t("fair.no_value_title"))
        return
    with st.container(horizontal=True):
        st.metric(t("fair.value", model=model), num(fair), border=True, height="stretch")
        st.metric(t("fair.price_now"), num(price), border=True, height="stretch")
        st.metric(t("fair.margin"), pct(fair / price - 1, 0), border=True, height="stretch",
                  help=t("fair.margin_help"))


def show_sensitivity(table: pd.DataFrame, r_label: str, g_label: str, alt: str) -> None:
    shown = table.copy()
    shown.index = [f"{r_label} {r:.1%}" for r in shown.index]
    shown.columns = [f"{g_label} {g:.1%}" for g in shown.columns]
    st.dataframe(shown.map(lambda v: num(v)), alt=alt)


if t_fair.open:
    with t_fair:
        need_snapshot()
        price = snap["price"]
        st.info(t("fair.estimate"), title=t("fair.estimate_title"), icon=":material/info:")
        this_year = date.today().year

        st.subheader(t("fair.ddm"))
        div = cache.dividends(symbol)
        last_dps = last_full_year_dps(div, this_year)
        if pd.isna(last_dps) or last_dps <= 0:
            st.info(t("fair.no_dividend", symbol=symbol, year=this_year - 1), title=t("fair.no_dividend_title"))
        else:
            c1, c2 = st.columns(2)
            with c1:
                g = pct_slider(t("fair.ddm_g"), -5.0, 10.0, default_ddm_growth(div, this_year), "ddm_g",
                               t("fair.ddm_g_help"))
            with c2:
                r = pct_slider(t("fair.ddm_r"), 4.0, 15.0, DEFAULT_REQUIRED_RETURN, "ddm_r", t("fair.ddm_r_help"))
            st.caption(t("fair.ddm_note", year=this_year - 1, dps=num(last_dps), next=num(last_dps * (1 + g)), g=g))
            try:
                show_fair_value("DDM", ddm_value(last_dps * (1 + g), g, r), price)
            except ValueError as e:
                st.error(str(e), title=t("fair.cant"))
            show_sensitivity(sensitivity(lambda rr, gg: ddm_value(last_dps * (1 + gg), gg, rr),
                                         [r - 0.01, r, r + 0.01], [g - 0.01, g, g + 0.01]),
                             "r", "g", t("fair.ddm_alt", symbol=symbol))

        st.subheader(t("fair.dcf"))
        fin = cache.financials(symbol)
        last = fin.iloc[-1] if not fin.empty else pd.Series(dtype=float)
        if sector in FINANCIAL_SECTORS:
            st.info(t("fair.no_dcf"), title=t("fair.no_dcf_title"))
        elif last.empty or not last.get("Free cash flow", 0) > 0 or not last.get("Shares", 0) > 0:
            st.info(t("fair.not_enough"), title=t("fair.not_enough_title"))
        else:
            rev_cagr = growth_quality(fin)["rev_cagr5"]
            c1, c2, c3 = st.columns(3)
            with c1:
                g = pct_slider(t("fair.dcf_g"), -5.0, 15.0,
                               min(max(0.0 if pd.isna(rev_cagr) else rev_cagr, 0.0), 0.10), "dcf_g",
                               t("fair.dcf_g_help"))
            with c2:
                tg = pct_slider(t("fair.dcf_tg"), 0.0, 4.0, 0.02, "dcf_tg", t("fair.dcf_tg_help"))
            with c3:
                r = pct_slider(t("fair.dcf_r"), 5.0, 15.0, 0.09, "dcf_r", t("fair.dcf_r_help"))
            net_debt = float(np.nan_to_num(last.get("Total debt", 0.0)) - np.nan_to_num(last.get("Cash", 0.0)))
            st.caption(t("fair.dcf_note", year=fin.index[-1], fcf=baht(last["Free cash flow"]), net_debt=baht(net_debt),
                         shares=baht(last["Shares"])))
            dcf = lambda rr, gg: dcf_value(last["Free cash flow"], gg, 5, tg, rr, net_debt, last["Shares"])  # noqa: E731
            try:
                show_fair_value("DCF", dcf(r, g), price)
            except ValueError as e:
                st.error(str(e), title=t("fair.cant"))
            show_sensitivity(sensitivity(dcf, [r - 0.01, r, r + 0.01], [g - 0.01, g, g + 0.01]),
                             "r", "g", t("fair.dcf_alt", symbol=symbol))

        st.subheader(t("fair.fscore"))
        score = piotroski(fin)
        if not score.available:
            st.info(t("fair.no_scores"), title=t("common.no_data"))
        else:
            st.metric("F-score", f"{score.points} / {score.available}", border=True, width="content",
                      help=t("fair.fscore_help"))
            st.markdown("\n".join(f"- {'✅' if ok else '❌' if ok is False else '➖'} {t(f'check.{check}')}"
                                  + (t("fair.no_check_data") if ok is None else "")
                                  for check, ok in score.checks.items()))

# ============ Prediction (from step 2) ============
if t_pred.open:
    with t_pred:
        st.markdown(t("pred.intro"))
        try:
            with st.spinner(t("pred.training")):
                result = cache.backtest(symbol)
        except (ValueError, cache.NoPriceData) as e:
            st.warning(str(e), title=t("pred.cant_title"))
            st.stop()

        with st.container(horizontal=True):
            st.metric(t("pred.accuracy"), f"{result.accuracy:.1%}", border=True, height="stretch")
            st.metric(t("pred.baseline"), f"{result.baseline_accuracy:.1%}", border=True, height="stretch",
                      help=t("pred.baseline_help"))
            st.metric(t("pred.next_day"), f"{result.next_day_prob_up:.0%}", border=True, height="stretch")

        edge = result.accuracy - result.baseline_accuracy
        if edge > 0.02:
            st.success(t("pred.edge", edge=edge), title=t("pred.edge_title"))
        else:
            st.info(t("pred.no_edge", edge=edge), title=t("pred.no_edge_title"))

        st.subheader(t("pred.periods"))
        w = result.windows
        cols = {k: t(f"pred.col_{k}") for k in ["period", "model", "baseline", "edge"]}
        st.dataframe(
            pd.DataFrame({cols["period"]: [f"{a:%d %b %Y} – {b:%d %b %Y}" for a, b in zip(w["test_start"], w["test_end"])],
                          cols["model"]: w["accuracy"], cols["baseline"]: w["baseline"],
                          cols["edge"]: w["accuracy"] - w["baseline"]}),
            hide_index=True,
            column_config={cols[k]: st.column_config.NumberColumn(cols[k], format="percent")
                           for k in ["model", "baseline", "edge"]},
            alt=t("pred.periods_alt", symbol=symbol),
        )
        st.caption(t("pred.average", count=len(w), model=w["accuracy"].mean(), baseline=w["baseline"].mean()))

        st.subheader(t("pred.backtest"))
        eq = result.test
        st.line_chart(
            eq[["Buy_and_hold", "Model_strategy", "Model_before_costs"]].rename(columns={
                "Buy_and_hold": t("pred.buy_hold"), "Model_strategy": t("pred.after_costs"),
                "Model_before_costs": t("pred.before_costs")}),
            y_label=t("pred.value_axis"),
            alt=t("pred.backtest_alt", symbol=symbol),
        )
        trades = int(eq["Prediction"].diff().abs().fillna(eq["Prediction"]).sum())
        st.caption(t("pred.note", share=eq["Prediction"].mean(), cost=result.cost_per_trade, trades=trades))
        st.subheader(t("pred.features"))
        st.bar_chart(result.feature_importance, horizontal=True, alt=t("pred.features_alt"))
