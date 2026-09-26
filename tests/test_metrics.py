import numpy as np
import pandas as pd
import pytest

from etf_dashboard.data import demo_prices
from etf_dashboard.metrics import (
    cagr,
    family_summary,
    growth_of,
    max_drawdown,
    summarize,
    total_return,
)


def series(values, start="2024-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_total_return():
    assert total_return(series([100, 110, 120])) == pytest.approx(0.2)


def test_total_return_ignores_leading_nans():
    assert total_return(series([np.nan, 50, 75])) == pytest.approx(0.5)


def test_max_drawdown():
    assert max_drawdown(series([100, 120, 60, 90, 130])) == pytest.approx(-0.5)


def test_cagr_one_year_doubling():
    s = pd.Series([100.0, 200.0], index=pd.to_datetime(["2023-01-01", "2024-01-01"]))
    assert cagr(s) == pytest.approx(1.0, rel=1e-2)


def test_growth_of():
    g = growth_of(pd.DataFrame({"A": [50.0, 100.0]}), 10_000)
    assert list(g["A"]) == [10_000, 20_000]


def test_summarize_ranks_best_first_and_family_summary():
    prices = pd.DataFrame(
        {"AAA": [100, 150.0], "BBB": [100, 90.0], "CCC": [100, 130.0]},
        index=pd.bdate_range("2024-01-01", periods=2),
    )
    info = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB", "CCC"],
            "Name": ["a", "b", "c"],
            "Category": ["x", "x", "y"],
            "Family": ["F1", "F1", "F2"],
        }
    )
    s = summarize(prices, info)
    assert list(s["Ticker"]) == ["AAA", "CCC", "BBB"]
    assert list(s["Rank"]) == [1, 2, 3]

    f = family_summary(s)
    assert list(f["Family"]) == ["F2", "F1"]  # F2 avg 30% beats F1 avg 20%
    assert f.set_index("Family").loc["F1", "Best ETF"] == "AAA"
    assert f.set_index("Family").loc["F2", "Avg Return"] == pytest.approx(0.3)


def test_demo_prices_deterministic():
    end = pd.Timestamp("2025-06-30")
    a = demo_prices(["SPY", "QQQ"], "1y", end)
    b = demo_prices(["SPY", "QQQ"], "1y", end)
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 253 and not a.isna().any().any()
