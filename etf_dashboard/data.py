"""Price data loading: live from Yahoo Finance, or a synthetic demo set."""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

# Yahoo Finance period strings -> approx trading days (for the demo generator)
PERIOD_DAYS = {"1mo": 21, "3mo": 63, "6mo": 126, "ytd": None, "1y": 252, "3y": 756, "5y": 1260, "10y": 2520}


def fetch_live_prices(tickers: list[str], period: str) -> pd.DataFrame:
    """Adjusted daily close prices (columns = tickers) from Yahoo Finance.

    Raises RuntimeError if nothing could be downloaded.
    """
    import yfinance as yf

    raw = yf.download(
        tickers, period=period, interval="1d", auto_adjust=True, progress=False, group_by="column", threads=True, timeout=10
    )
    if raw is None or raw.empty:
        raise RuntimeError("No data returned from Yahoo Finance.")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(columns={"Close": tickers[0]})
    close = close.dropna(axis=1, how="all").sort_index()
    if close.empty:
        raise RuntimeError("No price data returned from Yahoo Finance.")
    return close


def _seed(ticker: str) -> int:
    return int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)


def demo_prices(tickers: list[str], period: str, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Deterministic synthetic prices so the dashboard runs without internet.

    Each ticker gets its own drift/volatility derived from its name, plus a
    shared market factor so correlations look realistic. Not real data.
    """
    end = (end or pd.Timestamp.today()).normalize()
    if period == "ytd":
        start = pd.Timestamp(year=end.year, month=1, day=1)
        dates = pd.bdate_range(start, end)
    else:
        dates = pd.bdate_range(end=end, periods=PERIOD_DAYS.get(period, 252) + 1)
    n = len(dates)

    market = np.random.default_rng(42).normal(0.0004, 0.010, n)
    out = {}
    for t in tickers:
        rng = np.random.default_rng(_seed(t))
        beta = rng.uniform(0.2, 1.6)
        drift = rng.uniform(-0.0003, 0.0009)
        idio = rng.uniform(0.003, 0.018)
        rets = drift + beta * (market - 0.0004) + rng.normal(0, idio, n)
        rets[0] = 0.0
        out[t] = rng.uniform(20, 500) * np.exp(np.cumsum(rets))
    return pd.DataFrame(out, index=dates)
