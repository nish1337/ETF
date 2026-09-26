"""Holdings & Pie Builder: see what each ETF holds and turn the top picks into a brokerage pie."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from etf_dashboard.holdings import build_pie, fetch_top_holdings, is_us_listed, parse_holdings_file, round_to_total
from etf_dashboard.universe import all_etfs

# First three categorical slots: safe to tell apart even for color-blind readers
FUND_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
ETFS = all_etfs()
fund_color = {t: FUND_COLORS[i % len(FUND_COLORS)] for i, t in enumerate(ETFS)}

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem;}
      div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,0.25); border-radius: 10px; padding: 12px 16px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def yahoo_holdings(ticker: str) -> pd.DataFrame:
    return fetch_top_holdings(ticker)


@st.cache_data(show_spinner=False)
def file_holdings(data: bytes, name: str) -> pd.DataFrame:
    return parse_holdings_file(data, name)


# ---------- sidebar ----------
with st.sidebar:
    st.header("🥧 Pie settings")
    n_picks = st.slider("Stocks per ETF", 1, 15, 5)
    us_only = st.checkbox("Only US-listed tickers", value=False,
                          help="Skip foreign listings (e.g. 2330.TW) that many US brokerages can't buy; "
                               "the next-largest holding is picked instead.")
    method = st.radio("Weight stocks inside each ETF's slice",
                      ["Proportional to ETF weight", "Equal weight"],
                      help="Proportional keeps the fund's own tilt; equal gives each picked stock the same share.")
    st.markdown("**Share of the pie per ETF**")
    alloc = {t: st.number_input(t, 0, 100, round(100 / len(ETFS)), 1, key=f"alloc_{t}") for t in ETFS}
    whole = st.checkbox("Round to whole percents", value=True,
                        help="Many brokerage pies (e.g. M1) only accept whole-number percentages.")
    st.caption("Holdings change over time. This is a tool, not investment advice.")

st.title("🥧 Holdings & Pie Builder")
st.caption("See what each Avantis ETF holds, pick the top stocks, and get the percentages to enter in your brokerage pie.")

# ---------- load holdings ----------
holdings: dict[str, pd.DataFrame] = {}
sources: dict[str, str] = {}
with st.expander("📂 Upload full holdings files (optional: Yahoo only gives the top 10 per ETF)"):
    st.markdown(
        "On each fund's page at **avantisinvestors.com**, open the *Holdings* tab and download the full list "
        "(CSV or Excel), then drop it here. Any file with a ticker/name column and a weight column works."
    )
    cols = st.columns(len(ETFS))
    uploads = {t: c.file_uploader(t, type=["csv", "xlsx", "xls"], key=f"up_{t}") for t, c in zip(ETFS, cols)}

errors = []
with st.spinner("Loading holdings…"):
    for t in ETFS:
        try:
            if uploads[t] is not None:
                holdings[t] = file_holdings(uploads[t].getvalue(), uploads[t].name)
                sources[t] = f"uploaded file · {len(holdings[t])} holdings"
            else:
                holdings[t] = yahoo_holdings(t)
                sources[t] = f"Yahoo Finance · top {len(holdings[t])} holdings"
        except Exception as exc:
            errors.append(f"**{t}**: {exc}")
            holdings[t] = pd.DataFrame(columns=["Symbol", "Name", "Weight"])
            sources[t] = "no data"

if errors:
    st.error("Couldn't load some holdings. Check your internet connection, or upload the file above.\n\n"
             + "\n\n".join(errors), icon="⚠️")

# ---------- per-ETF holdings ----------
st.subheader("1 · What each ETF holds")
picks: dict[str, pd.DataFrame] = {}
tabs = st.tabs([f"{t} — {ETFS[t].replace('Avantis ', '')}" for t in ETFS])
for tab, t in zip(tabs, ETFS):
    with tab:
        df = holdings[t].copy()
        if df.empty:
            st.info(f"No holdings loaded for {t}.")
            picks[t] = df
            continue
        df.insert(0, "Rank", range(1, len(df) + 1))
        df["US-listed"] = df["Symbol"].map(is_us_listed)
        eligible = df[df["US-listed"]] if us_only else df
        default = list(eligible["Symbol"].head(n_picks))
        if len(eligible) < n_picks:
            st.warning(f"Only {len(eligible)} eligible holdings available for {t}. "
                       "Upload the full holdings file to pick more.", icon="ℹ️")

        left, right = st.columns([3, 2])
        with left:
            st.caption(f"Source: {sources[t]}")
            show = df.head(25).iloc[::-1]
            fig = go.Figure(go.Bar(
                x=show["Weight"], y=show["Symbol"], orientation="h",
                marker=dict(color=[fund_color[t] if s in default else "#b5b3ab" for s in show["Symbol"]],
                            cornerradius=4),
                text=[f"{w:.2%}" for w in show["Weight"]], textposition="outside", cliponaxis=False,
                customdata=show[["Name", "Rank"]],
                hovertemplate="<b>%{y}</b> · %{customdata[0]}<br>#%{customdata[1]} · %{x:.2%} of fund<extra></extra>",
            ))
            fig.update_layout(height=60 + 30 * len(show), margin=dict(l=8, r=8, t=8, b=8))
            fig.update_xaxes(tickformat=".1%", range=[0, show["Weight"].max() * 1.3],
                             gridcolor="rgba(137,135,129,0.25)")
            fig.update_yaxes(showgrid=False, ticksuffix="  ")
            st.plotly_chart(fig, use_container_width=True, key=f"bar_{t}")
        with right:
            chosen = st.multiselect(f"Stocks from {t} to include in your pie", list(df["Symbol"]), default=default,
                                    key=f"pick_{t}_{n_picks}_{us_only}_{sources[t]}",
                                    format_func=lambda s, d=df.set_index("Symbol"): f"{s} — {d.loc[s, 'Name']}")
            picks[t] = df[df["Symbol"].isin(chosen)][["Symbol", "Name", "Weight"]]
            c1, c2 = st.columns(2)
            c1.metric("Picked", f"{len(picks[t])} stocks")
            c2.metric("Share of the fund", f"{picks[t]['Weight'].sum():.1%}")
            foreign = [s for s in picks[t]["Symbol"] if not is_us_listed(s)]
            if foreign:
                st.caption(f"🌍 Foreign listings, may not be buyable at a US brokerage: {', '.join(foreign)}. "
                           "Look for a US ADR ticker (e.g. TSM for 2330.TW) or tick *Only US-listed*.")
        with st.expander(f"All {len(df)} loaded holdings for {t}"):
            st.dataframe(df, hide_index=True, use_container_width=True,
                         column_config={"Weight": st.column_config.NumberColumn("Weight in ETF", format="percent"),
                                        "US-listed": st.column_config.CheckboxColumn()})

# ---------- pie ----------
st.divider()
st.subheader("2 · Your pie")
pie = build_pie(picks, alloc, "proportional" if method.startswith("Proportional") else "equal")
if pie.empty:
    st.info("Pick at least one stock and give its ETF a share above 0%.")
    st.stop()

pie["Pie %"] = round_to_total(pie["Pie %"], 0 if whole else 2)
pie = pie[pie["Pie %"] > 0].sort_values("Pie %", ascending=False).reset_index(drop=True)
dropped = set().union(*[set(p["Symbol"]) for p in picks.values()]) - set(pie["Symbol"])

m = st.columns(4)
m[0].metric("Stocks in pie", len(pie))
m[1].metric("ETFs used", pie["From ETF"].str.split(", ").explode().nunique())
m[2].metric(f"Largest slice · {pie.iloc[0]['Pie %']:g}%", pie.iloc[0]["Symbol"])
m[3].metric("Total", f"{pie['Pie %'].sum():g}%")
if dropped:
    st.caption(f"Rounded down to 0% and left out: {', '.join(sorted(dropped))}. Untick whole-percent rounding to keep them.")

left, right = st.columns([1, 1])
with left:
    sb = pie.assign(ETF=pie["From ETF"].str.split(", ").str[0])
    fig = px.sunburst(sb, path=["ETF", "Symbol"], values="Pie %", color="ETF", color_discrete_map=fund_color,
                      hover_data={"Name": True})
    fig.update_traces(marker=dict(line=dict(width=2, color="white")), insidetextorientation="radial",
                      hovertemplate="<b>%{label}</b><br>%{value:g}% of pie<extra></extra>")
    fig.update_layout(height=480, margin=dict(l=8, r=8, t=8, b=8))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Inner ring = ETF, outer ring = stock. Hover for details.")
with right:
    st.dataframe(
        pie, hide_index=True, use_container_width=True, height=min(36 * (len(pie) + 1) + 4, 600),
        column_config={
            "Pie %": st.column_config.NumberColumn("Pie %", format="%.0f%%" if whole else "%.2f%%"),
            "Weight in ETF": st.column_config.NumberColumn(format="percent"),
        },
    )
    st.download_button("⬇️ Download pie as CSV", pie.to_csv(index=False), "my_pie.csv", "text/csv")
    st.code("\n".join(f"{s:<10} {v:g}%" for s, v in zip(pie["Symbol"], pie["Pie %"])), language=None)
    st.caption("Copy this list into your brokerage pie: ticker and target percent.")
