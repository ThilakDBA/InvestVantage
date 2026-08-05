import streamlit as st

from shared import configure_page, research_notice

configure_page("InvestVantage")

st.info(
    "Use the pages in the sidebar to move from market context to instrument research, "
    "signals, backtesting, portfolio research, and data-quality checks."
)

left, middle, right = st.columns(3)

with left:
    st.subheader("Discover")
    st.page_link("pages/1_Market_Overview.py", label="Market Overview", icon="🌐")
    st.page_link("pages/2_Watchlist.py", label="Watchlist", icon="👀")
    st.page_link("pages/3_Instrument_Research.py", label="Instrument Research", icon="📈")

with middle:
    st.subheader("Evaluate")
    st.page_link("pages/4_Signals.py", label="Signals", icon="🧭")
    st.page_link("pages/5_Fundamentals_Events.py", label="Fundamentals & Events", icon="🗞️")
    st.page_link("pages/6_Backtest_Lab.py", label="Backtest Lab", icon="🧪")

with right:
    st.subheader("Control")
    st.page_link("pages/7_Portfolio_Research.py", label="Portfolio Research", icon="💼")
    st.page_link("pages/8_Data_Health.py", label="Data Health", icon="🩺")

st.divider()
st.subheader("Research workflow")
st.markdown(
    "1. Check the market regime and provider freshness.  "
    "\n2. Rank the watchlist and open an instrument.  "
    "\n3. Review technical, fundamental, news, and event evidence.  "
    "\n4. Inspect the signal breakdown and invalidation conditions.  "
    "\n5. Validate assumptions in the Backtest Lab before paper trading."
)

research_notice()
