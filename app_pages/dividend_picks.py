from typing import cast

import pandas as pd
import streamlit as st

from src import cache
from src import dividend_picks as dp
from src import signals as sg
from src.fundamentals import SnapshotError
from src.i18n import current_lang, t
from src.picks_backtest import load_results, rule_passed

lang = current_lang()
st.title(t("pk.title"))
st.caption(t("pk.caption"))

data = cache.picks_data()
if len(data) < dp.LOW_VOL_KEEP:
    st.error(t("pk.too_few", count=len(data)), title=t("pk.too_few_title"))
    st.button(t("common.retry"), icon=":material/refresh:", key="retry")
    st.stop()

days = sorted({day for d in data.values() for day in d.close.index[-2:]})
today, yesterday = days[-1], days[-2]
screened = dp.screen(data, today)
top = dp.picks(screened)
entered, left = dp.changes(top, dp.picks(dp.screen(data, yesterday)))
market = dp.equal_weight_index(data)
results = load_results()
show_buy, show_sell = rule_passed(results, "buy_now"), rule_passed(results, "sell_now")

try:
    snaps = cache.snapshots().set_index("symbol")
except SnapshotError:
    snaps = pd.DataFrame()
universe = cache.set100().set_index("symbol")
growth = cache.growth().set_index("symbol")

st.subheader(t("pk.list_title", date=f"{today:%d %b %Y}"))
if entered:
    st.markdown(t("pk.entered", symbols=", ".join(entered)))
if left:
    st.markdown(t("pk.left", symbols=", ".join(left)))

table = screened[screened["symbol"].isin(top)].copy()
table["name"] = table["symbol"].map(universe["name"])
table["sector"] = table["symbol"].map(universe["sector"])
table["fscore"] = table["symbol"].map(growth["fscore"]) if "fscore" in growth else float("nan")
table["new"] = table["symbol"].isin(entered)
nc = st.column_config.NumberColumn
event = st.dataframe(
    table, hide_index=True, key="picks", on_select="rerun", selection_mode="single-row",
    column_order=["rank", "symbol", "name", "sector", "new", "div_yield", "momentum", "volatility", "payout", "fscore"],
    column_config={
        "rank": nc(t("pk.rank"), format="%d"),
        "symbol": st.column_config.TextColumn(t("common.symbol"), pinned=True),
        "name": st.column_config.TextColumn(t("common.company")),
        "sector": st.column_config.TextColumn(t("common.sector")),
        "new": st.column_config.CheckboxColumn(t("pk.new"), help=t("pk.new_help")),
        "div_yield": nc(t("pk.yield"), format="percent", help=t("pk.yield_help")),
        "momentum": nc(t("pk.momentum"), format="percent", help=t("pk.momentum_help")),
        "volatility": nc(t("pk.volatility"), format="percent", help=t("pk.volatility_help")),
        "payout": nc(t("pk.payout"), format="percent", help=t("pk.payout_help")),
        "fscore": nc("F-score", format="%d", help=t("scr.fscore_help")),
    },
    alt=t("pk.table_alt"),
)
if event.selection.rows:
    symbol = table.iloc[event.selection.rows[0]]["symbol"]
    st.switch_page("app_pages/stock.py", query_params={"symbol": symbol})


def evidence(key: str) -> str:
    meta = sg.SIGNALS[key]
    color = {"strong": "green", "medium": "blue", "weak": "orange", "none": "gray"}[meta.evidence]
    note = f" · {t(f'chk.{meta.checked}')}" if meta.checked != "none" else ""
    source = f" — {meta.source}" if meta.source else ""
    return f":{color}-badge[{t(f'ev.{meta.evidence}')}{note}]{source}"


def show_signals(sig: dict[str, sg.Signal], side: str) -> None:
    for key, s in sig.items():
        if sg.SIGNALS[key].side != side:
            continue
        mark = (":material/check_circle:" if s.on else ":material/remove:") if side != "info" else ":material/info:"
        st.markdown(f"{mark} **{t(f'sig.name.{key}')}** — {s.label}  \n{evidence(key)}")


st.subheader(t("pk.signals_title"))
st.caption(t("pk.signals_caption"))
for _, r in table.iterrows():
    symbol = r["symbol"]
    snap = snaps.loc[symbol] if symbol in snaps.index else None
    sig = sg.compute(data[symbol], today, rank=r["rank"], stage=r["stage"], market_close=market,
                     ex_div_date=None if snap is None else snap.get("ex_div_date"), today=today.date(), lang=lang)
    head = f"{int(r['rank'])}. {symbol} — {r['name']}"
    if show_buy and sg.buy_now(sig, r["rank"]):
        head += f"  ·  :green-badge[{t('pk.buy_now')}]"
    if show_sell and sg.sell_now(sig):
        head += f"  ·  :red-badge[{t('pk.sell')}]"
    with st.expander(head):
        st.markdown(f"**{t('pk.buy_signals')}**")
        show_signals(sig, "buy")
        st.markdown(f"**{t('pk.info_signals')}**")
        show_signals(sig, "info")
        st.markdown(f"**{t('pk.sell_signals')}**")
        show_signals(sig, "sell")
        st.page_link("app_pages/stock.py", label=t("today.open", symbol=symbol), icon=":material/arrow_forward:",
                     query_params={"symbol": symbol})

if not (show_buy and show_sell):
    st.info(t("pk.summary_hidden") if results else t("pk.no_backtest"), title=t("pk.summary_hidden_title"))

if left:
    st.subheader(t("pk.left_title"))
    by_symbol = screened.set_index("symbol")
    for symbol in left:
        stage, rank = str(by_symbol.at[symbol, "stage"]), cast(int, by_symbol.at[symbol, "rank"])
        why = t(f"pk.stage.{stage}") if stage != "ok" else t("pk.ranked", rank=int(rank))
        st.markdown(f"- **{symbol}**: {why}")

st.subheader(t("pk.backtest_title"))
if results:
    rows = [{"rule": t(f"pk.rule.{k}"), "cagr": v["cagr"], "base": results["base"]["cagr"], "passed": v["passed"]}
            for k, v in results["rules"].items()]
    st.markdown(t("pk.backtest_summary", start=results["start"], end=results["end"],
                  picks=results["base"]["cagr"], bench=results["benchmark"]["cagr"]))
    st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={
        "rule": st.column_config.TextColumn(t("pk.rule")),
        "cagr": nc(t("pk.rule_cagr"), format="percent"),
        "base": nc(t("pk.base_cagr"), format="percent"),
        "passed": st.column_config.CheckboxColumn(t("pk.passed")),
    }, alt=t("pk.backtest_alt"))
else:
    st.caption(t("pk.no_backtest"))
st.warning(t("pk.survivorship"), title=t("pk.limits_title"))
st.caption(t("pk.disclaimer"))
