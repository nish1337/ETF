# 🥧 Avantis ETF Dashboard

A dashboard for three Avantis ETFs (**AVUV**, **AVDV**, **AVEM**). It shows what stocks each fund holds and
at what percentage, lets you pick the top stocks from each fund, and turns those picks into a pie you can
enter at your brokerage.

## Pages

### 🥧 Holdings & Pie Builder (default page)
- Holdings for each ETF with their weight in the fund (bar chart + full table)
- Picks the **top 5 stocks by weight** from each ETF automatically. Change the count, or add and remove stocks by hand
- Set how much of the pie each ETF gets (default: equal thirds)
- Inside each ETF's slice, weight stocks **proportionally** to the fund's own weights, or **equally**
- Option to round to whole percents that still add up to exactly 100% (many brokerage pies require this)
- Flags foreign listings (e.g. `2330.TW`) that US brokerages often can't buy, with an *Only US-listed* filter
- Download the pie as CSV, or copy the ticker/percent list

**Holdings data:** by default the app pulls each fund's **top 10** holdings from Yahoo Finance. For the
full list, download the holdings file from each fund's page on
[avantisinvestors.com](https://www.avantisinvestors.com/) and upload it in the app. Any CSV or Excel file
with a ticker/name column and a weight column works.

### 📈 Performance
Return, CAGR, volatility, Sharpe ratio, drawdown, and growth of $10,000 for the three ETFs.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

Live prices come from Yahoo Finance via `yfinance` (no API key needed). If Yahoo can't be
reached, the app falls back to **synthetic demo data** and shows a warning. You can also pick
*Demo data (offline)* in the sidebar to try the dashboard without internet. Demo numbers are not real.

## Customize the ETF list

Edit `etf_dashboard/universe.py` to add or remove ETFs.

## Project layout

```
app.py                     Entry point (page navigation)
views/pie_builder.py       Holdings & Pie Builder page
views/performance.py       Performance page
etf_dashboard/universe.py  The ETFs (AVUV, AVDV, AVEM)
etf_dashboard/holdings.py  Holdings loading/parsing and pie math
etf_dashboard/data.py      Price loading (Yahoo Finance + offline demo data)
etf_dashboard/metrics.py   Return / risk metrics and rankings
tests/                     Unit tests (pytest)
```

## Tests

```bash
pip install pytest && pytest
```

> Past performance does not guarantee future results. This project is for education, not investment advice.
