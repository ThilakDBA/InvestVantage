import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.shared import API_BASE_URL, configure_page, research_notice, safe_get

configure_page("Portfolio Research", "🧺")

instruments = safe_get("/api/v1/instruments", default=[])
with st.expander("Add or update a paper holding"):
    with st.form("holding"):
        symbol = st.selectbox("Instrument", [item["symbol"] for item in instruments])
        quantity = st.number_input("Quantity", min_value=0.0, value=0.0)
        average_cost = st.number_input("Average cost", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Save paper holding", use_container_width=True)
    if submitted:
        import httpx

        response = httpx.put(
            f"{API_BASE_URL}/api/v1/portfolio/holdings",
            json={"symbol": symbol, "quantity": quantity, "average_cost": average_cost},
            timeout=10,
        )
        if response.is_success:
            st.success("Paper holding saved")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(response.json().get("detail", "Holding update failed"))

portfolio = safe_get("/api/v1/portfolio/exposure", default={})
holdings = portfolio.get("holdings", [])
if holdings:
    total = sum(item["cost_value"] for item in holdings)
    holding_frame = pd.DataFrame(holdings)
    total_column, positions_column, sectors_column = st.columns(3)
    total_column.metric("Invested cost", f"${total:,.2f}")
    positions_column.metric("Active positions", len(holdings))
    sectors_column.metric("Sectors", len(portfolio.get("sector_exposure", {})))
    allocation, exposure = st.columns(2)
    allocation.plotly_chart(
        px.pie(holding_frame, values="cost_value", names="symbol", title="Position allocation"),
        use_container_width=True,
    )
    sector_frame = pd.DataFrame(
        portfolio["sector_exposure"].items(), columns=["Sector", "Exposure"]
    )
    exposure.plotly_chart(
        px.bar(sector_frame, x="Sector", y="Exposure", title="Sector exposure (%)"),
        use_container_width=True,
    )
    st.dataframe(holding_frame, use_container_width=True, hide_index=True)
    for warning in portfolio.get("warnings", []):
        st.warning(warning)
else:
    st.info("No paper holdings are configured. Add one above to evaluate concentration.")

research_notice()
