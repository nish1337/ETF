"""ETF holdings: load them, pick top stocks, and turn picks into brokerage pie weights."""

from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd

COLUMNS = ["Symbol", "Name", "Weight"]  # Weight is a fraction of the fund (0.05 = 5%)

_SYMBOL_COLS = ("ticker", "symbol", "stock ticker", "ticker symbol")
_NAME_COLS = ("name", "security name", "security", "description", "holding", "holding name", "company")
_WEIGHT_COLS = ("weight", "% of net assets", "% net assets", "percent of net assets", "% of fund",
                "% weight", "weighting", "holding percent", "% of assets", "market value %", "portfolio %")
_NON_STOCK = re.compile(r"\b(?:cash|usd|dollar|future|futures|swap|money market|repo|fx|currency|receivable|payable)\b",
                        re.IGNORECASE)


def fetch_top_holdings(ticker: str) -> pd.DataFrame:
    """Top ~10 holdings from Yahoo Finance. Raises RuntimeError if unavailable."""
    import yfinance as yf

    raw = yf.Ticker(ticker).funds_data.top_holdings
    if raw is None or raw.empty:
        raise RuntimeError(f"Yahoo Finance returned no holdings for {ticker}.")
    df = raw.reset_index() if "Symbol" not in raw.columns else raw.copy()
    df = df.rename(columns={"Holding Percent": "Weight"})
    return clean(df[COLUMNS])


def _match(col: str, names: tuple[str, ...]) -> bool:
    c = re.sub(r"\s+", " ", str(col)).strip().lower()
    return c in names or any(n in c for n in names if len(n) > 4)


def _find_header_row(raw: pd.DataFrame) -> int:
    """Issuer files often have a few title lines before the real header."""
    for i in range(min(len(raw), 30)):
        cells = [str(v) for v in raw.iloc[i].tolist() if pd.notna(v)]
        if any(_match(c, _WEIGHT_COLS) for c in cells) and any(
            _match(c, _SYMBOL_COLS) or _match(c, _NAME_COLS) for c in cells
        ):
            return i
    raise ValueError("Couldn't find a header row with a weight column (e.g. 'Weight' or '% of Net Assets').")


def parse_holdings_file(data: bytes, filename: str) -> pd.DataFrame:
    """Parse a holdings export (CSV or Excel) from an ETF issuer or broker."""
    if filename.lower().endswith((".xlsx", ".xls")):
        raw = pd.read_excel(io.BytesIO(data), header=None, dtype=str)
    else:
        text = data.decode("utf-8-sig", errors="replace")
        width = max(len(line.split(",")) for line in text.splitlines()[:50] or [""])
        raw = pd.read_csv(io.StringIO(text), header=None, dtype=str, names=range(width), skip_blank_lines=True)

    h = _find_header_row(raw)
    df = raw.iloc[h + 1 :].copy()
    df.columns = [str(c).strip() for c in raw.iloc[h]]

    def pick(names):
        return next((c for c in df.columns if _match(c, names)), None)

    wcol, scol, ncol = pick(_WEIGHT_COLS), pick(_SYMBOL_COLS), pick(_NAME_COLS)
    if scol is None and ncol is None:
        raise ValueError("Couldn't find a ticker/symbol or name column.")
    out = pd.DataFrame({
        "Symbol": df[scol] if scol else "",
        "Name": df[ncol] if ncol else df[scol],
        "Weight": df[wcol].astype(str).str.replace(r"[%,\s]", "", regex=True),
    })
    out["Weight"] = pd.to_numeric(out["Weight"], errors="coerce")
    out = out.dropna(subset=["Weight"])
    # Issuers report either 5.2 (percent) or 0.052 (fraction)
    if out["Weight"].sum() > 2:
        out["Weight"] = out["Weight"] / 100
    return clean(out)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize text, drop cash/derivative lines, merge share classes, sort by weight."""
    df = df.copy()
    df["Symbol"] = df["Symbol"].fillna("").astype(str).str.strip().str.upper().replace({"NAN": "", "-": ""})
    df["Name"] = df["Name"].fillna("").astype(str).str.strip()
    df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")
    df = df[(df["Weight"] > 0) & ((df["Symbol"] != "") | (df["Name"] != ""))]
    df = df[~(df["Name"].str.contains(_NON_STOCK) & (df["Symbol"].str.len() == 0))]
    df = df[~df["Symbol"].isin(["CASH", "USD", "CASH_USD"])]
    df["Symbol"] = np.where(df["Symbol"] == "", df["Name"].str.upper().str[:12], df["Symbol"])
    df = df.groupby("Symbol", as_index=False).agg(Name=("Name", "first"), Weight=("Weight", "sum"))
    return df.sort_values("Weight", ascending=False).reset_index(drop=True)[COLUMNS]


def is_us_listed(symbol: str) -> bool:
    """Yahoo uses suffixes like .TW / .L / .KS for foreign listings; plain tickers are US-listed."""
    return bool(re.fullmatch(r"[A-Z]{1,5}([.\-][A-B])?", symbol))


def build_pie(picks: dict[str, pd.DataFrame], fund_alloc: dict[str, float], method: str = "proportional") -> pd.DataFrame:
    """Combine picked holdings from several funds into one pie that sums to 100%.

    picks:       fund ticker -> DataFrame (Symbol, Name, Weight) of the chosen stocks
    fund_alloc:  fund ticker -> share of the pie for that fund (any scale; normalized)
    method:      "proportional" keeps the funds' relative weights, "equal" splits each fund's slice evenly
    """
    total_alloc = sum(v for f, v in fund_alloc.items() if f in picks and len(picks[f]))
    rows = []
    for fund, df in picks.items():
        if df.empty or total_alloc <= 0:
            continue
        share = fund_alloc.get(fund, 0) / total_alloc
        w = df["Weight"] / df["Weight"].sum() if method == "proportional" else pd.Series(1 / len(df), index=df.index)
        for (_, r), wi in zip(df.iterrows(), w):
            rows.append({"Symbol": r["Symbol"], "Name": r["Name"], "From ETF": fund,
                         "Weight in ETF": r["Weight"], "Pie %": share * wi * 100})
    if not rows:
        return pd.DataFrame(columns=["Symbol", "Name", "From ETF", "Weight in ETF", "Pie %"])
    pie = pd.DataFrame(rows)
    pie = pie.groupby("Symbol", as_index=False).agg(
        Name=("Name", "first"), **{"From ETF": ("From ETF", lambda s: ", ".join(dict.fromkeys(s))),
                                   "Weight in ETF": ("Weight in ETF", "max"), "Pie %": ("Pie %", "sum")})
    return pie.sort_values("Pie %", ascending=False).reset_index(drop=True)


def round_to_total(values: pd.Series, decimals: int = 0, total: float = 100) -> pd.Series:
    """Round so the result still sums exactly to ``total`` (largest-remainder method)."""
    scale = 10**decimals
    raw = values / values.sum() * total * scale
    floored = np.floor(raw)
    short = int(round(total * scale - floored.sum()))
    order = (raw - floored).sort_values(ascending=False).index[:short]
    floored.loc[order] += 1
    return floored / scale
