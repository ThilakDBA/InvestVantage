import os

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

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
    context = (symbol, provider, requested_points)
    if analyse:
        try:
            response = httpx.get(
                f"{API_BASE_URL}/api/v1/analysis/{symbol}/technical",
                params={"provider": provider, "refresh": "true", "limit": requested_points},
                timeout=30,
            )
            response.raise_for_status()
            st.session_state["analysis_result"] = response.json()
            st.session_state["analysis_context"] = context
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("detail", "Analysis request failed")
            st.error(detail)
        except httpx.HTTPError as exc:
            st.error(f"API request failed: {exc}")

    result = st.session_state.get("analysis_result")
    if result is None or st.session_state.get("analysis_context") != context:
        st.subheader("Select an instrument and run technical analysis")
        st.write("The dashboard will show trend, momentum, volatility, volume and scoring factors.")
        st.stop()

    score, trend, price, rsi = st.columns(4)
    history = pd.DataFrame(result["price_history"])
    latest_close = history.iloc[-1]["close"]
    score.metric("Technical score", f"{result['technical_score']}/100")
    trend.metric("Trend", result["trend"].title())
    price.metric("Latest close", f"${latest_close:,.2f}")
    rsi_value = result["indicators"]["rsi_14"]
    rsi.metric("RSI (14)", f"{rsi_value:.1f}" if rsi_value is not None else "N/A")

    st.subheader(f"{symbol} daily price history")
    history["timestamp"] = pd.to_datetime(history["timestamp"])
    window = st.segmented_control(
        "Chart window",
        options=["1M", "3M", "6M", "1Y", "All"],
        default="3M",
    )
    window_sizes = {"1M": 22, "3M": 66, "6M": 132, "1Y": 252}
    chart_data = history.tail(window_sizes.get(window, len(history)))
    chart = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.76, 0.24],
    )
    chart.add_trace(
        go.Candlestick(
            x=chart_data["timestamp"],
            open=chart_data["open"],
            high=chart_data["high"],
            low=chart_data["low"],
            close=chart_data["close"],
            increasing_line_color="#14b8a6",
            decreasing_line_color="#ef4444",
            name="OHLC",
        ),
        row=1,
        col=1,
    )
    chart.add_trace(
        go.Bar(
            x=chart_data["timestamp"],
            y=chart_data["volume"].fillna(0),
            marker_color="#64748b",
            name="Volume",
        ),
        row=2,
        col=1,
    )
    chart.update_layout(
        height=560,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "y": 1.02, "x": 0},
    )
    chart.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor")
    chart.update_yaxes(fixedrange=False)
    st.plotly_chart(
        chart,
        use_container_width=True,
        config={"displaylogo": False, "responsive": True, "scrollZoom": True},
    )
    st.caption(
        "Daily OHLCV bars. Drag to zoom, double-click to reset, and hover for exact values. "
        "Intraday intervals will be added with the streaming market-data phase."
    )

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

    st.subheader("Quality Momentum signal")
    if st.button("Generate research signal", use_container_width=True):
        signal_response = httpx.post(
            f"{API_BASE_URL}/api/v1/signals/generate",
            json={"symbols": [symbol], "provider": provider, "limit": requested_points},
            timeout=30,
        )
        if signal_response.is_success:
            signal = signal_response.json()[0]
            left, middle, right = st.columns(3)
            left.metric("Recommendation", signal["recommendation"])
            middle.metric("Confidence", f'{signal["confidence_score"]}/100')
            right.metric("Risk", f'{signal["risk_score"]}/100')
            st.write(signal["explanation"])
            st.write(
                {
                    "Entry": signal["entry_price"],
                    "Stop reference": signal["stop_price"],
                    "Target reference": signal["target_price"],
                }
            )
        else:
            st.error(signal_response.json().get("detail", "Signal generation failed"))

st.divider()
st.caption(
    "Research only. Recommendations are not guaranteed and users remain responsible for decisions."
)
