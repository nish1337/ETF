"""Performance and risk metrics for ETF price series."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def total_return(prices: pd.Series) -> float:
    p = prices.dropna()
    return float(p.iloc[-1] / p.iloc[0] - 1) if len(p) >= 2 else np.nan


def cagr(prices: pd.Series) -> float:
    p = prices.dropna()
    if len(p) < 2:
        return np.nan
    years = (p.index[-1] - p.index[0]).days / 365.25
    if years <= 0:
        return np.nan
    return float((p.iloc[-1] / p.iloc[0]) ** (1 / years) - 1)


def annual_volatility(prices: pd.Series) -> float:
    r = prices.dropna().pct_change().dropna()
    return float(r.std() * np.sqrt(TRADING_DAYS)) if len(r) >= 2 else np.nan


def sharpe_ratio(prices: pd.Series, risk_free: float = 0.0) -> float:
    r = prices.dropna().pct_change().dropna()
    if len(r) < 2 or r.std() == 0:
        return np.nan
    excess = r - risk_free / TRADING_DAYS
    return float(excess.mean() / r.std() * np.sqrt(TRADING_DAYS))


def drawdown(prices: pd.Series) -> pd.Series:
    p = prices.dropna()
    return p / p.cummax() - 1


def max_drawdown(prices: pd.Series) -> float:
    dd = drawdown(prices)
    return float(dd.min()) if len(dd) else np.nan


def summarize(prices: pd.DataFrame, info: pd.DataFrame, risk_free: float = 0.0) -> pd.DataFrame:
    """One row per ETF with return/risk metrics, sorted by total return (best first).

    ``info`` must have columns Ticker, Name, Category, Family.
    """
    rows = []
    for t in prices.columns:
        s = prices[t]
        if s.dropna().shape[0] < 2:
            continue
        rows.append(
            {
                "Ticker": t,
                "Total Return": total_return(s),
                "CAGR": cagr(s),
                "Volatility": annual_volatility(s),
                "Sharpe": sharpe_ratio(s, risk_free),
                "Max Drawdown": max_drawdown(s),
                "Last Price": float(s.dropna().iloc[-1]),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = info.merge(df, on="Ticker", how="inner")
    df = df.sort_values("Total Return", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df


def family_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """Aggregate ETF metrics per fund family, sorted by average return."""
    if summary.empty:
        return summary
    g = summary.groupby("Family")
    out = pd.DataFrame(
        {
            "ETFs": g.size(),
            "Avg Return": g["Total Return"].mean(),
            "Best Return": g["Total Return"].max(),
            "Best ETF": g.apply(lambda d: d.loc[d["Total Return"].idxmax(), "Ticker"], include_groups=False),
            "Avg Volatility": g["Volatility"].mean(),
            "Avg Sharpe": g["Sharpe"].mean(),
        }
    )
    return out.sort_values("Avg Return", ascending=False).reset_index()


def growth_of(prices: pd.DataFrame, amount: float = 10_000) -> pd.DataFrame:
    """Value of ``amount`` invested at the first valid price of each column."""
    return prices.apply(lambda s: s / s.dropna().iloc[0] * amount)
