import json

import numpy as np
import pandas as pd
import pytest

from src import dividend_picks as dp
from src import picks_backtest as bt
from tests.test_dividend_picks import dividends, financials, stock


def flat(symbol_returns: dict[str, list[float]], dates: list[pd.Timestamp]) -> dict[str, dp.StockData]:
    """Stocks whose close moves by the given monthly returns between consecutive month ends."""
    out = {}
    for s, rets in symbol_returns.items():
        close = pd.Series(100 * np.cumprod([1.0, *[1 + r for r in rets]]), index=dates)
        prices = pd.DataFrame({"Close": close})
        out[s] = dp.StockData(prices, close, pd.Series(dtype=float), pd.DataFrame())
    return out


DATES = list(pd.date_range("2025-01-31", periods=4, freq="ME"))


def test_month_ends_stop_at_the_last_complete_month():
    dates = bt.month_ends(pd.Timestamp("2026-11-20"), years=1)
    assert dates[0] == pd.Timestamp("2025-10-31") and dates[-1] == pd.Timestamp("2026-10-31") and len(dates) == 13
    assert bt.month_ends(pd.Timestamp("2026-10-31"), years=1)[-1] == pd.Timestamp("2026-10-31")


def test_simulate_weighs_each_slot_one_tenth_and_charges_turnover():
    data = flat({"A": [0.10, 0.0, 0.0]}, DATES)
    rets, turns = bt.simulate(DATES, data, lambda day, held: ["A"], cost=0.01)
    assert turns.iloc[0] == pytest.approx(0.1)  # buying 1/10 from cash
    assert rets.iloc[0] == pytest.approx(0.1 * 0.10 - 0.1 * 0.01)
    # After +10% the slot drifted to 0.11/1.01; topping it back to 0.1 is a small trade.
    assert turns.iloc[1] == pytest.approx(abs(0.1 - 0.11 / 1.01))


def test_simulate_holding_nothing_earns_nothing():
    rets, turns = bt.simulate(DATES, flat({"A": [0.1, 0.1, 0.1]}, DATES), lambda day, held: [])
    assert rets.tolist() == [0.0, 0.0, 0.0] and turns.sum() == 0


def test_simulate_equal_weights_every_chosen_stock_without_slots():
    data = flat({"A": [0.10, 0, 0], "B": [-0.10, 0, 0]}, DATES)
    rets, _ = bt.simulate(DATES, data, lambda day, held: ["A", "B"], slots=None, cost=0.0)
    assert rets.iloc[0] == pytest.approx(0.0)


def test_stats_on_a_known_series():
    r = pd.Series([0.01] * 12)
    s = bt.stats(r, pd.Series([0.5] * 12))
    assert s["cagr"] == pytest.approx(1.01 ** 12 - 1) and s["max_drawdown"] == 0 and s["turnover"] == 6.0
    assert bt.stats(pd.Series([0.1, -0.5, 0.2] * 4), pd.Series([0.0] * 12))["max_drawdown"] < -0.5


def test_run_reports_base_benchmark_and_every_rule():
    data = {f"S{i:02d}": stock(vol=0.005 + i * 0.0003, seed=i, div=dividends(amount=1 + i / 20),
                               fin=financials(eps=(5,) * 5)) for i in range(15)}
    dates = list(pd.date_range("2025-10-31", periods=4, freq="ME"))
    results = bt.run(data, dates)
    assert results["months"] == 3 and results["stocks"] == 15
    assert set(results["rules"]) == {*bt.BUY_RULES, "rank_out", "below_trend", "buy_now", "sell_now"}
    for r in results["rules"].values():
        assert r["passed"] == (r["cagr"] >= results["base"]["cagr"] + bt.MIN_MARGIN)
    json.dumps(results)  # saveable as is


def test_rule_passed_reads_the_saved_file(tmp_path):
    path = tmp_path / "results.json"
    assert bt.load_results(path) is None and not bt.rule_passed(None, "buy_now")
    path.write_text(json.dumps({"rules": {"buy_now": {"passed": True}, "sell_now": {"passed": False}}}))
    results = bt.load_results(path)
    assert bt.rule_passed(results, "buy_now") and not bt.rule_passed(results, "sell_now")
    path.write_text("not json")
    assert bt.load_results(path) is None


def test_saved_results_match_the_rules_the_app_knows():
    results = bt.load_results()
    if results is None:
        pytest.skip("backtest not run yet")
    assert set(results["rules"]) == {*bt.BUY_RULES, "rank_out", "below_trend", "buy_now", "sell_now"}
    assert {"cagr", "volatility", "max_drawdown", "turnover"} <= set(results["base"])


def test_a_rule_must_beat_the_plain_picks_by_half_a_point(monkeypatch):
    data = {f"S{i:02d}": stock(vol=0.005 + i * 0.0003, seed=i, div=dividends(amount=1 + i / 20),
                               fin=financials(eps=(5,) * 5)) for i in range(15)}
    dates = list(pd.date_range("2025-10-31", periods=4, freq="ME"))
    base = bt.run(data, dates)["base"]["cagr"]
    lead = {"base": base}
    monkeypatch.setattr(bt, "stats", lambda *a: {"cagr": lead.pop("base", None) or lead["rule"]})
    for margin, passed in ((0.004, False), (0.005, True)):
        lead.update(base=base, rule=base + margin)
        assert all(r["passed"] is passed for r in bt.run(data, dates)["rules"].values())
