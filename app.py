"""Avantis ETF dashboard.

Run with:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="ETF Dashboard", page_icon="🥧", layout="wide")

st.navigation([
    st.Page("views/pie_builder.py", title="Holdings & Pie Builder", icon="🥧", default=True),
    st.Page("views/performance.py", title="Performance", icon="📈"),
]).run()
