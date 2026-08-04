import os

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="InvestVantage", page_icon="📈", layout="wide")
st.title("InvestVantage Research")
st.caption("Explainable market intelligence · Research and paper trading only")


@st.cache_data(ttl=30)
def instruments() -> list[dict]:
    response = httpx.get(f"{API_BASE_URL}/api/v1/instruments", timeout=10)
    response.raise_for_status()
    return response.json()


try:
    catalogue = instruments()
except httpx.HTTPError as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

if not catalogue:
    st.warning("No instruments are loaded. Run the watchlist seed service.")
    st.stop()

controls, content = st.columns([1, 3])
with controls:
    st.subheader("Analysis controls")
    symbol = st.selectbox("Instrument", [item["symbol"] for item in catalogue])
    provider = st.selectbox("Market data", ["mock", "twelve_data", "finnhub"])
    requested_points = st.slider("Price bars", 35, 250, 100)
    analyse = st.button("Analyse", type="primary", use_container_width=True)
    st.info(
        "Mock data is deterministic. Finnhub provides one quote and is not suitable "
        "for indicators yet."
    )

with content:
    if not analyse:
        st.subheader("Select an instrument and run technical analysis")
        st.write("The dashboard will show trend, momentum, volatility, volume and scoring factors.")
        st.stop()
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/analysis/{symbol}/technical",
            params={"provider": provider, "refresh": "true", "limit": requested_points},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", "Analysis request failed")
        st.error(detail)
        st.stop()
    except httpx.HTTPError as exc:
        st.error(f"API request failed: {exc}")
        st.stop()

    score, trend, price, rsi = st.columns(4)
    history = pd.DataFrame(result["price_history"])
    latest_close = history.iloc[-1]["close"]
    score.metric("Technical score", f'{result["technical_score"]}/100')
    trend.metric("Trend", result["trend"].title())
    price.metric("Latest close", f"${latest_close:,.2f}")
    rsi_value = result["indicators"]["rsi_14"]
    rsi.metric("RSI (14)", f"{rsi_value:.1f}" if rsi_value is not None else "N/A")

    st.subheader(f"{symbol} price history")
    history["timestamp"] = pd.to_datetime(history["timestamp"])
    st.line_chart(history.set_index("timestamp")["close"], height=360)

    positives, negatives = st.columns(2)
    with positives:
        st.subheader("Positive factors")
        for factor in result["positive_factors"] or ["No positive factor confirmed"]:
            st.success(factor)
    with negatives:
        st.subheader("Risk factors")
        for factor in result["negative_factors"] or ["No negative factor confirmed"]:
            st.warning(factor)

    st.subheader("Indicators")
    indicator_table = pd.DataFrame(
        [{"Indicator": key.upper(), "Value": value} for key, value in result["indicators"].items()]
    )
    st.dataframe(indicator_table, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Research only. Recommendations are not guaranteed and users remain responsible "
    "for decisions."
)
