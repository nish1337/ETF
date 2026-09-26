"""ETF universe: the fund families (issuers) we analyze and their ETFs.

Edit this file to add or remove funds. Each entry is
``ticker: (name, category)``.
"""

FUND_FAMILIES: dict[str, dict[str, tuple[str, str]]] = {
    "Vanguard": {
        "VOO": ("Vanguard S&P 500 ETF", "US Large Cap"),
        "VTI": ("Vanguard Total Stock Market ETF", "US Total Market"),
        "VUG": ("Vanguard Growth ETF", "US Growth"),
        "VGT": ("Vanguard Information Technology ETF", "Sector: Technology"),
        "VYM": ("Vanguard High Dividend Yield ETF", "US Dividend"),
        "VXUS": ("Vanguard Total International Stock ETF", "International"),
        "BND": ("Vanguard Total Bond Market ETF", "Bonds"),
    },
    "iShares (BlackRock)": {
        "IVV": ("iShares Core S&P 500 ETF", "US Large Cap"),
        "IWF": ("iShares Russell 1000 Growth ETF", "US Growth"),
        "IWM": ("iShares Russell 2000 ETF", "US Small Cap"),
        "SOXX": ("iShares Semiconductor ETF", "Sector: Semiconductors"),
        "EFA": ("iShares MSCI EAFE ETF", "International"),
        "IAU": ("iShares Gold Trust", "Commodities: Gold"),
        "AGG": ("iShares Core US Aggregate Bond ETF", "Bonds"),
    },
    "SPDR (State Street)": {
        "SPY": ("SPDR S&P 500 ETF Trust", "US Large Cap"),
        "XLK": ("Technology Select Sector SPDR", "Sector: Technology"),
        "XLE": ("Energy Select Sector SPDR", "Sector: Energy"),
        "XLF": ("Financial Select Sector SPDR", "Sector: Financials"),
        "XLV": ("Health Care Select Sector SPDR", "Sector: Health Care"),
        "GLD": ("SPDR Gold Shares", "Commodities: Gold"),
        "DIA": ("SPDR Dow Jones Industrial Average ETF", "US Large Cap"),
    },
    "Invesco": {
        "QQQ": ("Invesco QQQ Trust", "US Growth"),
        "RSP": ("Invesco S&P 500 Equal Weight ETF", "US Large Cap"),
        "SPLV": ("Invesco S&P 500 Low Volatility ETF", "US Low Volatility"),
        "PBW": ("Invesco WilderHill Clean Energy ETF", "Thematic: Clean Energy"),
        "SPHQ": ("Invesco S&P 500 Quality ETF", "US Quality"),
    },
    "Schwab": {
        "SCHD": ("Schwab US Dividend Equity ETF", "US Dividend"),
        "SCHG": ("Schwab US Large-Cap Growth ETF", "US Growth"),
        "SCHB": ("Schwab US Broad Market ETF", "US Total Market"),
        "SCHF": ("Schwab International Equity ETF", "International"),
        "SCHZ": ("Schwab US Aggregate Bond ETF", "Bonds"),
    },
    "ARK Invest": {
        "ARKK": ("ARK Innovation ETF", "Thematic: Innovation"),
        "ARKW": ("ARK Next Generation Internet ETF", "Thematic: Internet"),
        "ARKG": ("ARK Genomic Revolution ETF", "Thematic: Genomics"),
        "ARKQ": ("ARK Autonomous Tech & Robotics ETF", "Thematic: Robotics"),
    },
    "VanEck": {
        "SMH": ("VanEck Semiconductor ETF", "Sector: Semiconductors"),
        "GDX": ("VanEck Gold Miners ETF", "Commodities: Gold Miners"),
        "MOAT": ("VanEck Morningstar Wide Moat ETF", "US Quality"),
    },
}


def etf_table():
    """Flat list of dicts: ticker, name, category, family."""
    rows = []
    for family, etfs in FUND_FAMILIES.items():
        for ticker, (name, category) in etfs.items():
            rows.append({"Ticker": ticker, "Name": name, "Category": category, "Family": family})
    return rows
