from datetime import date

import pandas as pd
import streamlit as st

from src import cache, income, portfolio, safety
from src import dividend_picks as dp
from src.fundamentals import SnapshotError
from src.i18n import current_lang, t

st.title(t("port.title"))
# Public demo: holdings stay in this visitor's session, never in a file on the server (see portfolio.public_mode).
public = portfolio.public_mode()
st.caption(t("port.caption_public" if public else "port.caption"))
if public:
    st.info(t("port.public"), title=t("port.public_title"), icon=":material/public:")
saved = st.session_state.get("demo_holdings", portfolio.empty()) if public else portfolio.load()
last_year = date.today().year - 1
caps = st.session_state.get("conc_caps", portfolio.DEFAULT_CAPS)


def keep_caps() -> None:
    """Copy the cap inputs to a session key no widget owns: widget keys are dropped when another page is open,
    and Today reads the caps too."""
    st.session_state["conc_caps"] = {k: st.session_state[f"cap_{k}"] / 100 for k in portfolio.DEFAULT_CAPS}


def safety_level(symbol: str, sector: str) -> str | None:
    """The dividend safety grade of a held stock, as text. In public mode a stock not in the store costs about
    2 thaifin fetches (yearly and quarterly statements), once a day. None if its data can't be loaded."""
    try:
        d = dp.StockData(pd.DataFrame(), pd.Series(dtype=float), cache.dividend_events(symbol),
                         cache.financials(symbol), cache.quarterly(symbol))
    except Exception:  # one stock failing (network, bad data) must not break the page
        return None
    return t(f"safety.level.{safety.grade(d, sector, pd.Timestamp(date.today()), lang=current_lang()).level}")


if saved.empty:
    st.info(t("port.empty"), title=t("port.empty_title"))
else:
    try:
        pos = portfolio.positions(saved, cache.quotes(saved["symbol"].tolist()))
    except SnapshotError as e:
        st.warning(str(e), title=SnapshotError.title)
    else:
        pos["safety"] = [safety_level(sym, sector) if shares > 0 else None
                         for sym, sector, shares in zip(pos["symbol"], pos["sector"], pos["shares"])]
        tot = portfolio.totals(pos)
        with st.container(horizontal=True):
            st.metric(t("port.value"), f"{tot['value']:,.0f}", border=True, height="stretch")
            st.metric(t("port.pnl"), f"{tot['pnl']:+,.0f}",
                      f"{tot['pnl_pct']:+.1%}" if pd.notna(tot["pnl_pct"]) else None, border=True, height="stretch",
                      help=t("port.pnl_help", cost=f"{tot['cost']:,.0f}"))
            st.metric(t("port.dividend"), f"{tot['est_dividend']:,.0f}", border=True,
                      height="stretch", help=t("port.dividend_help", year=last_year))
            st.metric(t("port.yoc"), f"{tot['yield_on_cost']:.2%}" if pd.notna(tot["yield_on_cost"]) else "–",
                      border=True, height="stretch", help=t("port.yoc_help"))

        if missing := pos.loc[(pos["shares"] > 0) & pos["price"].isna(), "symbol"].tolist():
            st.warning(t("port.missing", symbols=", ".join(missing)), title=t("port.missing_title"))
        if breaches := portfolio.concentration(pos, caps):
            st.warning("\n".join(f"- {portfolio.breach_text(b, current_lang())}" for b in breaches),
                       title=t("conc.title"), icon=":material/pie_chart:")

        nc = st.column_config.NumberColumn
        st.dataframe(
            pos.sort_values(["value", "symbol"], ascending=[False, True]),
            hide_index=True,
            column_order=["symbol", "sector", "shares", "avg_cost", "price", "value", "pnl", "pnl_pct",
                          "est_dividend", "yield_on_cost", "safety"],
            column_config={
                "symbol": st.column_config.TextColumn(t("common.symbol"), pinned=True),
                "sector": st.column_config.TextColumn(t("common.sector")),
                "shares": nc(t("port.shares"), format="localized", help=t("port.shares_help")),
                "avg_cost": nc(t("port.avg_cost"), format="%.2f"),
                "price": nc(t("common.price"), format="%.2f"),
                "value": nc(t("port.col_value"), format="localized"),
                "pnl": nc(t("port.col_pnl"), format="localized"),
                "pnl_pct": nc(t("port.col_pnl_pct"), format="percent"),
                "est_dividend": nc(t("port.col_dividend"), format="localized",
                                   help=t("port.col_dividend_help", year=last_year)),
                "yield_on_cost": nc(t("port.yoc"), format="percent"),
                "safety": st.column_config.TextColumn(t("safety.col"), help=t("safety.col_help")),
            },
            alt=t("port.table_alt"),
        )

        # The calendar loads only when its tab is open (an expander would run its code on every rerun).
        t_alloc, t_income = st.tabs([t("port.allocation"), t("income.tab")], key="port_tab", on_change="rerun")
        if t_alloc.open:
            with t_alloc:
                alloc = portfolio.allocation(pos)
                if not alloc.empty:
                    st.bar_chart((alloc * 100).round(1).rename(t("port.alloc_series")), horizontal=True,
                                 x_label=t("port.alloc_axis"), alt=t("port.alloc_alt"))
        if t_income.open:
            with t_income:
                priced = pos[pos["value"].notna()]  # like the totals: held stocks with a price
                shares = dict(zip(priced["symbol"], priced["shares"]))
                events = {sym: cache.dividend_events(sym) for sym in shares}
                cal = income.monthly(events, shares, date.today().year)
                months = income.by_month(cal)
                st.caption(t("income.note", year=last_year))
                with st.container(horizontal=True):
                    for key, col in [("income.gross", "gross"), ("income.tax", "tax"), ("income.net", "net")]:
                        st.metric(t(key), f"{months[col].sum():,.0f}", border=True, height="stretch")
                names = t("income.months").split()
                st.bar_chart((cal * (1 - income.TAX)).set_axis(names), sort=False, x_label=t("income.axis"),
                             y_label=t("income.net"), alt=t("income.chart_alt"))
                st.dataframe(
                    months.set_axis(names).rename_axis("month").reset_index(), hide_index=True,
                    column_config={"month": st.column_config.TextColumn(t("income.col_month")),
                                   "gross": nc(t("income.col_gross"), format="localized"),
                                   "tax": nc(t("income.col_tax"), format="localized"),
                                   "net": nc(t("income.col_net"), format="localized")},
                    alt=t("income.months_alt"),
                )
                st.dataframe(
                    income.summary(pos, cal, events, date.today().year), hide_index=True,
                    column_config={
                        "symbol": st.column_config.TextColumn(t("common.symbol"), pinned=True),
                        "gross": nc(t("income.col_gross"), format="localized"),
                        "net": nc(t("income.col_net"), format="localized"),
                        "net_yield_on_cost": nc(t("income.col_net_yoc"), format="percent",
                                                help=t("income.col_net_yoc_help")),
                        "no_recent": st.column_config.CheckboxColumn(
                            t("income.col_no_recent"), help=t("income.col_no_recent_help", year=last_year)),
                        "may_shift": st.column_config.CheckboxColumn(
                            t("income.col_may_shift"),
                            help=t("income.col_may_shift_help", before=last_year - 1, year=last_year)),
                    },
                    alt=t("income.stocks_alt"),
                )
        st.caption(t("port.note", year=last_year))

        st.subheader(t("conc.caps"))
        with st.container(horizontal=True):
            for kind in portfolio.DEFAULT_CAPS:
                st.number_input(t(f"conc.cap_{kind}"), min_value=1, max_value=100, value=round(caps[kind] * 100),
                                step=1, key=f"cap_{kind}", on_change=keep_caps, help=t(f"conc.cap_{kind}_help"))
        st.caption(t("conc.caps_note"))

st.subheader(t("port.edit"))
with st.form("holdings_form", border=False):
    edited = st.data_editor(
        saved,
        key="holdings",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "symbol": st.column_config.TextColumn(t("common.symbol"), help=t("port.symbol_help")),
            "shares": st.column_config.NumberColumn(t("port.shares"), min_value=0, step=1, format="%d",
                                                    help=t("port.shares_edit_help")),
            "avg_cost": st.column_config.NumberColumn(t("port.avg_cost_edit"), min_value=0, format="%.2f",
                                                      help=t("port.avg_cost_edit_help")),
        },
    )
    submitted = st.form_submit_button(t("port.save"), icon=":material/save:", type="primary")

if submitted:
    holdings, problems = portfolio.clean(edited, lang=current_lang())
    if problems:
        st.error(t("port.not_saved") + "\n" + "\n".join(f"- {p}" for p in problems), title=t("port.check_title"))
    else:
        if public:
            st.session_state["demo_holdings"] = holdings
        else:
            portfolio.save(holdings)
        # The editor's state holds edits relative to the old table; drop it so the saved file is shown as-is
        # (otherwise added rows would be added a second time on top of the reloaded file).
        st.session_state.pop("holdings", None)
        st.session_state["saved_count"] = len(holdings)
        st.rerun()

if (count := st.session_state.pop("saved_count", None)) is not None:
    st.toast(t("port.saved", count=count), icon=":material/check:")
