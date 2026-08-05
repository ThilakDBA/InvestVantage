from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from shared import configure_page, research_notice, safe_get

configure_page("Data Health", "🩺")

health = safe_get("/health", default={})
inventory = safe_get("/api/v1/system/data-health", default={})
service, database, mode, instruments = st.columns(4)
service.metric("API service", health.get("status", "Unavailable"))
database.metric("Database", health.get("database", "Unavailable"))
mode.metric("Trading mode", health.get("trading_mode", "Unknown"))
instruments.metric("Active instruments", inventory.get("active_instruments", 0))

st.subheader("Providers")
providers = pd.DataFrame(inventory.get("providers", []))
if not providers.empty:
    providers["status"] = providers["configured"].map({True: "Configured", False: "Missing key"})
    st.dataframe(
        providers[["name", "status", "classification"]],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Stored price history")
prices = pd.DataFrame(inventory.get("price_inventory", []))
if not prices.empty:
    prices["latest_market_timestamp"] = pd.to_datetime(
        prices["latest_market_timestamp"], utc=True
    )
    prices["age_hours"] = prices["latest_market_timestamp"].apply(
        lambda value: round((datetime.now(UTC) - value.to_pydatetime()).total_seconds() / 3600, 1)
    )
    prices["freshness"] = prices["age_hours"].apply(
        lambda hours: "Current" if hours <= 24 else "Aging" if hours <= 240 else "Stale"
    )
    st.dataframe(prices, use_container_width=True, hide_index=True)
else:
    st.warning("No stored price bars were found.")

st.subheader("Research inventory")
research = pd.DataFrame(inventory.get("research_inventory", []))
if not research.empty:
    st.dataframe(research, use_container_width=True, hide_index=True)
else:
    st.warning("No fundamentals, news, earnings or corporate actions are stored.")

st.subheader("Interpretation")
st.markdown(
    """
- **Synthetic** means deterministic mock data used only for software testing.
- **External market data** means provider-sourced prices whose delay depends on entitlements.
- **External research data** means fundamentals, news or events retrieved from a provider.
- **Cached** data remains in PostgreSQL until a refresh job updates it.
"""
)
if inventory.get("broker_orders_enabled"):
    st.error("Broker orders unexpectedly appear enabled.")
else:
    st.success("Broker execution is disabled.")

st.info(
    "API error history and rate-limit events are not persisted yet. That requires an ingestion "
    "job log table in the next observability increment."
)
research_notice()
