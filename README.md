# Stock Dashboard

Interactive stock price dashboard (US and Thai SET stocks) built with Streamlit — with a price-trend prediction model planned next.

## How to run

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Roadmap

- [x] Step 1 — Dashboard: candlestick chart, summary metrics, moving averages
- [ ] Step 2 — Prediction: train a scikit-learn model on indicators and backtest it honestly
- [ ] Step 3 — AI: use an LLM to score news sentiment as an extra feature

## Project structure

```
app.py              # Streamlit UI
src/data.py         # download prices from Yahoo Finance
src/indicators.py   # technical indicators (features for the model)
```
