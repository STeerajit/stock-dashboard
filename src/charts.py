"""Plotly figures. Plotly is used because Streamlit's native charts have no candlestick type."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.i18n import text

# Indicators the user can switch on, in the order of the toggle buttons.
EXTRAS = ("sma200", "bollinger", "macd", "obv")

# Colours from the app theme (.streamlit/config.toml): green and red only for up and down.
UP, DOWN, ACCENT, MUTED = "#059669", "#DC2626", "#3B82F6", "#94A3B8"
GOLD = "#A16207"  # the palette's third colour, for the long average
LINE = {"SMA20": ACCENT, "SMA50": MUTED, "SMA200": GOLD}


def price_chart(df: pd.DataFrame, symbol: str, supports: list[float], resistances: list[float],
                lang: str = "en", extras: frozenset[str] | set[str] = frozenset()) -> go.Figure:
    """Candlestick + SMA20/50 + S/R lines, with Volume and RSI panels below.

    `extras` (see EXTRAS) adds SMA200 and the Bollinger bands on the price panel, and a MACD and an OBV panel.
    """
    panels = ["volume", "rsi"] + [p for p in ("macd", "obv") if p in extras]
    rows = 1 + len(panels)
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.5] + [0.5 / len(panels)] * len(panels))
    row_of = {p: i + 2 for i, p in enumerate(panels)}

    fig.add_trace(
        go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name=symbol,
                       increasing_line_color=UP, decreasing_line_color=DOWN),
        row=1, col=1,
    )
    for col in ["SMA20", "SMA50"] + (["SMA200"] if "sma200" in extras else []):
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col, line=dict(width=1.5, color=LINE[col])), row=1, col=1)
    if "bollinger" in extras:
        for col in ("BB_upper", "BB_lower"):
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=text(f"chart.{col}", lang),
                                     line=dict(width=1, dash="dot", color=ACCENT)), row=1, col=1)
    for lv in supports:
        fig.add_hline(y=lv, line=dict(color=UP, dash="dot", width=1), row=1, col=1,
                      annotation_text=f"S {lv:,.2f}", annotation_position="bottom right")
    for lv in resistances:
        fig.add_hline(y=lv, line=dict(color=DOWN, dash="dot", width=1), row=1, col=1,
                      annotation_text=f"R {lv:,.2f}", annotation_position="top right")

    up = df["Close"] >= df["Open"]
    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name=text("chart.volume", lang), marker_color=up.map({True: UP, False: DOWN})),
        row=row_of["volume"], col=1,
    )

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI 14", line=dict(width=1.5, color=ACCENT)), row=row_of["rsi"], col=1)
    for y in (30, 70):
        fig.add_hline(y=y, line=dict(color=MUTED, dash="dash", width=1), row=row_of["rsi"], col=1)

    if "macd" in extras:
        r = row_of["macd"]
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name=text("chart.macd_hist", lang),
                             marker_color=MUTED), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(width=1.5, color=ACCENT)), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name=text("chart.macd_signal", lang),
                                 line=dict(width=1.5, dash="dot", color=MUTED)), row=r, col=1)
        fig.update_yaxes(title_text="MACD", row=r, col=1)
    if "obv" in extras:
        r = row_of["obv"]
        fig.add_trace(go.Scatter(x=df.index, y=df["OBV"], name="OBV", line=dict(width=1.5, color=ACCENT)), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["OBV_SMA20"], name=text("chart.obv_avg", lang),
                                 line=dict(width=1, dash="dot", color=MUTED)), row=r, col=1)
        fig.update_yaxes(title_text="OBV", row=r, col=1)

    fig.update_layout(height=700 + 150 * (rows - 3), xaxis_rangeslider_visible=False, margin=dict(t=10, b=10),
                      showlegend=True, legend=dict(orientation="h", y=1.02, x=0))
    fig.update_yaxes(title_text=text("chart.price_axis", lang), row=1, col=1)
    fig.update_yaxes(title_text=text("chart.volume", lang), row=row_of["volume"], col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=row_of["rsi"], col=1)
    return fig
