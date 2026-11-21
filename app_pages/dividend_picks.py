from typing import cast

import pandas as pd
import streamlit as st

from src import cache, safety
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


INFO_MARK = ":blue[:material/info:]"


def side_text(sig: dict[str, sg.Signal], side: str) -> str:
    """Markdown for one side of a card: a count, the signals that are on, then the rest in one grey line."""
    mine = [s for s in sig.values() if sg.SIGNALS[s.key].side == side]
    on = [s for s in mine if s.on]
    lines = [f"**{t(f'pk.{side}_count', on=len(on), total=len(mine))}**"]
    mark = ":green[:material/check_circle:]" if side == "buy" else ":red[:material/warning:]"
    lines += [f"{mark} {s.short}" for s in on]
    if not on:
        lines.append(f":gray[{t('pk.no_buy')}]" if side == "buy"
                     else f":green[:material/check_circle:] {t('pk.no_sell')}")
    off = [s.short for s in mine if not s.on and s.short]
    if off:
        lines.append(f":gray[{t('pk.not_on', names=' · '.join(off))}]")
    return "  \n".join(lines)


def days_to_xd(snap) -> int | None:
    ex = None if snap is None else snap.get("ex_div_date")
    if ex is None or pd.isna(ex):
        return None
    days = (pd.Timestamp(ex).date() - today.date()).days
    return days if days >= 0 else None


st.subheader(t("pk.signals_title"))
st.caption(t("pk.signals_caption"))
for _, r in table.iterrows():
    symbol = r["symbol"]
    snap = snaps.loc[symbol] if symbol in snaps.index else None
    sig = sg.compute(data[symbol], today, rank=r["rank"], stage=r["stage"], market_close=market,
                     ex_div_date=None if snap is None else snap.get("ex_div_date"), today=today.date(), lang=lang)
    head = f"#### {int(r['rank'])}. {symbol} — {r['name']}"
    if show_buy and sg.buy_now(sig, r["rank"]):
        head += f"  :green-badge[{t('pk.buy_now')}]"
    if show_sell and sg.sell_now(sig):
        head += f"  :red-badge[{t('pk.sell')}]"
    facts = t("pk.summary", price=float(data[symbol].close.iloc[-1]), yield_=r["div_yield"])
    days = days_to_xd(snap)
    if days is not None:
        facts += " · " + t("pk.summary_xd", days=days)
    with st.container(border=True, key=f"card-pick-{symbol}"):
        st.markdown(head)
        st.caption(facts)
        buy, sell = st.columns(2)
        buy.markdown(side_text(sig, "buy"))
        sell.markdown(side_text(sig, "sell"))
        if "yield_vs_5y" in sig:
            st.markdown(f"{INFO_MARK} {sig['yield_vs_5y'].label}")
        grade = safety.grade(data[symbol], r["sector"], today, lang=lang)
        # Only the checks that are not good, to keep the card short (the stock page lists all of them).
        concerns = [line for c, line in zip(grade.checks, safety.reason_lines(grade)) if c.status != "good"]
        st.markdown("  \n".join([f"**{t('safety.label')}** {safety.badge(grade.level, lang)}", *concerns]))
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
