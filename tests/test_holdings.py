from pathlib import Path

import pandas as pd
import pytest

from etf_dashboard.holdings import build_pie, clean, is_us_listed, parse_holdings_file, round_to_total

FIXTURE = Path(__file__).parent / "fixtures" / "sample_holdings.csv"


def test_parse_issuer_csv_skips_title_rows_and_cash():
    df = parse_holdings_file(FIXTURE.read_bytes(), FIXTURE.name)
    assert list(df["Symbol"]) == ["AAA", "BBB", "CCC", "2330.TW", "DDD"]
    assert df.loc[0, "Weight"] == pytest.approx(0.052)
    assert df.loc[0, "Name"] == "Alpha Corp"


def test_parse_fraction_weights():
    csv = b"Symbol,Name,Weight\nX,Ex,0.4\nY,Why,0.6\n"
    df = parse_holdings_file(csv, "h.csv")
    assert list(df["Symbol"]) == ["Y", "X"]
    assert df["Weight"].sum() == pytest.approx(1.0)


def test_parse_without_weight_column_fails():
    with pytest.raises(ValueError):
        parse_holdings_file(b"Symbol,Name\nX,Ex\n", "h.csv")


def test_clean_merges_duplicate_symbols():
    df = clean(pd.DataFrame({"Symbol": ["a", "A", "B"], "Name": ["A1", "A2", "B"], "Weight": [0.01, 0.02, 0.025]}))
    assert list(df["Symbol"]) == ["A", "B"]
    assert df.loc[0, "Weight"] == pytest.approx(0.03)


def test_is_us_listed():
    assert is_us_listed("AAPL") and is_us_listed("BRK-B")
    assert not is_us_listed("2330.TW") and not is_us_listed("005930.KS") and not is_us_listed("RIO.L")


def picks():
    return {
        "F1": pd.DataFrame({"Symbol": ["A", "B"], "Name": ["a", "b"], "Weight": [0.03, 0.01]}),
        "F2": pd.DataFrame({"Symbol": ["C"], "Name": ["c"], "Weight": [0.02]}),
    }


def test_build_pie_proportional():
    pie = build_pie(picks(), {"F1": 50, "F2": 50}, "proportional").set_index("Symbol")["Pie %"]
    assert pie.to_dict() == pytest.approx({"A": 37.5, "B": 12.5, "C": 50.0})


def test_build_pie_equal_and_normalizes_alloc():
    pie = build_pie(picks(), {"F1": 2, "F2": 1}, "equal").set_index("Symbol")["Pie %"]
    assert pie.to_dict() == pytest.approx({"A": 100 / 3, "B": 100 / 3, "C": 100 / 3})


def test_build_pie_merges_stock_held_by_two_funds():
    p = picks()
    p["F2"] = pd.DataFrame({"Symbol": ["A"], "Name": ["a"], "Weight": [0.02]})
    pie = build_pie(p, {"F1": 50, "F2": 50}, "proportional").set_index("Symbol")
    assert pie.loc["A", "Pie %"] == pytest.approx(87.5)
    assert pie.loc["A", "From ETF"] == "F1, F2"


def test_round_to_total_sums_to_100():
    r = round_to_total(pd.Series([33.333, 33.333, 33.334]))
    assert r.sum() == 100 and set(r) == {33, 34}
    r2 = round_to_total(pd.Series([1.0] * 7), decimals=2)
    assert r2.sum() == pytest.approx(100)
