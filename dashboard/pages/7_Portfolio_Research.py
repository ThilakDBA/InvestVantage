import httpx
import pandas as pd
import plotly.express as px
import streamlit as st
from shared import API_BASE_URL, api_get, configure_page, research_notice, safe_get

configure_page("Portfolio Research", "💼")

instruments = safe_get("/api/v1/instruments", default=[])
with st.expander("Add or update a paper holding"):
    with st.form("holding"):
        symbol = st.selectbox("Instrument", [item["symbol"] for item in instruments])
        quantity = st.number_input("Quantity", min_value=0.0, value=0.0)
        average_cost = st.number_input("Average cost", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Save paper holding", use_container_width=True)
    if submitted:
        response = httpx.put(
            f"{API_BASE_URL}/api/v1/portfolio/holdings",
            json={"symbol": symbol, "quantity": quantity, "average_cost": average_cost},
            timeout=10,
        )
        if response.is_success:
            st.success("Paper holding saved")
            api_get.clear()
            st.rerun()
        else:
            st.error(response.json().get("detail", "Holding update failed"))

portfolio = safe_get("/api/v1/portfolio/exposure", default={})
holdings = portfolio.get("holdings", [])
if holdings:
    holding_frame = pd.DataFrame(holdings).sort_values("cost_value", ascending=False)
    total = holding_frame["cost_value"].sum()
    holding_frame["Allocation %"] = holding_frame["cost_value"] / total * 100
    largest_position = holding_frame.iloc[0]

    total_column, positions_column, sectors_column, concentration_column = st.columns(4)
    total_column.metric("Invested cost", f"${total:,.2f}")
    positions_column.metric("Active positions", len(holdings))
    sectors_column.metric("Sectors", len(portfolio.get("sector_exposure", {})))
    concentration_column.metric(
        "Largest position",
        largest_position["symbol"],
        f"{largest_position['Allocation %']:.1f}% of invested cost",
    )

    allocation_tab, sector_tab, holdings_tab = st.tabs(
        ["Position allocation", "Sector concentration", "Holdings"]
    )
    with allocation_tab:
        st.plotly_chart(
            px.bar(
                holding_frame.sort_values("Allocation %"),
                x="Allocation %",
                y="symbol",
                orientation="h",
                title="Position allocation ranked by invested cost",
                text_auto=".1f",
            ),
            use_container_width=True,
            key="portfolio-position-allocation",
        )
    with sector_tab:
        sector_frame = pd.DataFrame(
            portfolio["sector_exposure"].items(), columns=["Sector", "Exposure %"]
        ).sort_values("Exposure %")
        st.plotly_chart(
            px.bar(
                sector_frame,
                x="Exposure %",
                y="Sector",
                orientation="h",
                title="Sector exposure ranked by concentration",
                text_auto=".1f",
            ),
            use_container_width=True,
            key="portfolio-sector-exposure",
        )
    with holdings_tab:
        st.dataframe(holding_frame, use_container_width=True, hide_index=True)

    warnings = portfolio.get("warnings", [])
    if warnings:
        st.subheader("Concentration guardrails")
        for warning in warnings:
            st.warning(warning)
else:
    st.info("No paper holdings are configured. Add one above to evaluate concentration.")

research_notice()
