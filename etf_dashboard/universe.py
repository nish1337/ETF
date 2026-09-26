"""ETF universe: the fund families (issuers) we analyze and their ETFs.

Edit this file to add or remove funds. Each entry is
``ticker: (name, category)``.
"""

FUND_FAMILIES: dict[str, dict[str, tuple[str, str]]] = {
    "Avantis": {
        "AVUV": ("Avantis U.S. Small Cap Value ETF", "US Small Cap Value"),
        "AVDV": ("Avantis International Small Cap Value ETF", "International Small Cap Value"),
        "AVEM": ("Avantis Emerging Markets Equity ETF", "Emerging Markets"),
    },
}


def etf_table():
    """Flat list of dicts: ticker, name, category, family."""
    rows = []
    for family, etfs in FUND_FAMILIES.items():
        for ticker, (name, category) in etfs.items():
            rows.append({"Ticker": ticker, "Name": name, "Category": category, "Family": family})
    return rows


def all_etfs() -> dict[str, str]:
    """ticker -> name for every ETF in the universe."""
    return {t: name for etfs in FUND_FAMILIES.values() for t, (name, _) in etfs.items()}
