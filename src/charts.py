"""Plotly figures. Plotly is used because Streamlit's native charts have no candlestick type."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.i18n import text


def price_chart(df: pd.DataFrame, symbol: str, supports: list[float], resistances: list[float],
                lang: str = "en") -> go.Figure:
    """Candlestick + moving averages + S/R lines, with Volume and RSI panels below."""
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)

    fig.add_trace(
        go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=symbol),
        row=1, col=1,
    )
    for col in [c for c in df.columns if c.startswith("SMA")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col, line=dict(width=1.5)), row=1, col=1)
    for lv in supports:
        fig.add_hline(y=lv, line=dict(color="#2e9e6b", dash="dot", width=1), row=1, col=1,
                      annotation_text=f"S {lv:,.2f}", annotation_position="bottom right")
    for lv in resistances:
        fig.add_hline(y=lv, line=dict(color="#d6455d", dash="dot", width=1), row=1, col=1,
                      annotation_text=f"R {lv:,.2f}", annotation_position="top right")

    up = df["Close"] >= df["Open"]
    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name=text("chart.volume", lang), marker_color=up.map({True: "#2e9e6b", False: "#d6455d"})),
        row=2, col=1,
    )

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI 14", line=dict(width=1.5)), row=3, col=1)
    for y in (30, 70):
        fig.add_hline(y=y, line=dict(color="gray", dash="dash", width=1), row=3, col=1)

    fig.update_layout(height=700, xaxis_rangeslider_visible=False, margin=dict(t=10, b=10), showlegend=True,
                      legend=dict(orientation="h", y=1.02, x=0))
    fig.update_yaxes(title_text=text("chart.price_axis", lang), row=1, col=1)
    fig.update_yaxes(title_text=text("chart.volume", lang), row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
    return fig
