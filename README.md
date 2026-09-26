# 📈 ETF Performance Dashboard

An interactive dashboard that ranks ETFs from major fund families (Vanguard, iShares, SPDR,
Invesco, Schwab, ARK, VanEck) by return and shows which ones and which issuers performed best.

## Features

- **KPI tiles**: top ETF, top fund family, average return, best risk-adjusted (Sharpe), worst ETF
- **Top N leaderboard**: the highest-return ETFs for the selected period
- **Fund family comparison**: average return per issuer, with its best ETF
- **Growth of $10,000** chart for the top performers
- **Risk vs. return** scatter (volatility vs. total return)
- **Drawdown** chart (how far each top ETF fell from its peak)
- **Sortable table** with total return, CAGR, volatility, Sharpe, max drawdown, plus CSV download
- **ETF detail** tab with a price chart and stats for any single fund
- Periods from 1 month to 10 years, a family filter, and custom extra tickers

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

Live prices come from Yahoo Finance via `yfinance` (no API key needed). If Yahoo can't be
reached, the app falls back to **synthetic demo data** and shows a warning. You can also pick
*Demo data (offline)* in the sidebar to try the dashboard without internet. Demo numbers are not real.

## Customize the ETF list

Edit `etf_dashboard/universe.py` to add fund families or tickers.

## Project layout

```
app.py                     Streamlit dashboard (UI + charts)
etf_dashboard/universe.py  Fund families and their ETFs
etf_dashboard/data.py      Price loading (Yahoo Finance + offline demo data)
etf_dashboard/metrics.py   Return / risk metrics and rankings
tests/                     Unit tests (pytest)
```

## Tests

```bash
pip install pytest && pytest
```

> Past performance does not guarantee future results. This project is for education, not investment advice.
