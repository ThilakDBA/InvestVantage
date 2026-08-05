from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st
from shared import configure_page, research_notice, safe_get

configure_page("Market Overview", "🌐")

provider = st.selectbox("Market-data source", ["mock", "twelve_data"], index=0)
benchmarks = ["SPY", "QQQ", "XLK"]
cards = []
for symbol in benchmarks:
    payload = safe_get(f"/api/v1/market/{symbol}", {"provider": provider, "limit": 65}, {})
    bars = payload.get("bars", []) if payload else []
    if len(bars) >= 2:
        latest = bars[-1]
        close = latest["close"]
        cards.append(
            {
                "symbol": symbol,
                "price": close,
                "1D": (close / bars[-2]["close"] - 1) * 100,
                "1W": (close / bars[-min(6, len(bars))]["close"] - 1) * 100,
                "1M": (close / bars[-min(22, len(bars))]["close"] - 1) * 100,
                "timestamp": latest["timestamp"],
            }
        )

if cards:
    columns = st.columns(len(cards))
    for column, item in zip(columns, cards, strict=True):
        column.metric(
            item["symbol"],
            f"${item['price']:,.2f}",
            f"{item['1D']:+.2f}% today",
            help=f"Latest provider timestamp: {item['timestamp']}",
        )
    performance = pd.DataFrame(cards).melt(
        id_vars=["symbol"], value_vars=["1D", "1W", "1M"], var_name="Period", value_name="Return"
    )
    st.plotly_chart(
        px.bar(
            performance,
            x="symbol",
            y="Return",
            color="Period",
            barmode="group",
            title="Benchmark and sector performance (%)",
        ),
        use_container_width=True,
    )

spy = next((item for item in cards if item["symbol"] == "SPY"), None)
regime = "Unavailable"
if spy:
    regime = "Risk-on" if spy["1M"] > 0 else "Risk-off" if spy["1M"] < -3 else "Neutral"
regime_column, market_column, freshness_column = st.columns(3)
regime_column.metric("Market regime", regime, help="Baseline classification using SPY momentum.")
new_york_now = datetime.now(ZoneInfo("America/New_York"))
market_open = new_york_now.weekday() < 5 and time(9, 30) <= new_york_now.time() <= time(16)
market_column.metric("US regular session", "Open" if market_open else "Closed")
health = safe_get("/api/v1/system/data-health", default={})
latest = max(
    (row.get("latest_market_timestamp") or "" for row in health.get("price_inventory", [])),
    default="",
)
freshness_column.metric("Latest stored price", latest or "No data")

st.subheader("Top research signals")
signals = safe_get("/api/v1/signals", default=[])
if signals:
    signal_frame = pd.DataFrame(signals)
    columns = [
        "symbol",
        "recommendation",
        "confidence_score",
        "risk_score",
        "data_completeness",
        "generated_at",
    ]
    st.dataframe(signal_frame[columns].head(10), use_container_width=True, hide_index=True)
else:
    st.info("No signals have been generated yet.")

research_notice()
