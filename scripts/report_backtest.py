"""Print the backtest results table (Markdown) used in docs/article.md, and optionally save its figures.

Uses the local store (run scripts/update_data.py first), so the numbers are reproducible for the
"Data as of" date printed at the top.

    .venv/bin/python scripts/report_backtest.py
    uv run --no-project --with-requirements requirements.txt --with kaleido==1.5.2 \
        python scripts/report_backtest.py --figures docs/img   # + the two PNG figures
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import store  # noqa: E402
from src.indicators import add_indicators  # noqa: E402
from src.model import BacktestResult, train_and_backtest  # noqa: E402

STOCKS = ["PTT", "ADVANC", "KBANK", "CPALL", "AOT"]  # five large SET50 stocks from different sectors


def last_5_years(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.index > df.index[-1] - pd.DateOffset(years=5)]


def run(symbol: str) -> BacktestResult:
    return train_and_backtest(add_indicators(last_5_years(store.load_prices(store.STORE_PATH, symbol))))


def trades(r: BacktestResult) -> int:
    position = r.test["Prediction"]
    return int(position.diff().abs().fillna(position).sum())


def table(results: dict[str, BacktestResult]) -> str:
    lines = ["| Stock | Model accuracy | Baseline accuracy | Model − baseline | Strategy (after costs) "
             "| Buy & hold | Trades |",
             "|---|---|---|---|---|---|---|"]
    for sym, r in results.items():
        w, eq = r.windows, r.test
        lines.append(f"| {sym} | {w['accuracy'].mean():.1%} | {w['baseline'].mean():.1%} | "
                     f"{w['accuracy'].mean() - w['baseline'].mean():+.1%} | {eq['Model_strategy'].iloc[-1] - 1:+.1%} | "
                     f"{eq['Buy_and_hold'].iloc[-1] - 1:+.1%} | {trades(r)} |")
    return "\n".join(lines)


def figures(results: dict[str, BacktestResult], out: Path) -> None:
    import plotly.graph_objects as go

    out.mkdir(parents=True, exist_ok=True)
    first = max(results, key=lambda s: trades(results[s]))  # the stock where trading costs show the most
    eq = results[first].test
    fig = go.Figure()
    for col, name in [("Buy_and_hold", "Buy & hold"), ("Model_before_costs", "Model, before costs"),
                      ("Model_strategy", "Model, after costs")]:
        fig.add_scatter(x=eq.index, y=eq[col], name=name, mode="lines")
    fig.update_layout(title=f"{first}: 1 baht over the four test periods", yaxis_title="Value of 1 baht",
                      template="plotly_white", width=900, height=500)
    fig.write_image(out / "equity_curve.png", scale=2)

    fig = go.Figure()
    for sym, r in results.items():
        fig.add_bar(x=[f"Period {i + 1}" for i in range(len(r.windows))],
                    y=(r.windows["accuracy"] - r.windows["baseline"]) * 100, name=sym)
    fig.update_layout(title="Model accuracy minus baseline, per walk-forward period",
                      yaxis_title="Percentage points", template="plotly_white", width=900, height=500)
    fig.write_image(out / "accuracy_per_window.png", scale=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figures", type=Path, help="folder to save the two PNG figures in (needs kaleido)")
    args = parser.parse_args()
    as_of = store.as_of(store.STORE_PATH)
    if as_of is None:
        print("No local store. Run scripts/update_data.py first.", file=sys.stderr)
        return 1
    results = {sym: run(sym) for sym in STOCKS}
    print(f"Data as of {as_of:%d %b %Y}. Last 5 years; 4 walk-forward periods covering the newest 40%; "
          "0.17% cost per buy or sell.\n")
    print(table(results))
    if args.figures:
        figures(results, args.figures)
        print(f"\nFigures saved in {args.figures}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
