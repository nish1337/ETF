"""Performance page: rank the ETFs by return and risk."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from etf_dashboard.data import demo_prices, fetch_live_prices
from etf_dashboard.metrics import drawdown, family_summary, growth_of, summarize
from etf_dashboard.universe import FUND_FAMILIES, etf_table

# Categorical palette, fixed order (color follows the ETF, never its rank)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ACCENT = SERIES[0]
MUTED = "#b5b3ab"
GOOD, BAD = "#0ca30c", "#d03b3b"

PERIODS = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "Year to Date": "ytd",
           "1 Year": "1y", "3 Years": "3y", "5 Years": "5y", "10 Years": "10y"}

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem;}
      div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.25); border-radius: 10px; padding: 12px 16px;
      }
      div[data-testid="stMetricValue"] {font-size: 1.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- data ----------
@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers: tuple[str, ...], period: str, source: str) -> tuple[pd.DataFrame, str]:
    if source == "Live (Yahoo Finance)":
        try:
            return fetch_live_prices(list(tickers), period), "live"
        except Exception as exc:  # network down, blocked, rate-limited…
            return demo_prices(list(tickers), period), f"fallback: {exc}"
    return demo_prices(list(tickers), period), "demo"


def pct(x: float) -> str:
    return "–" if pd.isna(x) else f"{x:+.1%}"


def style_fig(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=8, b=8), hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(gridcolor="rgba(137,135,129,0.25)", zeroline=True, zerolinecolor="rgba(137,135,129,0.6)")
    return fig


def hbar_axes(fig: go.Figure, values: pd.Series) -> go.Figure:
    """Pad the value axis so outside labels never clip; grid runs along x only."""
    lo, hi = min(values.min(), 0), max(values.max(), 0)
    pad = (hi - lo) * 0.30 or 0.05
    fig.update_xaxes(tickformat=".0%", range=[lo - (pad if lo < 0 else 0), hi + pad],
                     showgrid=True, gridcolor="rgba(137,135,129,0.25)", zeroline=True,
                     zerolinecolor="rgba(137,135,129,0.6)")
    fig.update_yaxes(showgrid=False, zeroline=False, ticksuffix="  ")
    return fig


# ---------- sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    source = st.radio("Data source", ["Live (Yahoo Finance)", "Demo data (offline)"],
                      help="Demo data is synthetic and only for trying the dashboard without internet.")
    period_label = st.selectbox("Return period", list(PERIODS), index=4)
    families = st.multiselect("Fund families", list(FUND_FAMILIES), default=list(FUND_FAMILIES))
    top_n = st.slider("Top N ETFs to highlight", 1, 8, 3)
    risk_free = st.number_input("Risk-free rate (annual, %)", 0.0, 10.0, 4.0, 0.25) / 100
    extra = st.text_input("Extra tickers (comma separated)", placeholder="e.g. TQQQ, XLU")
    st.caption("Past performance does not guarantee future results. Not investment advice.")

info = pd.DataFrame(etf_table())
info = info[info["Family"].isin(families)]
extras = [t.strip().upper() for t in extra.split(",") if t.strip()]
extras = [t for t in extras if t not in set(info["Ticker"])]
if extras:
    info = pd.concat([info, pd.DataFrame({"Ticker": extras, "Name": extras, "Category": "Custom", "Family": "Custom"})])

st.title("📈 ETF Performance")
st.caption(f"Ranking {len(info)} ETFs from {info['Family'].nunique()} fund families by total return · {period_label}")

if info.empty:
    st.info("Select at least one fund family in the sidebar.")
    st.stop()

with st.spinner("Loading prices…"):
    prices, status = load_prices(tuple(info["Ticker"]), PERIODS[period_label], source)

if status == "demo":
    st.warning("Showing **synthetic demo data** — switch the data source to *Live* for real prices.", icon="🧪")
elif status.startswith("fallback"):
    st.error(f"Couldn't reach Yahoo Finance, showing synthetic demo data instead. ({status[10:]})", icon="⚠️")

summary = summarize(prices, info, risk_free)
if summary.empty:
    st.error("No price data available for the selected ETFs.")
    st.stop()

missing = sorted(set(info["Ticker"]) - set(summary["Ticker"]))
if missing:
    st.caption(f"No data for: {', '.join(missing)}")

fam = family_summary(summary)
top = summary.head(top_n)
top_tickers = list(top["Ticker"])
color_map = {t: SERIES[i % len(SERIES)] for i, t in enumerate(top_tickers)}

# ---------- KPI row ----------
best, worst = summary.iloc[0], summary.iloc[-1]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🏆 Top ETF", best["Ticker"], pct(best["Total Return"]), help=best["Name"])
k2.metric("🏦 Top fund family", fam.iloc[0]["Family"], f"{fam.iloc[0]['Avg Return']:+.1%} avg")
k3.metric("Average return", f"{summary['Total Return'].mean():+.1%}",
          f"{(summary['Total Return'] > 0).mean():.0%} of ETFs positive", delta_color="off")
best_sharpe = summary.loc[summary["Sharpe"].idxmax()]
k4.metric("⚖️ Best risk-adjusted", best_sharpe["Ticker"], f"Sharpe {best_sharpe['Sharpe']:.2f}", delta_color="off")
k5.metric("📉 Worst ETF", worst["Ticker"], pct(worst["Total Return"]))

st.divider()

# ---------- row 1: leaderboard + families ----------
c1, c2 = st.columns([3, 2])
with c1:
    st.subheader(f"Top {top_n} ETFs by return")
    lb = top.sort_values("Total Return")
    fig = go.Figure(go.Bar(
        x=lb["Total Return"], y=lb["Ticker"], orientation="h",
        marker=dict(color=[color_map[t] for t in lb["Ticker"]], cornerradius=4),
        text=[pct(v) for v in lb["Total Return"]], textposition="outside", cliponaxis=False,
        customdata=lb[["Name", "Family", "Volatility", "Sharpe"]],
        hovertemplate="<b>%{y}</b> · %{customdata[0]}<br>%{customdata[1]}<br>"
                      "Return %{x:+.1%}<br>Volatility %{customdata[2]:.1%} · Sharpe %{customdata[3]:.2f}<extra></extra>",
    ))
    st.plotly_chart(hbar_axes(style_fig(fig, 60 + 48 * len(lb)), lb["Total Return"]), use_container_width=True)

with c2:
    st.subheader("Fund families by average return")
    f = fam.sort_values("Avg Return")
    fig = go.Figure(go.Bar(
        x=f["Avg Return"], y=f["Family"], orientation="h",
        marker=dict(color=[GOOD if v >= 0 else BAD for v in f["Avg Return"]], cornerradius=4),
        text=[pct(v) for v in f["Avg Return"]], textposition="outside", cliponaxis=False,
        customdata=f[["ETFs", "Best ETF", "Best Return"]],
        hovertemplate="<b>%{y}</b><br>Avg return %{x:+.1%} across %{customdata[0]} ETFs<br>"
                      "Best: %{customdata[1]} (%{customdata[2]:+.1%})<extra></extra>",
    ))
    st.plotly_chart(hbar_axes(style_fig(fig, 60 + 48 * len(f)), f["Avg Return"]), use_container_width=True)

# ---------- row 2: growth + drawdown ----------
st.subheader(f"Growth of $10,000 — top {top_n}")
g = growth_of(prices[top_tickers]).reset_index(names="Date").melt("Date", var_name="ETF", value_name="Value")
fig = px.line(g, x="Date", y="Value", color="ETF", color_discrete_map=color_map,
              category_orders={"ETF": top_tickers})
fig.update_traces(line=dict(width=2), hovertemplate="%{fullData.name}: $%{y:,.0f}<extra></extra>")
fig.update_layout(hovermode="x unified")
fig.update_yaxes(tickprefix="$", tickformat=",.0f", title_text="")
st.plotly_chart(style_fig(fig, 420), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.subheader("Risk vs. return")
    sc = summary.assign(Group=["Top " + str(top_n) if t in top_tickers else "Others" for t in summary["Ticker"]],
                        Label=[t if t in top_tickers else "" for t in summary["Ticker"]])
    fig = px.scatter(sc, x="Volatility", y="Total Return", color="Group", text="Label",
                     color_discrete_map={f"Top {top_n}": ACCENT, "Others": MUTED},
                     hover_data={"Name": True, "Family": True, "Sharpe": ":.2f", "Group": False,
                                 "Volatility": ":.1%", "Total Return": ":+.1%", "Label": False})
    fig.update_traces(marker=dict(size=10, line=dict(width=1.5, color="white")), textposition="top center",
                      textfont=dict(size=10))
    fig.update_xaxes(tickformat=".0%", title="Annualized volatility")
    fig.update_yaxes(tickformat=".0%", title="Total return")
    st.plotly_chart(style_fig(fig, 420), use_container_width=True)

with c4:
    st.subheader("Drawdown from peak — top {}".format(top_n))
    dd = prices[top_tickers].apply(drawdown).reset_index(names="Date").melt("Date", var_name="ETF", value_name="Drawdown")
    fig = px.line(dd, x="Date", y="Drawdown", color="ETF", color_discrete_map=color_map,
                  category_orders={"ETF": top_tickers})
    fig.update_traces(line=dict(width=2), hovertemplate="%{fullData.name}: %{y:.1%}<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(tickformat=".0%", title_text="")
    st.plotly_chart(style_fig(fig, 420), use_container_width=True)

# ---------- tables ----------
st.subheader("All ETFs")
tab1, tab2, tab3 = st.tabs(["📋 Ranking", "🏦 Fund families", "🔍 ETF detail"])

pct_cols = ["Total Return", "CAGR", "Volatility", "Max Drawdown"]
with tab1:
    cats = st.multiselect("Filter by category", sorted(summary["Category"].unique()))
    view = summary[summary["Category"].isin(cats)] if cats else summary
    st.dataframe(
        view, hide_index=True, use_container_width=True, height=min(38 * (len(view) + 1), 600),
        column_config={
            "Total Return": st.column_config.ProgressColumn(
                "Total Return", format="percent", min_value=float(min(summary["Total Return"].min(), 0)),
                max_value=float(summary["Total Return"].max())),
            **{c: st.column_config.NumberColumn(c, format="percent") for c in pct_cols[1:]},
            "Sharpe": st.column_config.NumberColumn(format="%.2f"),
            "Last Price": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
    st.download_button("⬇️ Download CSV", view.to_csv(index=False), f"etf_ranking_{PERIODS[period_label]}.csv",
                       "text/csv")

with tab2:
    st.dataframe(
        fam, hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(c, format="percent")
                       for c in ["Avg Return", "Best Return", "Avg Volatility"]}
        | {"Avg Sharpe": st.column_config.NumberColumn(format="%.2f")},
    )

with tab3:
    pick = st.selectbox("Choose an ETF", summary["Ticker"],
                        format_func=lambda t: f"{t} — {summary.set_index('Ticker').loc[t, 'Name']}")
    row = summary.set_index("Ticker").loc[pick]
    m = st.columns(5)
    m[0].metric("Rank", f"#{row['Rank']} of {len(summary)}")
    m[1].metric("Total return", pct(row["Total Return"]))
    m[2].metric("CAGR", pct(row["CAGR"]))
    m[3].metric("Volatility", f"{row['Volatility']:.1%}")
    m[4].metric("Max drawdown", f"{row['Max Drawdown']:.1%}")
    s = prices[pick].dropna()
    fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(width=2, color=ACCENT),
                               fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
                               hovertemplate="%{x|%b %d, %Y}: $%{y:,.2f}<extra></extra>"))
    fig.update_layout(hovermode="x")
    fig.update_yaxes(tickprefix="$", range=[s.min() * 0.95, s.max() * 1.03])
    st.caption(f"{row['Family']} · {row['Category']}")
    st.plotly_chart(style_fig(fig, 340), use_container_width=True)
